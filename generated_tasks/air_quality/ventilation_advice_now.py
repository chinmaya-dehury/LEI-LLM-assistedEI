import os
import csv
import json
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any

DATA_TYPE = "air_quality"
RAW_PATH = os.path.join("data", DATA_TYPE, "raw_data.csv")
OUTPUT_DIR = os.path.join("output", DATA_TYPE)
RESULT_PATH = os.path.join(OUTPUT_DIR, "ventilation_advice_now_result.json")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return float("nan")
        return float(str(x).strip())
    except Exception:
        return float("nan")


def read_csv_records(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input CSV not found at {path}")
    rows: List[Dict[str, Any]] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Normalize and cast known numeric fields
            r_norm = dict(r)
            # timestamps
            if "timestamp_unix" in r_norm:
                try:
                    r_norm["timestamp_unix"] = int(float(str(r_norm["timestamp_unix"]).strip()))
                except Exception:
                    r_norm["timestamp_unix"] = None
            # Keep timestamp_utc as string
            # geo
            for k in ["lat", "lon", "aqi_uk", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]:
                if k in r_norm:
                    r_norm[k] = _safe_float(r_norm[k])
            rows.append(r_norm)
    # Sort by timestamp_unix if present, else by timestamp_utc
    def sort_key(rec: Dict[str, Any]):
        if rec.get("timestamp_unix") is not None:
            return rec["timestamp_unix"]
        # Fallback: parse utc string
        ts = rec.get("timestamp_utc")
        try:
            return int(datetime.fromisoformat(ts).timestamp()) if ts else 0
        except Exception:
            return 0
    rows.sort(key=sort_key)
    return rows


def percent_change(curr: float, prev: float) -> float:
    try:
        if prev == 0 or (abs(prev) < 1e-9):
            return float("inf") if curr != prev else 0.0
        return (curr - prev) / prev * 100.0
    except Exception:
        return float("nan")


def compute_ventilation_advice(
    rows: List[Dict[str, Any]],
    M: int = 3,
    pm25_threshold: float = 35.0,
    o3_threshold: float = 100.0,
    spike_pct_threshold: float = 30.0,
    pm25_abs_spike: float = 10.0,
    o3_abs_spike: float = 20.0,
) -> Dict[str, Any]:
    if not rows:
        raise ValueError("No data rows available.")

    n = len(rows)
    M_eff = max(1, min(M, n))
    recent = rows[-M_eff:]
    latest = rows[-1]
    prev = rows[-2] if n >= 2 else None

    # Extract metrics
    pm25_values = [r.get("pm2_5", float("nan")) for r in recent]
    o3_values = [r.get("o3", float("nan")) for r in recent]

    pm25_recent_max = max([v for v in pm25_values if v == v], default=float("nan"))
    o3_recent_max = max([v for v in o3_values if v == v], default=float("nan"))

    pm25_ok = (pm25_recent_max <= pm25_threshold) if pm25_recent_max == pm25_recent_max else False
    o3_ok = (o3_recent_max <= o3_threshold) if o3_recent_max == o3_recent_max else False

    # Spike detection on most recent step
    spike_detected = False
    spike_reasons = []
    if prev is not None:
        pm25_curr = latest.get("pm2_5", float("nan"))
        pm25_prev = prev.get("pm2_5", float("nan"))
        o3_curr = latest.get("o3", float("nan"))
        o3_prev = prev.get("o3", float("nan"))

        # PM2.5 spike
        if pm25_curr == pm25_curr and pm25_prev == pm25_prev:
            pm25_pct = percent_change(pm25_curr, pm25_prev)
            pm25_abs = pm25_curr - pm25_prev
            if (pm25_pct != pm25_pct):
                pass
            else:
                if pm25_pct > spike_pct_threshold or pm25_abs > pm25_abs_spike:
                    spike_detected = True
                    spike_reasons.append(
                        f"PM2.5 spike: +{pm25_abs:.2f} ug/m3 ({pm25_pct:.1f}%)"
                    )
        # O3 spike
        if o3_curr == o3_curr and o3_prev == o3_prev:
            o3_pct = percent_change(o3_curr, o3_prev)
            o3_abs = o3_curr - o3_prev
            if (o3_pct != o3_pct):
                pass
            else:
                if o3_pct > spike_pct_threshold or o3_abs > o3_abs_spike:
                    spike_detected = True
                    spike_reasons.append(
                        f"O3 spike: +{o3_abs:.2f} ug/m3 ({o3_pct:.1f}%)"
                    )
    else:
        # Not enough data to detect spike
        spike_detected = False

    recommend = bool(pm25_ok and o3_ok and (not spike_detected))

    # Build reasoning
    reasons = []
    if not pm25_ok:
        reasons.append(
            f"PM2.5 recent max {pm25_recent_max:.2f} ug/m3 exceeds threshold {pm25_threshold:.2f}."
        )
    if not o3_ok:
        reasons.append(
            f"O3 recent max {o3_recent_max:.2f} ug/m3 exceeds threshold {o3_threshold:.2f}."
        )
    if spike_detected:
        reasons.append("; ".join(spike_reasons) if spike_reasons else "Recent spike detected.")
    if not reasons:
        reasons.append(
            f"All clear in last {M_eff} intervals: PM2.5 <= {pm25_threshold}, O3 <= {o3_threshold}, no spikes."
        )

    latest_time = latest.get("timestamp_utc") or (
        datetime.fromtimestamp(latest.get("timestamp_unix", 0), tz=timezone.utc).isoformat()
    )

    result = {
        "recommendation": "yes" if recommend else "no",
        "pm25_recent_max_ugm3": pm25_recent_max,
        "o3_recent_max_ugm3": o3_recent_max,
        "intervals_checked": M_eff,
        "latest_timestamp_utc": latest_time,
        "latest_coords": {
            "lat": latest.get("lat"),
            "lon": latest.get("lon"),
        },
        "recent_spike_detected": bool(spike_detected),
        "reasons": reasons,
    }
    return result


def save_result_json(task_name: str, task_desc: str, insights: Dict[str, Any]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now_iso = iso_now()

    # Prepare result summaries according to required schema
    summaries = [
        {
            "name": "ventilation_recommended_now",
            "value": insights.get("recommendation"),
            "description": "Overall recommendation to ventilate now based on thresholds and spike checks.",
            "tiemstamp": now_iso,
        },
        {
            "name": "pm25_recent_max_ugm3",
            "value": round(float(insights.get("pm25_recent_max_ugm3", float("nan"))), 2) if insights.get("pm25_recent_max_ugm3") == insights.get("pm25_recent_max_ugm3") else None,
            "description": "Maximum PM2.5 over the last M intervals (ug/m3).",
            "tiemstamp": now_iso,
        },
        {
            "name": "o3_recent_max_ugm3",
            "value": round(float(insights.get("o3_recent_max_ugm3", float("nan"))), 2) if insights.get("o3_recent_max_ugm3") == insights.get("o3_recent_max_ugm3") else None,
            "description": "Maximum O3 over the last M intervals (ug/m3).",
            "tiemstamp": now_iso,
        },
        {
            "name": "recent_spike_detected",
            "value": insights.get("recent_spike_detected"),
            "description": "Whether a recent pollutant spike was detected between the last two readings.",
            "tiemstamp": now_iso,
        },
        {
            "name": "intervals_checked",
            "value": insights.get("intervals_checked"),
            "description": "Number of recent intervals considered (M).",
            "tiemstamp": now_iso,
        },
        {
            "name": "latest_reading_time_utc",
            "value": insights.get("latest_timestamp_utc"),
            "description": "Timestamp of the latest sensor reading (UTC).",
            "tiemstamp": now_iso,
        },
        {
            "name": "latest_coords",
            "value": insights.get("latest_coords"),
            "description": "Latitude and longitude of the latest reading.",
            "tiemstamp": now_iso,
        },
        {
            "name": "reasons",
            "value": " ".join(insights.get("reasons", [])),
            "description": "Human-readable explanation supporting the recommendation.",
            "tiemstamp": now_iso,
        },
    ]

    out = {
        "task_name": task_name,
        "description": task_desc,
        "result_summary": summaries,
        "result_generated_at": now_iso,
    }

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"Saved result to: {RESULT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Ventilation advice based on PM2.5 and O3 thresholds and spike checks.")
    parser.add_argument("--M", type=int, default=int(os.environ.get("VENT_M", 3)), help="Number of recent intervals to check (default: 3)")
    parser.add_argument("--pm25_threshold", type=float, default=float(os.environ.get("VENT_PM25_TH", 35.0)), help="PM2.5 threshold in ug/m3 (default: 35)")
    parser.add_argument("--o3_threshold", type=float, default=float(os.environ.get("VENT_O3_TH", 100.0)), help="O3 threshold in ug/m3 (default: 100)")
    parser.add_argument("--spike_pct", type=float, default=float(os.environ.get("VENT_SPIKE_PCT", 30.0)), help="Spike percent change threshold (default: 30%%)")
    parser.add_argument("--pm25_abs_spike", type=float, default=float(os.environ.get("VENT_PM25_ABS", 10.0)), help="PM2.5 absolute spike threshold (ug/m3) (default: 10)")
    parser.add_argument("--o3_abs_spike", type=float, default=float(os.environ.get("VENT_O3_ABS", 20.0)), help="O3 absolute spike threshold (ug/m3) (default: 20)")
    args = parser.parse_args()

    task_name = "ventilation_advice_now"
    task_desc = "Recommend whether it’s currently safe to ventilate based on PM2.5 and O3 staying below thresholds for the last M intervals and no recent spike detected."

    rows = read_csv_records(RAW_PATH)
    insights = compute_ventilation_advice(
        rows,
        M=args.M,
        pm25_threshold=args.pm25_threshold,
        o3_threshold=args.o3_threshold,
        spike_pct_threshold=args.spike_pct,
        pm25_abs_spike=args.pm25_abs_spike,
        o3_abs_spike=args.o3_abs_spike,
    )
    save_result_json(task_name, task_desc, insights)


if __name__ == "__main__":
    main()
