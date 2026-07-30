#!/usr/bin/env python3
"""
monitor_generated_code.py
-------------------------
Run a generated Python task and log its CPU and memory usage to CSV.

Usage examples:
  python monitor_generated_task.py generated_tasks/air-quality/my_task.py --csv output/air-quality_resource.csv
  python monitor_generated_task.py generated_tasks/air-quality/my_task.py --csv output.csv --interval 1.0 --timeout 300

The script launches the target script with the same Python interpreter, samples
`psutil.Process` metrics at `--interval` seconds while the process runs, and
writes per-sample rows to the CSV plus a small JSON summary with aggregate stats.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import List

import psutil


import ctypes
try:
    from ctypes import wintypes
except ImportError:
    wintypes = None

if wintypes is not None:
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ('cb', wintypes.DWORD),
            ('PageFaultCount', wintypes.DWORD),
            ('PeakWorkingSetSize', ctypes.c_size_t),
            ('WorkingSetSize', ctypes.c_size_t),
            ('QuotaPeakWorkingSetSize', ctypes.c_size_t),
            ('QuotaWorkingSetSize', ctypes.c_size_t),
            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
            ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
            ('PagefileUsage', ctypes.c_size_t),
            ('PeakPagefileUsage', ctypes.c_size_t)
        ]

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ('dwLowDateTime', wintypes.DWORD),
            ('dwHighDateTime', wintypes.DWORD)
        ]

def iso_ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def monitor_process(p: subprocess.Popen, csv_path: str, interval: float = 1.0, timeout: float | None = None, extra_info: dict | None = None) -> dict:
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    fieldnames = [
        "timestamp",
        "elapsed_s",
        "pid",
        "cpu_percent",
        "rss_mb",
        "vms_mb",
    ]

    start_perf = time.perf_counter()
    proc = psutil.Process(p.pid)
    peak_rss = 0.0
    samples = 0
    cpu_accum = 0.0
    accumulated_cpu_time = 0.0

    psapi = None
    kernel32 = None
    if os.name == "nt" and wintypes is not None:
        try:
            psapi = ctypes.WinDLL('psapi')
            kernel32 = ctypes.WinDLL('kernel32')
        except Exception:
            pass

    def filetime_to_seconds(ft):
        val = (ft.dwHighDateTime << 32) + ft.dwLowDateTime
        return val * 1e-7

    r_start = None
    if os.name != "nt":
        try:
            import resource
            r_start = resource.getrusage(resource.RUSAGE_CHILDREN)
        except Exception:
            pass

    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        # Initialize cpu_percent counter (non-blocking)
        try:
            proc.cpu_percent(interval=None)
        except Exception:
            pass

        while True:
            # If process ended quickly, check if we should relaunch
            if p.poll() is not None:
                if psapi is not None and kernel32 is not None and getattr(p, "_handle", None) is not None:
                    try:
                        pmc = PROCESS_MEMORY_COUNTERS()
                        pmc.cb = ctypes.sizeof(pmc)
                        if psapi.GetProcessMemoryInfo(int(p._handle), ctypes.byref(pmc), pmc.cb):
                            peak_rss = max(peak_rss, pmc.PeakWorkingSetSize / (1024 * 1024))
                        creation_time = FILETIME()
                        exit_time = FILETIME()
                        kernel_time = FILETIME()
                        user_time = FILETIME()
                        if kernel32.GetProcessTimes(
                            int(p._handle),
                            ctypes.byref(creation_time),
                            ctypes.byref(exit_time),
                            ctypes.byref(kernel_time),
                            ctypes.byref(user_time)
                        ):
                            accumulated_cpu_time += filetime_to_seconds(user_time) + filetime_to_seconds(kernel_time)
                    except Exception:
                        pass
                elif os.name != "nt" and r_start is not None:
                    try:
                        import resource
                        r_end = resource.getrusage(resource.RUSAGE_CHILDREN)
                        peak_rss = max(peak_rss, r_end.ru_maxrss / 1024.0)
                        accumulated_cpu_time += (r_end.ru_utime - r_start.ru_utime) + (r_end.ru_stime - r_start.ru_stime)
                        r_start = r_end
                    except Exception:
                        pass

                if timeout is not None and (time.perf_counter() - start_perf) < timeout:
                    try:
                        p = subprocess.Popen(
                            p.args,
                            cwd=os.path.dirname(p.args[1]) if len(p.args) > 1 else None,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        proc = psutil.Process(p.pid)
                        proc.cpu_percent(interval=None)
                        continue
                    except Exception:
                        break
                else:
                    break

            # sleep for interval then sample non-blocking cpu_percent
            try:
                time.sleep(interval)
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                # unexpected issue sampling; break to avoid tight loop
                break

            rss_mb = mem.rss / (1024 * 1024)
            vms_mb = mem.vms / (1024 * 1024)
            elapsed = time.perf_counter() - start_perf

            peak_rss = max(peak_rss, rss_mb)
            samples += 1
            cpu_accum += cpu

            writer.writerow({
                "timestamp": iso_ts(),
                "elapsed_s": f"{elapsed:.3f}",
                "pid": p.pid,
                "cpu_percent": f"{cpu:.2f}",
                "rss_mb": f"{rss_mb:.3f}",
                "vms_mb": f"{vms_mb:.3f}",
            })
            f.flush()

            # Optional timeout check
            if timeout is not None and (time.perf_counter() - start_perf) > timeout:
                try:
                    p.terminate()
                except Exception:
                    pass
                break

    end_perf = time.perf_counter()
    # ensure process finished
    try:
        return_code = p.wait(timeout=1)
    except Exception:
        return_code = p.poll()

    duration_s = end_perf - start_perf
    avg_cpu_percent = round(cpu_accum / samples, 3) if samples else 0.0
    peak_rss_mb = round(peak_rss, 3)

    if psapi is not None and kernel32 is not None and getattr(p, "_handle", None) is not None:
        try:
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(pmc)
            if psapi.GetProcessMemoryInfo(int(p._handle), ctypes.byref(pmc), pmc.cb):
                win_peak_rss = pmc.PeakWorkingSetSize / (1024 * 1024)
                peak_rss_mb = round(max(peak_rss, win_peak_rss), 3)

            creation_time = FILETIME()
            exit_time = FILETIME()
            kernel_time = FILETIME()
            user_time = FILETIME()
            if kernel32.GetProcessTimes(
                int(p._handle),
                ctypes.byref(creation_time),
                ctypes.byref(exit_time),
                ctypes.byref(kernel_time),
                ctypes.byref(user_time)
            ):
                total_cpu_time = accumulated_cpu_time + filetime_to_seconds(user_time) + filetime_to_seconds(kernel_time)
                if duration_s > 0:
                    avg_cpu_percent = round((total_cpu_time / duration_s) * 100, 3)
        except Exception:
            pass
    elif os.name != "nt" and r_start is not None:
        try:
            import resource
            r_end = resource.getrusage(resource.RUSAGE_CHILDREN)
            peak_rss_mb = round(max(peak_rss, r_end.ru_maxrss / 1024.0), 3)
            total_cpu_time = accumulated_cpu_time + (r_end.ru_utime - r_start.ru_utime) + (r_end.ru_stime - r_start.ru_stime)
            if duration_s > 0:
                avg_cpu_percent = round((total_cpu_time / duration_s) * 100, 3)
        except Exception:
            pass

    summary = {
        "pid": p.pid,
        "exit_code": return_code,
        "start_time": iso_ts(),
        "duration_s": round(duration_s, 3),
        "avg_cpu_percent": avg_cpu_percent,
        "peak_rss_mb": peak_rss_mb,
    }

    if extra_info:
        summary.update(extra_info)

    # write summary next to CSV
    json_path = os.path.splitext(csv_path)[0] + "_summary.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(summary, jf, indent=2)

    return summary

    if extra_info:
        summary.update(extra_info)

    # write summary next to CSV
    json_path = os.path.splitext(csv_path)[0] + "_summary.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(summary, jf, indent=2)

    return summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a generated Python script and monitor CPU/memory usage.")
    parser.add_argument("script", help="Path to the generated Python script to run")
    parser.add_argument("--csv", required=False, help="Output CSV path for resource samples (optional). If omitted, will be placed inside the script's generated_tasks/<dataset> folder.")
    parser.add_argument("--dataset", required=False, help="Dataset name (optional). If omitted, inferred from the script path or generated_tasks layout.")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds (default: 1.0)")
    parser.add_argument("--timeout", type=float, default=None, help="Kill process after this many seconds (optional)")
    parser.add_argument("--args", default="", help="Arguments to forward to the script (quoted string)")

    args = parser.parse_args(argv)

    script_path = args.script
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found: {script_path}")
        return 2

    # determine CSV path if not provided: prefer dataset folder under generated_tasks
    def infer_dataset_from_script(path: str) -> str | None:
        # If path contains generated_tasks/<dataset>/..., use that
        parts = os.path.normpath(path).split(os.sep)
        if "generated_tasks" in parts:
            idx = parts.index("generated_tasks")
            if idx + 1 < len(parts):
                return parts[idx + 1]

        # Otherwise, try to locate the script under generated_tasks/*/
        base = os.path.basename(path)
        gen_root = os.path.join(os.path.dirname(__file__), "generated_tasks")
        if os.path.isdir(gen_root):
            for candidate in os.listdir(gen_root):
                candidate_dir = os.path.join(gen_root, candidate)
                if not os.path.isdir(candidate_dir):
                    continue
                for root, _, files in os.walk(candidate_dir):
                    if base in files:
                        return candidate

        # Fallback: try data/ folders that exist
        data_root = os.path.join(os.path.dirname(__file__), "data")
        if os.path.isdir(data_root):
            for candidate in os.listdir(data_root):
                if os.path.isdir(os.path.join(data_root, candidate)):
                    return candidate

        return None

    # launch with same Python interpreter
    cmd = [sys.executable, script_path]
    if args.args:
        # shlex.split so users can pass quoted arguments
        cmd.extend(shlex.split(args.args))

    cwd = os.path.dirname(script_path) or None
    # decide csv path
    csv_path = args.csv
    if not csv_path:
        dataset = args.dataset or infer_dataset_from_script(script_path)
        if dataset:
            # place CSV in generated_tasks/<dataset>/resource_usage_<timestamp>.csv
            gen_dir = None
            # if script already under generated_tasks/<dataset>, use that folder
            parts = os.path.normpath(script_path).split(os.sep)
            if "generated_tasks" in parts:
                idx = parts.index("generated_tasks")
                if idx + 1 < len(parts) and parts[idx + 1] == dataset:
                    gen_dir = os.path.join(*parts[: idx + 2])
            if not gen_dir:
                gen_dir = os.path.join(os.path.dirname(__file__), "generated_tasks", dataset)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(gen_dir, f"resource_usage_{ts}.csv")
        else:
            # default to local file
            csv_path = os.path.splitext(script_path)[0] + "_resource.csv"

    print(f"[Monitor] Launching: {' '.join(cmd)} (cwd={cwd})")
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    extra = {"script": script_path, "cmd": cmd}
    try:
        summary = monitor_process(p, csv_path, interval=args.interval, timeout=args.timeout, extra_info=extra)
    except KeyboardInterrupt:
        try:
            p.terminate()
        except Exception:
            pass
        print("[Monitor] Interrupted by user")
        return 1

    print("[Monitor] Done. Summary:")
    print(json.dumps(summary, indent=2))

    # optionally print stdout/stderr of process
    try:
        out, err = p.communicate(timeout=0.1)
        if out:
            print("--- stdout (snippet) ---")
            print(out[:1000])
        if err:
            print("--- stderr (snippet) ---")
            print(err[:1000])
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
