"""1.8.1: forgiving input parsing for admin commands.

On Oct 29 an admin needed three tries at /setup because the time zone had to be typed exactly
"America/Chicago" ("central" and "america/chicago" were both rejected). Everything here accepts the
ways people actually type things and, when it can't, says what it got and what would work.
"""
import difflib
import re
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

# Common names, abbreviations and cities -> IANA zone. Keys are normalized (see _norm).
TZ_ALIASES = {
    # US
    "central": "America/Chicago", "ct": "America/Chicago", "cst": "America/Chicago", "cdt": "America/Chicago",
    "us central": "America/Chicago", "central time": "America/Chicago", "chicago": "America/Chicago",
    "texas": "America/Chicago", "dallas": "America/Chicago", "houston": "America/Chicago",
    "eastern": "America/New_York", "et": "America/New_York", "est": "America/New_York", "edt": "America/New_York",
    "us eastern": "America/New_York", "eastern time": "America/New_York", "new york": "America/New_York",
    "nyc": "America/New_York", "ny": "America/New_York", "miami": "America/New_York", "atlanta": "America/New_York",
    "mountain": "America/Denver", "mt": "America/Denver", "mst": "America/Denver", "mdt": "America/Denver",
    "us mountain": "America/Denver", "mountain time": "America/Denver", "denver": "America/Denver",
    "arizona": "America/Phoenix", "phoenix": "America/Phoenix",
    "pacific": "America/Los_Angeles", "pt": "America/Los_Angeles", "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles", "us pacific": "America/Los_Angeles", "pacific time": "America/Los_Angeles",
    "la": "America/Los_Angeles", "los angeles": "America/Los_Angeles", "california": "America/Los_Angeles",
    "seattle": "America/Los_Angeles", "san francisco": "America/Los_Angeles",
    "alaska": "America/Anchorage", "akst": "America/Anchorage", "hawaii": "Pacific/Honolulu", "hst": "Pacific/Honolulu",
    # Canada / Latin America
    "atlantic": "America/Halifax", "ast": "America/Halifax", "newfoundland": "America/St_Johns",
    "toronto": "America/Toronto", "vancouver": "America/Vancouver", "mexico city": "America/Mexico_City",
    "brazil": "America/Sao_Paulo", "brt": "America/Sao_Paulo", "sao paulo": "America/Sao_Paulo",
    "argentina": "America/Argentina/Buenos_Aires", "buenos aires": "America/Argentina/Buenos_Aires",
    # Europe
    "uk": "Europe/London", "gmt": "Europe/London", "bst": "Europe/London", "britain": "Europe/London",
    "england": "Europe/London", "ireland": "Europe/Dublin",
    "cet": "Europe/Paris", "cest": "Europe/Paris", "central european": "Europe/Paris", "europe": "Europe/Paris",
    "france": "Europe/Paris", "germany": "Europe/Berlin", "spain": "Europe/Madrid", "italy": "Europe/Rome",
    "netherlands": "Europe/Amsterdam", "belgium": "Europe/Brussels", "sweden": "Europe/Stockholm",
    "norway": "Europe/Oslo", "denmark": "Europe/Copenhagen", "poland": "Europe/Warsaw", "austria": "Europe/Vienna",
    "switzerland": "Europe/Zurich", "portugal": "Europe/Lisbon", "wet": "Europe/Lisbon",
    "eet": "Europe/Helsinki", "eest": "Europe/Helsinki", "eastern european": "Europe/Helsinki",
    "finland": "Europe/Helsinki", "suomi": "Europe/Helsinki", "greece": "Europe/Athens", "romania": "Europe/Bucharest",
    "turkey": "Europe/Istanbul", "russia": "Europe/Moscow", "msk": "Europe/Moscow", "moscow": "Europe/Moscow",
    "ukraine": "Europe/Kyiv", "kiev": "Europe/Kyiv",
    # Asia / Oceania
    "india": "Asia/Kolkata", "ist": "Asia/Kolkata", "japan": "Asia/Tokyo", "jst": "Asia/Tokyo",
    "korea": "Asia/Seoul", "kst": "Asia/Seoul", "china": "Asia/Shanghai", "singapore": "Asia/Singapore",
    "sgt": "Asia/Singapore", "philippines": "Asia/Manila", "aest": "Australia/Sydney", "aedt": "Australia/Sydney",
    "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne", "brisbane": "Australia/Brisbane",
    "awst": "Australia/Perth", "perth": "Australia/Perth", "acst": "Australia/Adelaide", "adelaide": "Australia/Adelaide",
    "nz": "Pacific/Auckland", "nzst": "Pacific/Auckland", "nzdt": "Pacific/Auckland", "new zealand": "Pacific/Auckland",
    "auckland": "Pacific/Auckland",
    # Universal
    "utc": "UTC", "z": "UTC", "zulu": "UTC", "universal": "UTC",
}

