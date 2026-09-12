import os
import json
import datetime as dt

import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# --------------------------------------------------------------------------------------
# Open-Meteo — free, no API key
#   /v1/forecast      → up to 16 days ahead of "today"
#   /v1/geocoding     → city name → (lat, lon)
# Docs: https://open-meteo.com/en/docs
# --------------------------------------------------------------------------------------
FORECAST_DAYS_MAX = 16

# WMO weather code → human-readable string
WMO_CODE_MAP = {
    0: "Clear",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Dense Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ Slight Hail",
    99: "Thunderstorm w/ Heavy Hail",
}


def _wmo_to_text(code) -> str:
    try:
        return WMO_CODE_MAP.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


def _geocode(place: str) -> tuple[float, float, str] | None:
    """Open-Meteo geocoding — free, no key. Returns (lat, lon, resolved_name)."""
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        r.raise_for_status()
        results = (r.json() or {}).get("results") or []
        if not results:
            return None
        hit = results[0]
        return float(hit["latitude"]), float(hit["longitude"]), hit.get("name", place)
    except Exception:
        return None


def _fetch_open_meteo_forecast(lat: float, lon: float, start_iso: str, days: int) -> list[dict]:
    """Real NWP forecast from Open-Meteo, up to 16 days from today."""
    end_iso = (dt.date.fromisoformat(start_iso) + dt.timedelta(days=days - 1)).isoformat()
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "timezone": "auto",
        "start_date": start_iso,
        "end_date": end_iso,
    }
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
    r.raise_for_status()
    daily = (r.json() or {}).get("daily") or {}

    out = []
    for i, d in enumerate(daily.get("time") or []):
        out.append(
            {
                "date": d,
                "condition": _wmo_to_text(
                    (daily.get("weathercode") or [None] * (i + 1))[i]
                ),
                "temp_high": (daily.get("temperature_2m_max") or [None] * (i + 1))[i],
                "temp_low": (daily.get("temperature_2m_min") or [None] * (i + 1))[i],
                "precipitation_chance": (
                    daily.get("precipitation_probability_max") or [None] * (i + 1)
                )[i],
                "source": "open-meteo-forecast",
            }
        )
    return out


# --------------------------------------------------------------------------------------
# Public API — same signature as before
# --------------------------------------------------------------------------------------
def get_weather(destination: str, start_date: str, duration: int) -> list[dict]:
    """
    Returns a real Open-Meteo forecast for the trip IF the entire trip falls
    inside the free forecast window (next 16 days from today).

    Returns an EMPTY list when:
      - the trip extends past the 16-day horizon, OR
      - the start date is missing/invalid, OR
      - the destination can't be geocoded, OR
      - the API call fails.

    Callers should treat `len(result) == 0` as "no weather info available —
    don't display a Weather tab".

    Inputs:
        destination: e.g. "Istanbul, Turkey"
        start_date:  ISO date string "YYYY-MM-DD"
        duration:    number of days
    """
    try:
        start = dt.date.fromisoformat(start_date)
    except (TypeError, ValueError):
        return []

    if duration <= 0:
        return []

    today = dt.date.today()
    days_until_start = (start - today).days
    forecast_coverage = FORECAST_DAYS_MAX - days_until_start

    # The whole trip must fit inside the available forecast window.
    if forecast_coverage < duration:
        return []

    geo = _geocode(destination)
    if not geo:
        return []

    lat, lon, _resolved_name = geo
    try:
        rows = _fetch_open_meteo_forecast(lat, lon, start.isoformat(), duration)
    except Exception:
        return []

    # If Open-Meteo returned fewer rows than asked (e.g. partial coverage),
    # treat it as "no weather info" rather than showing partial data.
    if len(rows) < duration:
        return []

    return rows


# quick manual test — run this file directly to check it works
if __name__ == "__main__":
    cases = [
        # (label, destination, days_from_today, duration, expected_count)
        ("Short trip, soon",         "Istanbul, Turkey", 3,   4,  4),   # all in window
        ("Exactly fills the window", "Paris, France",    5,   11, 11),  # 11 days fits exactly
        ("One day too long",         "Paris, France",    5,   12, 0),   # 12 doesn't fit
        ("Trip way in the future",   "Tokyo, Japan",    60,   10, 0),   # outside window entirely
        ("Very long trip",           "London, UK",       2,   45, 0),   # way past 14-day window
        ("Geocoding fails",          "Atlantis",         0,   3,  0),   # city not found
        ("Trip starting yesterday",  "Cairo, Egypt",    -1,   3,  3),   # negative offset is fine
        ("Bad start date",           "Dubai, UAE",       0,   3,  0),   # "not-a-date" → returns []
    ]

    # Run the bad-date case by passing a non-ISO string
    import sys
    for label, dest, offset, dur, expected in cases:
        if label == "Bad start date":
            sd = "not-a-date"
        else:
            sd = (dt.date.today() + dt.timedelta(days=offset)).isoformat()
        result = get_weather(dest, sd, dur)
        status = "OK " if len(result) == expected else "FAIL"
        print(f"{status}  {label:32s}  got {len(result)} rows (expected {expected})")
