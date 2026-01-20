from flask import Flask, render_template, request
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("OPENWEATHER_API_KEY")

CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def get_weather(city: str):
    params = {"q": city, "appid": API_KEY, "units": "imperial"}
    r = requests.get(CURRENT_URL, params=params, timeout=10)
    data = r.json()

    if r.status_code == 200:
        return {
            "ok": True,
            "city": data.get("name"),
            "temp": round(data["main"]["temp"]),
            "desc": data["weather"][0]["description"].title(),
            "humidity": data["main"]["humidity"],
            "wind": data["wind"]["speed"],
            "icon": data["weather"][0].get("icon"),
        }

    return {"ok": False, "status": r.status_code, "message": data.get("message", "Unknown error")}


def get_5_day_forecast(city: str):
    params = {"q": city, "appid": API_KEY, "units": "imperial"}
    r = requests.get(FORECAST_URL, params=params, timeout=10)
    data = r.json()

    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "message": data.get("message", "Forecast error")}

    days = {}

    for item in data.get("list", []):
        # item["dt_txt"] looks like "2026-01-19 12:00:00"
        date_str = item["dt_txt"].split(" ")[0]
        temp = item["main"]["temp"]

        if date_str not in days:
            days[date_str] = {
                "temps": [],
                "weather_counts": {},
                "dt": item["dt"],
            }

        days[date_str]["temps"].append(temp)

        # Count descriptions to choose the most common one that day
        w = item["weather"][0]
        key = (w["description"], w["icon"])
        days[date_str]["weather_counts"][key] = days[date_str]["weather_counts"].get(key, 0) + 1

    forecast = []
    # Sort by date so it’s stable
    for date_str in sorted(days.keys())[:5]:
        info = days[date_str]
        dt = datetime.fromtimestamp(info["dt"])

        # Pick the most frequent weather description/icon for the day
        (desc, icon), _count = max(info["weather_counts"].items(), key=lambda kv: kv[1])

        forecast.append({
            "day": dt.strftime("%a"),
            "date": dt.strftime("%b %d"),
            "min": round(min(info["temps"])),
            "max": round(max(info["temps"])),
            "desc": desc.title(),
            "icon": icon,
        })

    return {"ok": True, "days": forecast}


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    forecast = None
    error = None
    city_value = ""

    if request.method == "POST":
        city_value = request.form.get("city", "").strip()

        if not city_value:
            error = "Please enter a city."
        else:
            current = get_weather(city_value)
            if not current["ok"]:
                error = f"Current weather error ({current['status']}): {current['message']}"
            else:
                weather = current

                fc = get_5_day_forecast(city_value)
                if fc["ok"]:
                    forecast = fc["days"]
                else:
                    error = f"Forecast error ({fc['status']}): {fc['message']}"

    return render_template("index.html", weather=weather, forecast=forecast, error=error, city=city_value)


if __name__ == "__main__":
    app.run(debug=True)
