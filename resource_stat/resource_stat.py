import os
import sys
import time
import json
from datetime import datetime, timedelta

# Import resource metrics helpers from resource_monitor to reduce redundancy
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(SCRIPT_DIR)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from resource_monitor import get_cpu_percent, get_memory_percent
except ImportError:
    import psutil
    def get_cpu_percent(interval=0.1): return psutil.cpu_percent(interval=interval)
    def get_memory_percent(): return psutil.virtual_memory().percent

# Configuration
MONITORING_INTERVAL_SECONDS = float(os.environ.get("MONITORING_INTERVAL_SECONDS", 0.1))
MAX_RETENTION = timedelta(hours=2)
SUMMARY_WINDOWS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "10m": timedelta(minutes=10),
    "30m": timedelta(minutes=30),
}
OUTPUT_JSON = os.environ.get("OUTPUT_JSON", os.path.join(SCRIPT_DIR, "resource_usage_summary.json"))
PID_FILE = os.environ.get("MONITOR_PID_FILE", os.path.join(SCRIPT_DIR, "monitor.pid"))
RUN_DURATION_SECONDS = int(os.environ.get("RUN_DURATION_SECONDS", "0"))


def summarize(samples, window_td):
    """Return summary dict (avg_cpu, avg_mem) for samples within window_td."""
    cutoff = datetime.now() - window_td
    recent = [s for s in samples if s[0] >= cutoff]
    if not recent:
        return {"avg_cpu": None, "avg_mem": None}
    cpu_vals = [s[1] for s in recent]
    mem_vals = [s[2] for s in recent]
    return {
        "avg_cpu": round(sum(cpu_vals) / len(cpu_vals), 2),
        "avg_mem": round(sum(mem_vals) / len(mem_vals), 2),
    }


def write_pid_file(pid_file):
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


def save_summary(out_file, payload):
    tmp = out_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, out_file)


def monitor_loop():
    """Main monitoring loop. Keeps samples in-memory and writes summary periodically."""
    samples = []  # each sample: (timestamp, cpu_percent, mem_percent)
    start = datetime.now()
    last_save = datetime.min

    import psutil
    cores = psutil.cpu_count(logical=True)
    memory_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)

    print(f"Monitor started (pid={os.getpid()}). Interval {MONITORING_INTERVAL_SECONDS}s")
    write_pid_file(PID_FILE)

    try:
        while True:
            now = datetime.now()
            # Retrieve cpu and mem using imported helper functions
            cpu = get_cpu_percent(interval=MONITORING_INTERVAL_SECONDS)
            mem = get_memory_percent()
            samples.append((now, cpu, mem))
            
            # Print sample to stdout
            print(f"Checked at {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}: CPU {cpu}%, Mem {mem}%")

            # discard samples older than MAX_RETENTION
            cutoff = datetime.now() - MAX_RETENTION
            samples = [s for s in samples if s[0] >= cutoff]

            # Save summaries every 2 seconds or if RUN_DURATION_SECONDS set and nearing end
            save_interval = max(2.0, MONITORING_INTERVAL_SECONDS * 2)
            if (datetime.now() - last_save).total_seconds() >= save_interval:
                payload = {
                    "generated_at": datetime.now().isoformat(),
                    "last_checked": datetime.now().isoformat(),
                    "summary_windows": {},
                    "total_cpu_capacity_cores": cores,
                    "total_memory_capacity_gb": memory_gb,
                }
                for name, td in SUMMARY_WINDOWS.items():
                    payload["summary_windows"][name] = summarize(samples, td)

                save_summary(OUTPUT_JSON, payload)
                last_save = datetime.now()

            # If RUN_DURATION_SECONDS set (for testing), exit after duration
            if RUN_DURATION_SECONDS > 0 and (datetime.now() - start).total_seconds() >= RUN_DURATION_SECONDS:
                print("Run duration reached; exiting monitor loop.")
                break

    except KeyboardInterrupt:
        print("KeyboardInterrupt received; exiting.")
    finally:
        # cleanup pid file
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass


if __name__ == "__main__":
    monitor_loop()