"""
edge_dashboard.py
-----------------
Real-time Streamlit dashboard for visualizing Edge Scheduler task execution results.

Displays:
- Task name, description, and execution output
- Real-time metrics: execution status, duration, return code
- Auto-refresh to track scheduler.py execution (every 5 seconds)
- Task execution history and performance metrics

Run:
    streamlit run edge_dashboard.py

Modified on: 23-05-2026
"""

import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta
from pathlib import Path
import time

# Configuration
LOG_DIR = "logs"
DATA_DIR = "data"
TASKS_DIR = "generated_tasks"
OUTPUT_DIR = "output"

# Load from config if available
try:
    from config import DATA_TYPE
except ImportError:
    DATA_TYPE = "air_quality"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_task_descriptions() -> dict:
    """Load task descriptions from tasks_list.json."""
    tasks_file = os.path.join(TASKS_DIR, DATA_TYPE, "tasks_list.json")
    
    if not os.path.exists(tasks_file):
        return {}
    
    try:
        with open(tasks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Create dict mapping task name to description
            tasks = {}
            if isinstance(data, list):
                for task in data:
                    tasks[task.get("name", "Unknown")] = task.get("description", "No description")
            return tasks
    except Exception as e:
        st.warning(f"Could not load task descriptions: {e}")
        return {}


def get_execution_results() -> list:
    """Load execution results from output directory."""
    output_path = os.path.join(OUTPUT_DIR, DATA_TYPE)
    
    if not os.path.exists(output_path):
        return []
    
    results = []
    for json_file in sorted(Path(output_path).glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                results.append({
                    "filename": json_file.stem,
                    "timestamp": os.path.getmtime(json_file),
                    "data": data
                })
        except Exception as e:
            st.warning(f"Could not load {json_file}: {e}")
    
    return results


def get_latest_csv_metrics() -> pd.DataFrame:
    """Load the latest scheduler CSV metrics."""
    timestamp_path = os.path.join("timestamp_path", DATA_TYPE)
    
    if not os.path.exists(timestamp_path):
        return pd.DataFrame()
    
    # Find latest step4 CSV file
    csv_files = list(Path(timestamp_path).glob("step4_*.csv"))
    if not csv_files:
        return pd.DataFrame()
    
    latest_csv = max(csv_files, key=os.path.getmtime)
    
    try:
        df = pd.read_csv(latest_csv)
        return df.sort_values("start_time", ascending=False) if "start_time" in df.columns else df
    except Exception as e:
        st.warning(f"Could not load CSV metrics: {e}")
        return pd.DataFrame()


def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable string."""
    if pd.isna(seconds):
        return "N/A"
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = seconds / 60
        return f"{minutes:.2f}m"


# ============================================================================
# STREAMLIT LAYOUT
# ============================================================================

st.set_page_config(
    page_title="Edge Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧠 LLM-Assisted Edge Intelligence Dashboard")
st.markdown(f"Real-time Scheduler Execution Monitor | Data Type: **{DATA_TYPE}**")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")
refresh_interval = st.sidebar.slider(
    "Auto-refresh interval (seconds)",
    min_value=1,
    max_value=60,
    value=5,
    step=1
)

st.sidebar.markdown("---")
st.sidebar.write(f"**Data Type:** {DATA_TYPE}")
st.sidebar.write(f"**Output Directory:** `output/{DATA_TYPE}/`")
st.sidebar.write(f"**Metrics Directory:** `timestamp_path/{DATA_TYPE}/`")

# Manual refresh button
if st.sidebar.button("Refresh Now"):
    st.rerun()

# Auto-refresh logic
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = current_time
    st.rerun()

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

# Load data
task_descriptions = get_task_descriptions()
execution_results = get_execution_results()
csv_metrics = get_latest_csv_metrics()

# Display status
status_col1, status_col2, status_col3, status_col4 = st.columns(4)

if not csv_metrics.empty:
    successful = len(csv_metrics[csv_metrics["status"] == "success"]) if "status" in csv_metrics.columns else 0
    failed = len(csv_metrics[csv_metrics["status"] == "failed"]) if "status" in csv_metrics.columns else 0
    total = len(csv_metrics)
    
    # Try both column name variations
    duration_col = "script_duration_sec" if "script_duration_sec" in csv_metrics.columns else "script_duration"
    avg_duration = csv_metrics[duration_col].astype(float).mean() if duration_col in csv_metrics.columns else 0
    
    status_col1.metric("Total Tasks", total)
    status_col2.metric("Successful", successful)
    status_col3.metric("Failed", failed)
    status_col4.metric("Avg Duration", format_duration(avg_duration))
else:
    status_col1.metric("Total Tasks", 0)
    status_col2.metric("Successful", 0)
    status_col3.metric("Failed", 0)
    status_col4.metric("Avg Duration", "N/A")

# Last update timestamp
if not csv_metrics.empty:
    # Try both column name variations
    time_col = "script_start_time_ist" if "script_start_time_ist" in csv_metrics.columns else "start_time"
    if time_col in csv_metrics.columns:
        last_update = csv_metrics[time_col].iloc[0]
        st.info(f"Last updated: {last_update}")
    else:
        st.info("Waiting for scheduler execution results...")
else:
    st.info("Waiting for scheduler execution results...")

# ============================================================================
# EXECUTION METRICS TABLE
# ============================================================================

# Section removed - redundant with Performance Summary below

# ============================================================================
# DETAILED TASK RESULTS
# ============================================================================

st.markdown("### Task Details")

if execution_results:
    st.info(f"Found {len(execution_results)} execution result files")
    
    for idx, result in enumerate(execution_results[:10]):  # Show last 10 results
        result_data = result["data"]
        timestamp = datetime.fromtimestamp(result["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        
        task_name = result_data.get("task_name", "Unknown")
        description = task_descriptions.get(task_name, "No description available")
        output = result_data.get("result_summary", [])
        
        # Create expander with task info
        expander_title = f"✓ {task_name} — {timestamp}"
        if result_data.get("status") == "failed":
            expander_title = f"✗ {task_name} — {timestamp}"
        
        with st.expander(expander_title, expanded=(idx == 0)):
            # Task description
            st.markdown(f"**Description:** {description}")
            
            # Task status
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Status:** {result_data.get('status', 'unknown')}")
            col2.write(f"**Duration:** {format_duration(result_data.get('duration', 0))}")
            col3.write(f"**Return Code:** {result_data.get('return_code', 'N/A')}")
            
            # Output details
            st.markdown("**Output:**")
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict):
                        st.json(item)
                    else:
                        st.write(item)
            elif isinstance(output, dict):
                st.json(output)
            else:
                st.code(str(output))
            
            # Error information if present
            if "error" in result_data and result_data["error"]:
                st.error(f"**Error:** {result_data['error']}")
else:
    st.info("No execution results found yet. Run scheduler/edge_scheduler.py to generate output.")

# ============================================================================
# PERFORMANCE SUMMARY
# ============================================================================

if not csv_metrics.empty:
    st.markdown("### Performance Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Success rate
        if "status" in csv_metrics.columns and len(csv_metrics) > 0:
            success_count = len(csv_metrics[csv_metrics["status"] == "success"])
            success_rate = (success_count / len(csv_metrics)) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
    
    with col2:
        # Execution time distribution
        duration_col = "script_duration_sec" if "script_duration_sec" in csv_metrics.columns else "script_duration"
        if duration_col in csv_metrics.columns:
            durations = csv_metrics[duration_col].astype(float)
            st.metric("Max Duration", format_duration(durations.max()))

# ============================================================================
# AUTO-REFRESH INDICATOR
# ============================================================================

st.markdown("---")
st.caption(
    f"Auto-refresh enabled (every {refresh_interval}s) | "
    f"Last refresh: {datetime.now().strftime('%H:%M:%S')} | "
    f"Data Type: {DATA_TYPE}"
)
