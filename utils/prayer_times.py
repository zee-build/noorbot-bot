import aiohttp, logging
from datetime import date, datetime
from typing import Optional
from config import PRAYER_METHOD, TIMEZONE, get_prayer_method
import pytz

logger = logging.getLogger(__name__)
PRAYER_KEYS   = ["fajr","dhuhr","asr","maghrib","isha"]
PRAYER_NAMES  = {"fajr":"Fajr","dhuhr":"Dhuhr","asr":"Asr","maghrib":"Maghrib","isha":"Isha"}
PRAYER_EMOJIS = {"fajr":"🌙","dhuhr":"☀️","asr":"🌤","maghrib":"🌅","isha":"🌃"}


_ramadan_cache: dict = {}   # {date_str: bool}


async def get_prayer_times(lat, lng, for_date: date = None, country: str = "") -> Optional[dict]:
    if not for_date:
        for_date = date.today()
    method = get_prayer_method(country)
    url = (f"https://api.aladhan.com/v1/timings/"
           f"{for_date.day:02d}-{for_date.month:02d}-{for_date.year}"
           f"?latitude={lat}&longitude={lng}&method={method}")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                t = data["data"]["timings"]
                # Cache Ramadan status from this response
                hijri_month = data["data"]["date"]["hijri"]["month"]["number"]
                key = for_date.isoformat()
                _ramadan_cache[key] = (hijri_month == 9)
                return {k: t[v.capitalize()][:5] for k, v in
                        [("fajr","Fajr"),("dhuhr","Dhuhr"),("asr","Asr"),
                         ("maghrib","Maghrib"),("isha","Isha")]}
    except Exception as e:
        logger.error(f"Prayer time fetch failed: {e}")
        return None


async def is_ramadan(lat=25.2048, lng=55.2708, country: str = "") -> bool:
    """Returns True if today is in Ramadan. Uses cached result if available."""
    today = date.today().isoformat()
    if today in _ramadan_cache:
        return _ramadan_cache[today]
    # Trigger a prayer times fetch to populate cache
    await get_prayer_times(lat, lng, country=country)
    return _ramadan_cache.get(today, False)


async def get_city_coordinates(city: str) -> Optional[dict]:
    """Geocode a city name using Open Nominatim (free, no key)."""
    url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
    headers = {"User-Agent": "NoorBot/2.0"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
                data = await r.json()
                if not data:
                    return None
                return {
                    "city":    data[0].get("display_name","").split(",")[0].strip(),
                    "country": data[0].get("display_name","").split(",")[-1].strip(),
                    "lat":     float(data[0]["lat"]),
                    "lng":     float(data[0]["lon"]),
                }
    except Exception as e:
        logger.error(f"Geocode failed: {e}")
        return None


def minutes_until_prayer(prayer_time_str: str, tz_name: str = TIMEZONE) -> int:
    tz  = pytz.timezone(tz_name)
    now = datetime.now(tz)
    h, m = map(int, prayer_time_str.split(":"))
    prayer_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return int((prayer_dt - now).total_seconds() / 60)


def minutes_since_prayer(prayer_time_str: str, tz_name: str = TIMEZONE) -> int:
    return -minutes_until_prayer(prayer_time_str, tz_name)


def to_12h(time_str: str) -> str:
    """Convert 'HH:MM' (24h) to '5:30 AM' (12h) format."""
    h, m = map(int, time_str.split(":"))
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {period}"


def format_prayer_schedule(times: dict, city: str = "") -> str:
    lines = [f"📅 *Prayer Times{' — ' + city if city else ''}*\n"]
    for key in PRAYER_KEYS:
        lines.append(f"{PRAYER_EMOJIS[key]} *{PRAYER_NAMES[key]}*: `{to_12h(times[key])}`")
    return "\n".join(lines)
