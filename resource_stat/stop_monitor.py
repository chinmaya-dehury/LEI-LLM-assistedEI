import os
import time
import signal
import psutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.environ.get("MONITOR_PID_FILE", os.path.join(SCRIPT_DIR, "monitor.pid"))


def read_pid():
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def stop_process(pid, timeout=5):
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"No process with pid {pid} found.")
        return True

    print(f"Stopping process {pid} (graceful terminate)...")
    try:
        p.terminate()
    except Exception as e:
        print(f"Error terminating process: {e}")

    gone, alive = psutil.wait_procs([p], timeout=timeout)
    if alive:
        print(f"Process {pid} did not exit in {timeout}s; killing...")
        for pr in alive:
            try:
                pr.kill()
            except Exception as e:
                print(f"Error killing process: {e}")
        return False

    print(f"Process {pid} stopped.")
    return True


if __name__ == "__main__":
    pid = read_pid()
    if not pid:
        print(f"PID file '{PID_FILE}' not found or invalid.")
        raise SystemExit(1)

    ok = stop_process(pid)
    # cleanup pid file
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass

    if not ok:
        raise SystemExit(2)
