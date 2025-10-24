import psutil
import time
from datetime import datetime, timedelta
import json

def get_resource_usage():
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=5)

    cpu_usages = []
    memory_usages = []

    while datetime.now() < end_time:
        cpu_usages.append(psutil.cpu_percent(interval=1))
        memory_info = psutil.virtual_memory()
        memory_usages.append(memory_info.percent)
        print(f"Checked at {datetime.now().strftime('%H:%M:%S')}: CPU {cpu_usages[-1]}%, Memory {memory_usages[-1]}%")
        # time.sleep(4)  # Sleep for the remaining 4 seconds to make it 5 seconds total

    avg_cpu_usage = sum(cpu_usages) / len(cpu_usages)
    avg_memory_usage = sum(memory_usages) / len(memory_usages)

    total_cpu_capacity = psutil.cpu_count(logical=True)
    total_memory_capacity = round(psutil.virtual_memory().total / (1024 ** 3), 2)  # in GB

    return {
        "average_cpu_usage": avg_cpu_usage,
        "average_memory_usage": avg_memory_usage,
        "total_cpu_capacity": total_cpu_capacity,
        "total_memory_capacity": total_memory_capacity
    }

if __name__ == "__main__":
    counter = 1
    while counter <= 10:
        usage_stats = get_resource_usage()
        print("Resource Usage in the Last 5 Minutes:")
        print(f"Average CPU Usage: {usage_stats['average_cpu_usage']}%")
        print(f"Average Memory Usage: {usage_stats['average_memory_usage']}%")
        print(f"Total CPU Capacity: {usage_stats['total_cpu_capacity']} cores")
        print(f"Total Memory Capacity: {usage_stats['total_memory_capacity']} GB")
        counter += 1

    # save the resource usage stats to a json file     
    # with open("resource_usage_stats.json", "w") as f:
    #     json.dump(usage_stats, f, indent=2)