import csv
import json
import os
import sys
from datetime import datetime, timezone

DATA_TYPE = "air_quality"
INPUT_PATH = os.path.join("data", DATA_TYPE, "raw_data.csv")
OUTPUT_DIR = os.path.join("output", DATA_TYPE)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "health_advisory_generator_result.json")

# Simple pollutant thresholds (ug/m3) used only to infer dominant pollutant relative intensity
# These are heuristic reference values to rank dominance; they are NOT full DAQI breakpoints.
POLLUTANT_THRESHOLDS = {
    "pm2_5": 15.0,   # WHO 2021 24h guideline
    "pm10": 45.0,    # WHO 2021 24h guideline
    "no2": 25.0,     # WHO 2021 24h guideline
    "o3": 100.0,     # WHO 2021 8h guideline
    "so2": 40.0,     # WHO 2021 24h guideline
    "co": 4000.0,    # 24h proxy (4 mg/m3)
    "no": 200.0,     # heuristic (no widely used short-term WHO 24h guideline)
    "nh3": 200.0     # heuristic (context dependent)
}

FRIENDLY_NAME = {
    "pm2_5": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "o3": "O3",
    "so2": "SO2",
    "co": "CO",
    "no": "NO",
    "nh3": "NH3"
}


def to_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def parse_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            # Strip keys/values to be safe
            r = { (k.strip() if isinstance(k, str) else k): (v.strip() if isinstance(v, str) else v) for k, v in r.items() }
            rows.append(r)
    # Sort by timestamp_unix if present, else by timestamp_utc
    def sort_key(r):
        tu = to_float(r.get("timestamp_unix"))
        if tu is not None:
            return tu
        ts = r.get("timestamp_utc") or ""
        # Attempt to parse
        try:
            return datetime.fromisoformat(ts.replace(" ", "T")).timestamp()
        except Exception:
            return 0
    rows.sort(key=sort_key)
    return rows


def daqi_band(aqi_value):
    # UK DAQI bands: 1-3 Low, 4-6 Moderate, 7-9 High, 10 Very High
    if aqi_value is None:
        return "Unknown"
    try:
        aqi = float(aqi_value)
    except Exception:
        return "Unknown"
    if aqi <= 3:
        return "Low"
    elif aqi <= 6:
        return "Moderate"
    elif aqi <= 9:
        return "High"
    else:
        return "Very High"


def make_advice_general(band, dominant_name):
    base = f"Dominant pollutant: {dominant_name}. " if dominant_name else ""
    if band == "Low":
        return base + "Air quality is good for most people. Normal outdoor activities." 
    if band == "Moderate":
        return base + "Air quality is acceptable. If you experience symptoms (e.g., cough, eye irritation), reduce prolonged or heavy outdoor exertion."
    if band == "High":
        return base + "Air quality is poor. Reduce prolonged or heavy outdoor exertion; consider indoor alternatives away from traffic."
    if band == "Very High":
        return base + "Air quality is very poor. Avoid strenuous outdoor activity; consider staying indoors with windows closed."
    return base + "Air quality status unavailable. Use caution if you notice symptoms."


def make_advice_sensitive(band, dominant_name):
    base = f"Dominant pollutant: {dominant_name}. " if dominant_name else ""
    if band == "Low":
        return base + "Usually safe for sensitive groups (children, elderly, asthmatics). Keep medications handy as advised."
    if band == "Moderate":
        return base + "Consider shorter or less intense outdoor activities; avoid busy roads; use a well-fitted mask if symptoms occur."
    if band == "High":
        return base + "Limit time outdoors and avoid strenuous activity; keep windows closed; follow your care plan and consider a mask/air purifier."
    if band == "Very High":
        return base + "Stay indoors where possible; reschedule outdoor plans; follow your action plan and seek advice if symptoms worsen."
    return base + "Air quality status unavailable. Consider limiting exposure if you are sensitive."


