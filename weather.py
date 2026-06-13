import httpx
import os

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")

async def get_weather(city: str) -> str:
    if not city or not WEATHER_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://api.weatherstack.com/current",
                params={"access_key": WEATHER_API_KEY, "query": city, "units": "m"},
                timeout=10
            )
            data = response.json()
            if "current" not in data:
                return ""
            temp = data["current"]["temperature"]
            feels = data["current"]["feelslike"]
            desc = data["current"]["weather_descriptions"][0]
            humidity = data["current"]["humidity"]
            desc_lower = desc.lower()
            if any(w in desc_lower for w in ["sunny", "clear"]):
                icon = "☀️"
            elif any(w in desc_lower for w in ["partly"]):
                icon = "⛅️"
            elif any(w in desc_lower for w in ["overcast", "cloudy"]):
                icon = "☁️"
            elif any(w in desc_lower for w in ["rain", "drizzle"]):
                icon = "🌧"
            elif any(w in desc_lower for w in ["snow", "blizzard"]):
                icon = "❄️"
            elif any(w in desc_lower for w in ["thunder", "storm"]):
                icon = "⛈"
            elif any(w in desc_lower for w in ["fog", "mist"]):
                icon = "🌫"
            else:
                icon = "🌤"
            return f"{icon} {desc}, {temp}°C (відчувається {feels}°C), вологість {humidity}%"
    except Exception:
        return ""
