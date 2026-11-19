"""
Wrappers around the free third-party APIs. Each function returns plain dicts/lists
and raises ApiError with a user-friendly message on failure.
"""
import requests
from django.conf import settings
from django.core.cache import cache

TIMEOUT = 8


class ApiError(Exception):
    pass


def _get_json(url, params=None):
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException:
        raise ApiError("Could not reach the service. Check your internet connection.")
    if resp.status_code == 404:
        raise ApiError("No results found.")
    if resp.status_code in (400, 401, 403):
        raise ApiError("The API rejected the request (check your API key / quota).")
    if not resp.ok:
        raise ApiError(f"Service error ({resp.status_code}).")
    try:
        return resp.json()
    except ValueError:
        raise ApiError("Unexpected response from the service.")


# ------------------------------------------------------------ Google Books
def search_books(query):
    params = {"q": query, "maxResults": 6, "printType": "books"}
    if settings.GOOGLE_BOOKS_API_KEY:
        params["key"] = settings.GOOGLE_BOOKS_API_KEY
    data = _get_json("https://www.googleapis.com/books/v1/volumes", params)
    results = []
    for item in data.get("items", []):
        info = item.get("volumeInfo", {})
        results.append({
            "title": info.get("title", "Untitled"),
            "subtitle": ", ".join(info.get("authors", [])) or "Unknown author",
            "url": info.get("infoLink", ""),
            "image": (info.get("imageLinks", {}).get("thumbnail") or "").replace("http://", "https://"),
        })
    if not results:
        raise ApiError("No books found.")
    return results


# ------------------------------------------------------------ Dictionary
def define_word(word):
    word = word.strip().split()[0] if word.strip() else ""
    if not word:
        raise ApiError("Enter a word.")
    data = _get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{requests.utils.quote(word)}")
    if not isinstance(data, list) or not data:
        raise ApiError("No definition found.")
    entry = data[0]
    meanings = []
    for m in entry.get("meanings", [])[:3]:
        defs = m.get("definitions", [])
        if defs:
            meanings.append({
                "part_of_speech": m.get("partOfSpeech", ""),
                "definition": defs[0].get("definition", ""),
                "example": defs[0].get("example", ""),
            })
    return {"word": entry.get("word", word), "phonetic": entry.get("phonetic", ""), "meanings": meanings}


# ------------------------------------------------------------ YouTube
def search_videos(query):
    if not settings.YOUTUBE_API_KEY:
        raise ApiError("YouTube API key is not set. See README step 4.")
    data = _get_json("https://www.googleapis.com/youtube/v3/search", {
        "part": "snippet", "q": query + " tutorial", "type": "video", "maxResults": 6,
        "safeSearch": "strict", "key": settings.YOUTUBE_API_KEY,
    })
    results = []
    for item in data.get("items", []):
        vid = item.get("id", {}).get("videoId")
        sn = item.get("snippet", {})
        if vid:
            results.append({
                "title": sn.get("title", ""),
                "subtitle": sn.get("channelTitle", ""),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "image": sn.get("thumbnails", {}).get("default", {}).get("url", ""),
            })
    if not results:
        raise ApiError("No videos found.")
    return results


# ------------------------------------------------------------ ZenQuotes
FALLBACK_QUOTE = {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"}


def daily_quote():
    cached = cache.get("daily_quote")
    if cached:
        return cached
    try:
        data = _get_json("https://zenquotes.io/api/today")
        quote = {"text": data[0]["q"], "author": data[0]["a"]}
    except (ApiError, KeyError, IndexError, TypeError):
        return FALLBACK_QUOTE
    cache.set("daily_quote", quote, 60 * 60 * 6)
    return quote


# ------------------------------------------------------------ Open-Meteo (weather)
WEATHER_CODES = {
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Violent showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


def _suggestion(code, temp):
    if code >= 95:
        return "Thunderstorm outside - stay in, unplug and tackle your deep-focus tasks."
    if 51 <= code <= 82:
        return "Rainy day - perfect for staying in and finishing your reading and writing tasks."
    if temp is not None and temp >= 33:
        return "It's very hot - study somewhere cool and keep water nearby."
    if code in (0, 1, 2):
        return "Nice weather - take a short study break outside between tasks."
    return "Calm conditions - a good time for a steady study session."


def weather_for_city(city):
    city = (city or settings.DEFAULT_CITY).strip()
    cache_key = f"weather:{city.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    geo = _get_json("https://geocoding-api.open-meteo.com/v1/search", {"name": city, "count": 1})
    if not geo.get("results"):
        raise ApiError(f'City "{city}" not found.')
    place = geo["results"][0]
    wx = _get_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": place["latitude"], "longitude": place["longitude"],
        "current": "temperature_2m,weather_code", "timezone": "auto",
    })
    cur = wx.get("current", {})
    code, temp = cur.get("weather_code", 0), cur.get("temperature_2m")
    result = {
        "city": f'{place["name"]}, {place.get("country", "")}'.strip(", "),
        "temp": temp,
        "condition": WEATHER_CODES.get(code, "Unknown"),
        "suggestion": _suggestion(code, temp),
    }
    cache.set(cache_key, result, 60 * 15)
    return result