def identify_dominant_pollutant(row):
    ratios = []
    for p, thr in POLLUTANT_THRESHOLDS.items():
        val = to_float(row.get(p))
        if val is None or thr is None or thr <= 0:
            continue
        ratio = val / thr
        ratios.append((p, ratio, val))
    if not ratios:
        return None, None, None
    # choose max ratio
    p, ratio, val = max(ratios, key=lambda x: x[1])
    return p, ratio, val


def to_iso_utc(ts_str):
    # Input like '2025-10-28 17:24:12' presumed UTC from dataset column name
    if not ts_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(ts_str.replace(" ", "T"))
        # Treat as UTC-naive -> set tzinfo UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    ensure_dirs()
    now_iso = datetime.now(timezone.utc).isoformat()

    result = {
        "task_name": "health_advisory_generator",
        "description": "Generate brief, on-device health advisories for general and sensitive groups based on DAQI band and the identified dominant pollutant.",
        "result_summary": [],
        "result_generated_at": now_iso
    }

    if not os.path.exists(INPUT_PATH):
        # Graceful error entry while still respecting schema
        result["result_summary"].append({
            "name": "data_error",
            "value": f"File not found: {INPUT_PATH}",
            "description": "Input CSV missing; cannot compute advisories.",
            "tiemstamp": now_iso
        })
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        rows = parse_rows(INPUT_PATH)
    except Exception as e:
        result["result_summary"].append({
            "name": "data_error",
            "value": "read_failed",
            "description": f"Failed to read CSV: {e}",
            "tiemstamp": now_iso
        })
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if not rows:
        result["result_summary"].append({
            "name": "no_data",
            "value": "0_rows",
            "description": "CSV has no data rows.",
            "tiemstamp": now_iso
        })
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    last = rows[-1]
    last_ts_iso = to_iso_utc(last.get("timestamp_utc"))

    aqi_val = to_float(last.get("aqi_uk"))
    band = daqi_band(aqi_val)

    dom_key, dom_ratio, dom_val = identify_dominant_pollutant(last)
    dom_name = FRIENDLY_NAME.get(dom_key, dom_key.upper()) if dom_key else None

    # Trend vs previous reading
    trend_value = "insufficient_data"
    if len(rows) >= 2:
        prev = rows[-2]
        aqi_prev = to_float(prev.get("aqi_uk"))
        if aqi_val is not None and aqi_prev is not None:
            delta = aqi_val - aqi_prev
            if delta > 0:
                trend_value = f"up by +{delta:.1f}"
            elif delta < 0:
                trend_value = f"down by {delta:.1f}"
            else:
                trend_value = "no change"
    
    # Summaries
    aqi_label = f"{band} ({int(aqi_val) if aqi_val is not None else 'NA'})" if band != "Unknown" else "Unknown"
    result["result_summary"].append({
        "name": "latest_daqi_band",
        "value": aqi_label,
        "description": "Latest UK DAQI band derived from aqi_uk value.",
        "tiemstamp": last_ts_iso
    })

    if dom_key is not None:
        result["result_summary"].append({
            "name": "dominant_pollutant",
            "value": f"{dom_name} ({dom_val:.2f} ug/m3)",
            "description": f"Dominant by relative intensity vs heuristic reference (x{dom_ratio:.2f}).",
            "tiemstamp": last_ts_iso
        })
    else:
        result["result_summary"].append({
            "name": "dominant_pollutant",
            "value": "unknown",
            "description": "Could not determine dominant pollutant from available fields.",
            "tiemstamp": last_ts_iso
        })

    general_text = make_advice_general(band, dom_name)
    sensitive_text = make_advice_sensitive(band, dom_name)

    result["result_summary"].append({
        "name": "general_public_advisory",
        "value": band,
        "description": general_text,
        "tiemstamp": last_ts_iso
    })

    result["result_summary"].append({
        "name": "sensitive_groups_advisory",
        "value": band,
        "description": sensitive_text,
        "tiemstamp": last_ts_iso
    })

    result["result_summary"].append({
        "name": "aqi_trend_since_prev",
        "value": trend_value,
        "description": "Change in aqi_uk compared to previous reading.",
        "tiemstamp": last_ts_iso
    })

    # Persist and print
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())