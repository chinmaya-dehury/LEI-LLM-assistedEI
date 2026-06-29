"""
resource_monitor.py
-------------------
Monitors Raspberry Pi system resources:
- CPU usage (%)
- Memory usage (%)
- Network I/O (bytes sent/received)
- CPU temperature (°C)

Can be called from pipeline steps to log metrics at start/end of each step.

Created on 04-06-2026 by Siddharth
"""

import os
import json
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional


IST = timezone(timedelta(hours=5, minutes=30))


def get_cpu_percent(interval: float = 1.0) -> float:
    """Get CPU usage percentage (average across all cores)."""
    return psutil.cpu_percent(interval=interval)


def get_memory_percent() -> float:
    """Get memory usage percentage."""
    return psutil.virtual_memory().percent


def get_network_io() -> Dict[str, int]:
    """Get cumulative network I/O stats."""
    net_io = psutil.net_io_counters()
    return {
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv,
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv,
    }


def get_cpu_temperature() -> Optional[float]:
    """
    Get CPU temperature in Celsius.
    On Raspberry Pi: reads from /sys/class/thermal/thermal_zone0/temp
    Returns None if not available.
    """
    try:
        # Raspberry Pi thermal zone
        temp_path = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_path):
            with open(temp_path, "r") as f:
                temp_millidegrees = int(f.read().strip())
                return temp_millidegrees / 1000.0
        
        # Alternative: using psutil (requires psutil with sensors)
        # sensors_temperatures() may not be available on Windows
        if not hasattr(psutil, 'sensors_temperatures'):
            return None
        
        temps = psutil.sensors_temperatures()
        if "coretemp" in temps:
            return temps["coretemp"][0].current
        if "cpu_thermal" in temps:
            return temps["cpu_thermal"][0].current
        
        return None
    except (AttributeError, FileNotFoundError, ValueError):
        # Silent return on Windows or systems without sensor support
        return None
    except Exception as e:
<<<<<<< HEAD
        print(f"[WARNING] Could not read CPU temperature: {e}")
=======
        # Only warn on unexpected errors
        print(f"[WARNING] Unexpected error reading CPU temperature: {e}")
>>>>>>> benchmark-v3.0
        return None


def capture_resource_snapshot() -> Dict:
    """Capture all resource metrics at a single point in time."""
    return {
        "timestamp_ist": datetime.now(IST).isoformat(),
        "cpu_percent": get_cpu_percent(interval=0.5),
        "memory_percent": get_memory_percent(),
        "network_io": get_network_io(),
        "cpu_temperature_celsius": get_cpu_temperature(),
    }


def log_resource_metrics(
    csv_path: str,
    step_name: str,
    event_type: str,  # "start" or "end"
    task_name: str = "",
    model_name: str = "",
    run_count: str = "",
) -> None:
    """
    Log resource metrics to CSV.
    event_type: "start" or "end" of a step
    """
    import csv
    
    snapshot = capture_resource_snapshot()
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    
    fieldnames = [
        "timestamp_ist",
        "step",
        "event_type",
        "run_count",
        "task_name",
        "model_name",
        "cpu_percent",
        "memory_percent",
        "bytes_sent",
        "bytes_recv",
        "packets_sent",
        "packets_recv",
        "cpu_temperature_celsius",
    ]
    
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            "timestamp_ist": snapshot["timestamp_ist"],
            "step": step_name,
            "event_type": event_type,
            "run_count": run_count,
            "task_name": task_name,
            "model_name": model_name,
            "cpu_percent": snapshot["cpu_percent"],
            "memory_percent": snapshot["memory_percent"],
            "bytes_sent": snapshot["network_io"]["bytes_sent"],
            "bytes_recv": snapshot["network_io"]["bytes_recv"],
            "packets_sent": snapshot["network_io"]["packets_sent"],
            "packets_recv": snapshot["network_io"]["packets_recv"],
            "cpu_temperature_celsius": snapshot["cpu_temperature_celsius"],
        })


def save_resource_summary(json_path: str, summary_data: Dict) -> None:
    """Save resource monitoring summary as JSON."""
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)