# Shown first in autocomplete when the box is empty.
POPULAR_TZ = [
    ("US Central (Chicago)", "America/Chicago"), ("US Eastern (New York)", "America/New_York"),
    ("US Mountain (Denver)", "America/Denver"), ("US Pacific (Los Angeles)", "America/Los_Angeles"),
    ("Arizona (Phoenix)", "America/Phoenix"), ("UK (London)", "Europe/London"),
    ("Central Europe (Paris, Berlin)", "Europe/Paris"), ("Eastern Europe (Helsinki)", "Europe/Helsinki"),
    ("Brazil (São Paulo)", "America/Sao_Paulo"), ("Australia East (Sydney)", "Australia/Sydney"),
    ("UTC", "UTC"),
]


def _norm(s: str) -> str:
    s = (s or "").strip().lower().replace("_", " ").replace("-", " ").replace(".", "")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\b(standard|daylight|summer)\b", "", s)  # "Central Standard Time" -> "central time"
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*\btimezone\b|\s*\btime zone\b", "", s).strip()
    return s


@lru_cache(maxsize=1)
def _zones() -> dict:
    """normalized name -> real IANA name, for every zone, plus city-only keys ("helsinki")."""
    by_name, by_city = {}, {}
    for z in available_timezones():
        if z.startswith(("Etc/", "SystemV/", "posix/", "right/")) or "/" not in z and z != "UTC":
            continue
        by_name[_norm(z.replace("/", " / "))] = z
        by_name[z.lower()] = z
        city = _norm(z.rsplit("/", 1)[-1])
        if city not in by_city or z.count("/") < by_city[city].count("/"):
            by_city[city] = z
    return {"name": by_name, "city": by_city}


_OFFSET = re.compile(r"^(?:utc|gmt)?\s*([+-])\s*(\d{1,2})(?::?00)?$")


def resolve_tz(text: str) -> str | None:
    """'central', 'CST', 'america/chicago', 'New York', 'Helsinki', 'UTC-6' -> an IANA zone, or None."""
    raw = (text or "").strip()
    if not raw:
        return None
    raw = re.sub(r"^american\b", "America", raw, flags=re.I)  # 1.10.7: common typo, 'American/Chicago'
    try:  # exact IANA name: the common case
        ZoneInfo(raw)
        if "/" in raw or raw.upper() == "UTC":
            return raw if raw != "utc" else "UTC"
    except (ZoneInfoNotFoundError, ValueError, OSError):  # 1.10.7: 'America' is a folder in tzdata -> IsADirectoryError
        pass
    n = _norm(raw)
    for key in (n, re.sub(r"\btime$", "", n).strip()):
        if key in TZ_ALIASES:
            return TZ_ALIASES[key]
    z = _zones()
    if raw.lower() in z["name"]:
        return z["name"][raw.lower()]
    if _norm(raw.replace("/", " / ")) in z["name"]:
        return z["name"][_norm(raw.replace("/", " / "))]
    if n in z["city"]:
        return z["city"][n]
    m = _OFFSET.match(raw.lower().replace(" ", ""))
    if m:  # fixed offsets: Etc/GMT signs are inverted (UTC-6 is Etc/GMT+6)
        sign, hours = m.group(1), int(m.group(2))
        if hours == 0:
            return "UTC"
        if hours <= 14:
            return f"Etc/GMT{'+' if sign == '-' else '-'}{hours}"
    return None


def suggest_tz(text: str, n: int = 3) -> list[str]:
    """Closest real zones for a typo, for the error message."""
    key = _norm(text)
    z = _zones()
    out = []
    for pool in (TZ_ALIASES, z["city"]):  # friendly names first, then cities
        for h in difflib.get_close_matches(key, list(pool), n=n, cutoff=0.6):
            if pool[h] not in out:
                out.append(pool[h])
    return out[:n]


def tz_choices(current: str, limit: int = 25) -> list[tuple[str, str]]:
    """Autocomplete: (label, value) pairs for what's typed so far."""
    q = _norm(current)
    if not q:
        return POPULAR_TZ[:limit]
    out, seen = [], set()

    def add(label, value):
        if value not in seen and len(out) < limit:
            seen.add(value)
            out.append((label[:100], value))
    exact = resolve_tz(current)
    if exact:
        add(f"{exact} (from \"{current.strip()[:40]}\")" if exact.lower() != current.strip().lower() else exact, exact)
    for label, value in POPULAR_TZ:
        if q in _norm(label) or q in value.lower():
            add(label, value)
    for alias, value in TZ_ALIASES.items():
        if alias.startswith(q):
            add(f"{value} ({alias})", value)
    names = sorted(set(_zones()["name"].values()))
    for name in names:  # city starts with what's typed, then anywhere in the name
        if _norm(name.rsplit("/", 1)[-1]).startswith(q):
            add(name, name)
    for name in names:
        if q in _norm(name.replace("/", " ")):
            add(name, name)
    return out


def bad_tz_text(text: str) -> str:
    sug = suggest_tz(text)
    hint = f" Did you mean {' or '.join(f'`{s}`' for s in sug)}?" if sug else ""
    return (f"I don't recognize the time zone `{(text or '').strip()[:60]}`.{hint}\n"
            "-# Try a name like `Central`, `Eastern`, `Pacific`, `UK`, `CET`, a city like `Helsinki`, "
            "or a full zone like `America/Chicago`. The box suggests matches as you type.")
