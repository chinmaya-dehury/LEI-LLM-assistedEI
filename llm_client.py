"""Shared LLM client with Gemini rate limiting support."""

from __future__ import annotations

import math
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Iterable, Mapping, Sequence

from openai import OpenAI, RateLimitError

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    MODEL_RATE_LIMITS,
    MIN_REQUEST_INTERVAL_SECONDS,
)


class RateLimiter:
	"""Coarse-grained rate limiter for per-minute and per-day quotas."""

	def __init__(
		self,
		requests_per_minute: int,
		tokens_per_minute: int,
		requests_per_day: int,
		min_interval_seconds: float,
	) -> None:
		self.requests_per_minute = max(0, requests_per_minute)
		self.tokens_per_minute = max(0, tokens_per_minute)
		self.requests_per_day = max(0, requests_per_day)
		self.min_interval_seconds = max(0.0, float(min_interval_seconds))

		self._lock = Lock()
		self._request_times: deque[float] = deque()
		self._token_events: deque[tuple[float, int]] = deque()
		self._token_sum = 0
		self._last_request_time = 0.0
		self._current_day = datetime.now(timezone.utc).date()
		self._requests_today = 0

	def wait_for_slot(self, estimated_tokens: int = 0) -> None:
		"""Block until another request is allowed, using prompt-token estimate."""
		tokens = max(0, int(estimated_tokens))

		while True:
			with self._lock:
				now = time.monotonic()
				self._reset_day_if_needed()
				self._prune(now)

				if self.requests_per_day and self._requests_today >= self.requests_per_day:
					raise RuntimeError(
						"Daily Gemini quota exhausted (requests_per_day=%d)."
						% self.requests_per_day
					)

				sleep_candidates: list[float] = []

				if self.min_interval_seconds:
					elapsed = now - self._last_request_time if self._last_request_time else float("inf")
					if elapsed < self.min_interval_seconds:
						sleep_candidates.append(self.min_interval_seconds - elapsed)

				if self.requests_per_minute and len(self._request_times) >= self.requests_per_minute:
					earliest = self._request_times[0]
					sleep_candidates.append(max(0.0, 60.0 - (now - earliest)))

				if self.tokens_per_minute:
					if self._token_sum + tokens > self.tokens_per_minute and self._token_events:
						earliest_token_time, _ = self._token_events[0]
						sleep_candidates.append(max(0.0, 60.0 - (now - earliest_token_time)))

				sleep_for = max(sleep_candidates) if sleep_candidates else 0.0

				if sleep_for <= 0.0:
					self._last_request_time = now
					self._request_times.append(now)
					self._token_events.append((now, tokens))
					self._token_sum += tokens
					self._requests_today += 1
					return

			# Sleep outside lock
			time.sleep(min(sleep_for, 5.0))

	def record_completion(self, total_tokens: int | None) -> None:
		"""Replace last token estimate with the actual total tokens."""
		if total_tokens is None:
			return
		total = max(0, int(total_tokens))

		with self._lock:
			now = time.monotonic()
			if self._token_events:
				_, prev = self._token_events.pop()
				self._token_sum = max(0, self._token_sum - prev)
				self._token_events.append((now, total))
				self._token_sum += total
			self._prune(now)

	def _prune(self, now: float) -> None:
		"""Remove request/token entries older than one minute."""
		while self._request_times and (now - self._request_times[0]) > 60.0:
			self._request_times.popleft()

		while self._token_events and (now - self._token_events[0][0]) > 60.0:
			_, tokens = self._token_events.popleft()
			self._token_sum = max(0, self._token_sum - tokens)

	def _reset_day_if_needed(self) -> None:
		today = datetime.now(timezone.utc).date()
		if today != self._current_day:
			self._current_day = today
			self._requests_today = 0


def _default_limit(value: Any, fallback: int) -> int:
	try:
		val = int(value)
		return val if val > 0 else fallback
	except Exception:
		return fallback


_rate_limiter = RateLimiter(
	requests_per_minute=_default_limit(MODEL_RATE_LIMITS.get("requests_per_minute"), 10),
	tokens_per_minute=_default_limit(MODEL_RATE_LIMITS.get("input_tokens_per_minute"), 250_000),
	requests_per_day=_default_limit(MODEL_RATE_LIMITS.get("requests_per_day"), 20),
	min_interval_seconds=MIN_REQUEST_INTERVAL_SECONDS,
)

_client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)


def rate_limiter() -> RateLimiter:
	return _rate_limiter


def client() -> OpenAI:
	return _client


def estimate_tokens_from_messages(messages: Sequence[Mapping[str, Any]]) -> int:
	"""Crude heuristic token estimator for OpenAI-compatible chat prompts."""
	if not isinstance(messages, Sequence):
		return 0

	total_chars = 0
	for msg in messages:
		if not isinstance(msg, Mapping):
			continue
		content = msg.get("content", "")
		if isinstance(content, str):
			total_chars += len(content)
		elif isinstance(content, Iterable):
			for part in content:
				if isinstance(part, Mapping):
					text = part.get("text")
					if isinstance(text, str):
						total_chars += len(text)
				elif isinstance(part, str):
					total_chars += len(part)

	# Rough average: 4 chars/token, add small overhead per message
	token_estimate = total_chars / 4.0 + len(messages) * 6
	return max(1, int(math.ceil(token_estimate)))


def _extract_usage_total_tokens(response: Any) -> int | None:
	usage = getattr(response, "usage", None)
	if usage is not None:
		total = getattr(usage, "total_tokens", None)
		if total is None and isinstance(usage, Mapping):
			total = usage.get("total_tokens")
		if total is not None:
			try:
				return int(total)
			except Exception:
				return None

	if hasattr(response, "model_dump"):
		try:
			payload: Dict[str, Any] = response.model_dump()
			total = (
				(payload.get("usage") or {}).get("total_tokens")
			)
			if total is not None:
				return int(total)
		except Exception:
			return None
	return None


def chat_completion(*, model: str, messages: Sequence[Mapping[str, Any]], max_retries: int = 5, timeout: float = 180.0, **kwargs: Any):
	"""Wrapper applying rate limits before issuing a chat.completions request.
	
	Includes exponential backoff retry logic for rate limit (429) errors.
	Default timeout is 180 seconds (3 minutes) per request.
	"""
	prompt_tokens = estimate_tokens_from_messages(messages)
	
	for attempt in range(max_retries + 1):
		_rate_limiter.wait_for_slot(prompt_tokens)
		try:
			# Set timeout for the request
			if 'timeout' not in kwargs:
				kwargs['timeout'] = timeout
			response = _client.chat.completions.create(model=model, messages=messages, **kwargs)
			_rate_limiter.record_completion(_extract_usage_total_tokens(response))
			return response
		except RateLimitError as err:
			if attempt >= max_retries:
				raise
			# Use simple exponential backoff: 10s, 20s, 40s, 60s, 60s
			wait_time = min(10 * (2 ** attempt), 60)
			print(f"Rate limit hit. Waiting {wait_time:.0f}s before retry {attempt + 1}/{max_retries}...")
			time.sleep(wait_time)


__all__ = [
	"chat_completion",
	"client",
	"estimate_tokens_from_messages",
	"rate_limiter",
]
