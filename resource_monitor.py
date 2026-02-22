"""Resource monitoring for tracking CPU, memory, and GPU usage during pipeline execution"""
import psutil
import time
from typing import Dict

def get_system_resources() -> Dict[str, float]:
	"""Get current system resource usage"""
	cpu_percent = psutil.cpu_percent(interval=0.1)
	memory = psutil.virtual_memory()
	
	return {
		"cpu_percent": round(cpu_percent, 2),
		"memory_used_mb": round(memory.used / (1024 * 1024), 2),
		"memory_percent": round(memory.percent, 2),
		"memory_available_mb": round(memory.available / (1024 * 1024), 2),
	}

def get_process_resources() -> Dict[str, float]:
	"""Get current process resource usage"""
	try:
		process = psutil.Process()
		with process.oneshot():
			cpu = process.cpu_percent(interval=0.1)
			mem_info = process.memory_info()
			
		return {
			"process_cpu_percent": round(cpu, 2),
			"process_memory_mb": round(mem_info.rss / (1024 * 1024), 2),
		}
	except Exception:
		return {"process_cpu_percent": 0, "process_memory_mb": 0}
