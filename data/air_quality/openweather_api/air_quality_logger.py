import requests
import csv
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# ----------------------------
# CONFIG - EDIT THESE
# ----------------------------
# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")  # <-- read your OpenWeather API key from .env file
LAT = 28                        # <-- latitude (number) of Delhi
LON = 77                        # <-- longitude (number) of Delhi
CSV_FILE = "../air_quality_log.csv"
POLL_INTERVAL_SECONDS = 10 * 60  # 10 minutes


def fetch_air_quality(api_key, lat, lon):
    """
    Call OpenWeather Air Pollution API and return parsed data dict.
    """
    url = (
        f"http://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}&lon={lon}&appid={api_key}"
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()  # raise error if bad status code

    data = resp.json()

    # Defensive parsing
    coord = data.get("coord", {})
    entries = data.get("list", [])

    if not entries:
        raise ValueError("API returned no 'list' data")

    first = entries[0]

    main = first.get("main", {})
    comps = first.get("components", {})
    dt_unix = first.get("dt", 0)

    # Convert UNIX timestamp to human-readable UTC string too
    dt_utc_str = datetime.fromtimestamp(dt_unix).strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "timestamp_unix": dt_unix,
        "timestamp_utc": dt_utc_str,
        "lat": coord.get("lat"),
        "lon": coord.get("lon"),
        "aqi_uk": main.get("aqi"),
        "co": comps.get("co"),
        "no": comps.get("no"),
        "no2": comps.get("no2"),
        "o3": comps.get("o3"),
        "so2": comps.get("so2"),
        "pm2_5": comps.get("pm2_5"),
        "pm10": comps.get("pm10"),
        "nh3": comps.get("nh3"),
    }

    return row


def write_header_if_needed(csv_file, fieldnames):
    """
    Create the CSV with header if it doesn't exist.
    """
    file_exists = os.path.isfile(csv_file)

    if not file_exists:
        with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def append_row(csv_file, fieldnames, row):
    """
    Append one row of data to the CSV.
    """
    with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


def main():
    fieldnames = [
        "timestamp_unix",
        "timestamp_utc",
        "lat",
        "lon",
        "aqi_uk",
        "co",
        "no",
        "no2",
        "o3",
        "so2",
        "pm2_5",
        "pm10",
        "nh3",
    ]

    # Ensure CSV has header
    write_header_if_needed(CSV_FILE, fieldnames)

    while True:
        try:
            # 1. Get latest reading
            reading = fetch_air_quality(API_KEY, LAT, LON)

            # 2. Append to CSV
            append_row(CSV_FILE, fieldnames, reading)

            # 3. Print to console for visibility
            print(f"[{reading['timestamp_utc']}] Logged AQI_UK={reading['aqi_uk']} to {CSV_FILE}")

        except Exception as e:
            # If there's any issue (network etc.), log it to console and continue
            print(f"Error: {e}")

        # 4. Sleep for 10 minutes
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
