import aiohttp, logging
from datetime import date, datetime
from typing import Optional
from config import PRAYER_METHOD, TIMEZONE
import pytz

logger = logging.getLogger(__name__)
PRAYER_KEYS   = ["fajr","dhuhr","asr","maghrib","isha"]
PRAYER_NAMES  = {"fajr":"Fajr","dhuhr":"Dhuhr","asr":"Asr","maghrib":"Maghrib","isha":"Isha"}
PRAYER_EMOJIS = {"fajr":"🌙","dhuhr":"☀️","asr":"🌤","maghrib":"🌅","isha":"🌃"}

# Aladhan API calculation method per country
# Keys are lowercase country names (from Nominatim) and ISO-2 codes
COUNTRY_PRAYER_METHODS: dict = {
    # Gulf Region
    "ae": 16, "united arab emirates": 16, "dubai": 16,
    "kw": 9,  "kuwait": 9,
    "qa": 10, "qatar": 10,
    "bh": 8,  "bahrain": 8,
    "om": 8,  "oman": 8,
    # Saudi Arabia
    "sa": 4,  "saudi arabia": 4,
    # Levant / North Africa
    "eg": 5,  "egypt": 5,
    "jo": 23, "jordan": 23,
    "ma": 21, "morocco": 21,
    "dz": 19, "algeria": 19,
    "tn": 18, "tunisia": 18,
    # Turkey
    "tr": 13, "turkey": 13, "türkiye": 13,
    # Iran
    "ir": 7,  "iran": 7,
    # South / Central Asia
    "pk": 1,  "pakistan": 1,
    "in": 1,  "india": 1,
    "bd": 1,  "bangladesh": 1,
    "af": 1,  "afghanistan": 1,
    # South-East Asia
    "my": 17, "malaysia": 17,
    "sg": 11, "singapore": 11,
    "id": 20, "indonesia": 20,
    # Europe
    "fr": 12, "france": 12,
    "pt": 22, "portugal": 22,
    "ru": 14, "russia": 14, "russian federation": 14,
    "gb": 3,  "uk": 3, "united kingdom": 3,
    "de": 3,  "germany": 3,
    "nl": 3,  "netherlands": 3,
    "be": 3,  "belgium": 3,
    "se": 3,  "sweden": 3,
    "no": 3,  "norway": 3,
    "dk": 3,  "denmark": 3,
    "it": 3,  "italy": 3,
    "es": 3,  "spain": 3,
    # North America
    "us": 2,  "usa": 2, "united states": 2, "united states of america": 2,
    "ca": 2,  "canada": 2,
    # Oceania
    "au": 3,  "australia": 3,
    "nz": 3,  "new zealand": 3,
}


def get_method_for_country(country: str) -> int:
    """Return the best Aladhan calculation method for the given country name or ISO code."""
    return COUNTRY_PRAYER_METHODS.get(country.strip().lower(), PRAYER_METHOD)


_ramadan_cache: dict = {}   # {date_str: bool}


async def get_prayer_times(lat, lng, for_date: date = None, country: str = "") -> Optional[dict]:
    if not for_date:
        for_date = date.today()
    method = get_method_for_country(country) if country else PRAYER_METHOD
    url = (f"https://api.aladhan.com/v1/timings/"
           f"{for_date.day}-{for_date.month}-{for_date.year}"
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
                times = {k: t[v.capitalize()][:5] for k, v in
                         [("fajr","Fajr"),("dhuhr","Dhuhr"),("asr","Asr"),
                          ("maghrib","Maghrib"),("isha","Isha")]}
                # Capture timezone from API so callers can persist it
                tz_from_api = data["data"]["meta"].get("timezone", "")
                if tz_from_api:
                    times["_tz"] = tz_from_api
                return times
    except Exception as e:
        logger.error(f"Prayer time fetch failed: {e}")
        return None


async def is_ramadan(lat=25.2048, lng=55.2708) -> bool:
    """Returns True if today is in Ramadan. Uses cached result if available."""
    today = date.today().isoformat()
    if today in _ramadan_cache:
        return _ramadan_cache[today]
    # Trigger a prayer times fetch to populate cache
    await get_prayer_times(lat, lng)
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


def fmt12(time_str: str) -> str:
    """Convert 'HH:MM' (24h) to '12:MM AM/PM' for display."""
    h, m = map(int, time_str.split(":"))
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def minutes_until_prayer(prayer_time_str: str, tz_name: str = TIMEZONE) -> int:
    tz  = pytz.timezone(tz_name)
    now = datetime.now(tz)
    h, m = map(int, prayer_time_str.split(":"))
    prayer_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return int((prayer_dt - now).total_seconds() / 60)


def minutes_since_prayer(prayer_time_str: str, tz_name: str = TIMEZONE) -> int:
    return -minutes_until_prayer(prayer_time_str, tz_name)


def format_prayer_schedule(times: dict, city: str = "") -> str:
    lines = [f"📅 *Prayer Times{' — ' + city if city else ''}*\n"]
    for key in PRAYER_KEYS:
        lines.append(f"{PRAYER_EMOJIS[key]} *{PRAYER_NAMES[key]}*: `{fmt12(times[key])}`")
    return "\n".join(lines)
