import os
import httpx

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")

WEATHER_ICONS = {
    "clear":        "☀️",
    "sunny":        "☀️",
    "partly":       "⛅️",
    "cloudy":       "☁️",
    "overcast":     "☁️",
    "rain":         "🌧",
    "drizzle":      "🌦",
    "snow":         "❄️",
    "sleet":        "🌨",
    "thunder":      "⛈",
    "fog":          "🌫",
    "mist":         "🌫",
    "blizzard":     "🌨",
}


async def get_weather(city: str) -> str:
    if not city:
        return ""

    if WEATHER_API_KEY:
        try:
            return await _fetch_weather(city)
        except Exception:
            pass

    # Fallback без API
    return _mock_weather(city)


async def _fetch_weather(city: str) -> str:
    url = "http://api.weatherstack.com/current"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={
            "access_key": WEATHER_API_KEY,
            "query": city,
            "units": "m"
        }, timeout=10)
        data = response.json()

        if "current" not in data:
            return _mock_weather(city)

        temp = data["current"]["temperature"]
        desc = data["current"]["weather_descriptions"][0].lower()
        icon = "🌤"
        for key, emoji in WEATHER_ICONS.items():
            if key in desc:
                icon = emoji
                break

        return f"{icon} {temp}°C, {data['current']['weather_descriptions'][0]}"


def _mock_weather(city: str) -> str:
    """Повертає заглушку якщо API недоступний"""
    import random
    options = [
        "☀️ +22°C, сонячно",
        "⛅️ +18°C, хмарно",
        "🌧 +15°C, дощить",
        "☁️ +17°C, похмуро",
        "☀️ +25°C, спекотно",
    ]
    return random.choice(options)
