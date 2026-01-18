# Performance Analysis Results

This project analyzes and visualizes performance metrics across multiple IoT devices (Raspberry Pi 4 and 5) for different sensor datasets (Air Quality, Wind, Soil, Temperature/Humidity).

## Dataset Requirements

The project expects the following directory structure with timestamp-based data:

```
Rpi4 Updated Data/
  ├── AQ/timestamp_path/air_quality/       (Air Quality data)
  ├── Wind/timestamp_path/wind/            (Wind data)
  ├── Soil/timestamp_path/soil/            (Soil data)
  └── TH/timestamp_path/temp_humidity/       (Temperature & Humidity data)

Rpi5 Updated Data/
  ├── AQ/timestamp_path/air_quality/
  ├── Wind/timestamp_path/wind/
  ├── Soil/timestamp_path/soil/
  └── TH/timestamp_path/temp_humidity/
```

Each case directory should contain csv files generated after running the LEI-LMM Assisted Edge Intelligence

## Execution Order

Run the scripts in the following order:

1. **`result_step1.py`** - Aggregates and analyzes step 1 performance metrics
2. **`result_step2.py`** - Analyzes step 2 metrics
3. **`result_step3.py`** - Analyzes step 3 metrics
4. **`result_step4.py`** - Analyzes step 4 metrics
5. **`result_validation.py`** - Processes validation metrics
6. **`result_avg_cpu.py`** - Calculates average CPU/memory usage
7. **`res_complete_pipeline.py`** - Generates complete pipeline analysis
8. **`combine_cases_plots.py`** - Creates combined visualizations across all cases

## Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

## Output

All aggregated results are saved to `result_rpi4_rpi5/` directory with CSV and visualization files.

## Requirements

- Python 3.x
- pandas, numpy, seaborn, matplotlib, scipy
