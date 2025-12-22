import os, json, datetime
import pandas as pd

def main():
    data_path = os.path.join("data", "temp_humidity", "raw_data.csv")
    df = pd.read_csv(data_path, parse_dates=["timestamp"])
    alpha = 0.3
    temp_series = df["temperature_c"]
    hum_series = df["humidity_percent"]
    temp_s = temp_series.iloc[0]
    hum_s = hum_series.iloc[0]
    for t, h in zip(temp_series.iloc[1:], hum_series.iloc[1:]):
        temp_s = alpha * t + (1 - alpha) * temp_s
        hum_s = alpha * h + (1 - alpha) * hum_s
    forecast = {"temperature_c": round(temp_s, 2), "humidity_percent": round(hum_s, 2)}
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    result = {
        "task_name": "simple_forecast_next_interval",
        "description": "Predict the next 5‑minute temperature and humidity values using exponential smoothing (α=0.3).",
        "result_summary": [
            {
                "name": "forecast_temperature_c",
                "value": forecast["temperature_c"],
                "description": "Forecasted temperature for next interval (°C).",
                "timestamp": now
            },
            {
                "name": "forecast_humidity_percent",
                "value": forecast["humidity_percent"],
                "description": "Forecasted humidity for next interval (%).",
                "timestamp": now
            }
        ],
        "result_generated_at": now
    }
    out_dir = os.path.join("output", "temp_humidity")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "simple_forecast_next_interval_result.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()