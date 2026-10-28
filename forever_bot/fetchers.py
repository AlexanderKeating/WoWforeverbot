"""
Everything that touches the internet. Rules:
  * every source is isolated: one failure never blocks another or the post
  * every request has a timeout, retries with backoff, and honors 429 Retry-After
  * multiple ways to find each thing (alt feed URLs, RSS autodiscovery, category name variants,
    title keyword matching) instead of one exact lookup
  * on failure, fall back to the last good result (up to STALE_OK_HOURS old)
  * creator content is passed through verbatim: title, link, and their own description only
"""
import asyncio
import html
import logging
import re
import time
import unicodedata
from calendar import timegm
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp
import feedparser

from . import content as C
from .logsetup import Timer, ev, new_run_id

log = logging.getLogger("forever.fetch")

TIMEOUT = aiohttp.ClientTimeout(total=20, connect=8)
RETRIES = 3
STALE_OK_HOURS = 36
NEWS_MAX_AGE_HOURS = 48
UA = "ForeverSherpaBot/1.2 (+discord bot)"


def real_secret(v: str | None) -> str:
    """Treat placeholders typed into a host's env form ('none', 'skip', '-') as not set."""
    v = (v or "").strip()
    return "" if v.lower() in ("", "none", "skip", "-", "n/a", "na", "later", "todo", "x") else v


# ======================================================================= text helpers
def normalize(text: str) -> str:
    """lowercase, strip accents and punctuation (keeps '+'), collapse spaces."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", html.unescape(str(text)))
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = t.replace("’", "'").replace("'", "")
    t = re.sub(r"[^a-z0-9+#]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_ALIASES = [normalize(a) for a in C.FOREVER_ALIASES]
_WEAK = [normalize(a) for a in C.FOREVER_WEAK]
_CTX = set(normalize(a) for a in C.WOW_CONTEXT)


def is_forever(*texts: str) -> bool:
    """True if the text is about WoW: Forever. Tolerates 'WoW: Forever', 'World of Warcraft Forever',
    '#WoWForever', 'Classic+', zone/race names, or bare 'Forever' next to a WoW word."""
    t = " " + normalize(" ".join(x for x in texts if x)) + " "
    squashed = t.replace(" ", "")
    for a in _ALIASES:
        if f" {a} " in t or (len(a.replace(" ", "")) >= 10 and a.replace(" ", "") in squashed):
            return True
    words = set(t.split())
    if any(w in words for w in _WEAK) and words & _CTX:
        return True
    return False


def is_clean(title: str) -> bool:
    low = (title or "").lower()
    squashed = re.sub(r"[^a-z]", "", low)
    return not any(bad in low or bad in squashed for bad in C.TITLE_BLOCKLIST)


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def excerpt(text: str, limit: int = 200) -> str:
    """Creator's own words, cut at a word boundary. No rewording."""
    text = strip_html(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",.;:-–—")
    return cut + "…"


def canonical_url(url: str) -> str:
    try:
        p = urlsplit(url.strip())
        return urlunsplit((p.scheme.lower() or "https", p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:
        return (url or "").strip()


def _entry_time(entry) -> str | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime.fromtimestamp(timegm(st), tz=timezone.utc).isoformat()
            except (OverflowError, ValueError, TypeError):
                continue
    return None


def _age_hours(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except ValueError:
        return None


# ======================================================================= http
class FetchError(Exception):
    pass


async def http_get(session: aiohttp.ClientSession, url: str, *, params=None, headers=None,
                   want_json=False):
    """GET with timeout, retries, exponential backoff and 429 handling. Raises FetchError."""
    last = None
    host = urlsplit(url).netloc
    for attempt in range(RETRIES):
        t0 = time.perf_counter()
        try:
            async with session.get(url, params=params, headers={"User-Agent": UA, **(headers or {})},
                                   timeout=TIMEOUT) as r:
                ms = (time.perf_counter() - t0) * 1000
                ev(log, "http", logging.DEBUG, host=host, path=urlsplit(url).path[:80], status=r.status,
                   ms=ms, attempt=attempt + 1)
                if r.status == 429:
                    wait = min(float(r.headers.get("Retry-After", 2 ** attempt * 2) or 2), 30)
                    last = f"429 rate limited ({url})"
                    ev(log, "http_retry", logging.WARNING, host=host, status=429, wait_s=wait, attempt=attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                if r.status >= 500:
                    last = f"{r.status} server error ({url})"
                    ev(log, "http_retry", logging.WARNING, host=host, status=r.status, attempt=attempt + 1)
                    await asyncio.sleep(2 ** attempt)
                    continue
                if r.status == 401:
                    raise FetchError("401")
                if r.status >= 400:
                    raise FetchError(f"{r.status} ({url})")  # client errors don't get better on retry
                if want_json:
                    return await r.json(content_type=None)
                return await r.text(errors="replace")
        except FetchError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            last = f"{type(e).__name__}: {e} ({url})"
            ev(log, "http_retry", logging.WARNING, host=host, error=type(e).__name__, detail=str(e)[:120],
               ms=(time.perf_counter() - t0) * 1000, attempt=attempt + 1)
            await asyncio.sleep(2 ** attempt)
    raise FetchError(last or f"failed ({url})")


# ======================================================================= news (RSS)
_LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
_ATTR = re.compile(r'(\w+)\s*=\s*["\']([^"\']*)["\']')


def discover_feeds(page_html: str, base: str) -> list[str]:
    out = []
    for tag in _LINK_TAG.findall(page_html or ""):
        a = {k.lower(): v for k, v in _ATTR.findall(tag)}
        if "alternate" in a.get("rel", "").lower() and re.search(r"(rss|atom)\+xml", a.get("type", ""), re.I):
            if a.get("href"):
                out.append(urljoin(base, html.unescape(a["href"])))
    return out


def parse_feed(text: str, source_name: str) -> list[dict]:
    parsed = feedparser.parse(text)
    if not parsed.entries:
        raise FetchError("no entries (not a feed?)")
    items = []
    for e in parsed.entries:
        title = strip_html(e.get("title", ""))
        link = e.get("link") or next((l.get("href") for l in e.get("links", []) if l.get("href")), None)
        if not title or not link:
            continue
        summary = strip_html(e.get("summary", "") or e.get("description", ""))
        items.append({
            "id": "news:" + canonical_url(link),
            "title": title,
            "url": link.strip(),
            "source": source_name,
            "published": _entry_time(e),
            "_match_text": f"{title} {summary} {' '.join(t.get('term', '') for t in e.get('tags', []))}",
        })
    return items


async def fetch_news_source(session, src: dict) -> list[dict]:
    errors = []
    candidates = list(src.get("feeds", []))
    tried = set()
    # 1) known feed URLs, 2) feeds discovered on the homepage
    for phase in (0, 1):
        if phase == 1 and src.get("home"):
            try:
                page = await http_get(session, src["home"])
                candidates = [u for u in discover_feeds(page, src["home"]) if u not in tried]
                ev(log, "feed_autodiscovery", source=src["name"], found=len(candidates),
                   feeds=",".join(candidates)[:200] or "-")
            except FetchError as e:
                errors.append(f"home: {e}")
                candidates = []
        for url in candidates:
            if url in tried:
                continue
            tried.add(url)
            try:
                text = await http_get(session, url)
                items = parse_feed(text, src["name"])
                matched, off_topic, too_old = [], 0, 0
                for it in items:
                    if not is_forever(it.pop("_match_text")):
                        off_topic += 1
                        continue
                    age = _age_hours(it["published"])
                    if age is not None and age > NEWS_MAX_AGE_HOURS:
                        too_old += 1
                        continue
                    matched.append(it)
                ev(log, "feed_ok", source=src["name"], feed=url, phase="known" if phase == 0 else "discovered",
                   entries=len(items), kept=len(matched), off_topic=off_topic, too_old=too_old)
                return matched
            except FetchError as e:
                ev(log, "feed_failed", logging.DEBUG, source=src["name"], feed=url, error=str(e)[:120])
                errors.append(str(e))
    raise FetchError("; ".join(errors[-3:]) or "no usable feed")


def dedupe_news(items: list[dict]) -> list[dict]:
    seen_url, seen_title, out = set(), set(), []
    for it in items:
        k1, k2 = canonical_url(it["url"]), normalize(it["title"])
        if k1 in seen_url or k2 in seen_title:
            continue
        seen_url.add(k1)
        seen_title.add(k2)
        out.append(it)
    out.sort(key=lambda i: i.get("published") or "", reverse=True)
    return out


# ======================================================================= Twitch
class Twitch:
    API = "https://api.twitch.tv/helix"

    def __init__(self, client_id: str, client_secret: str):
        self.cid, self.secret = real_secret(client_id), real_secret(client_secret)
        self._token, self._token_exp = None, 0.0
        self._games = None  # (forever_ids, fallback_id, resolved_at)
        self._users = {}    # login -> (id, display)

    @property
    def configured(self):
        return bool(self.cid and self.secret)

    async def _auth(self, session):
        async with session.post("https://id.twitch.tv/oauth2/token", timeout=TIMEOUT, params={
            "client_id": self.cid, "client_secret": self.secret, "grant_type": "client_credentials"}) as r:
            if r.status != 200:
                raise FetchError(f"twitch auth {r.status}")
            j = await r.json(content_type=None)
        self._token = j["access_token"]
        self._token_exp = time.time() + int(j.get("expires_in", 3600)) - 120

    async def get(self, session, path, params):
        for attempt in (0, 1):
            if not self._token or time.time() > self._token_exp:
                await self._auth(session)
            try:
                return await http_get(session, f"{self.API}/{path}", params=params, want_json=True,
                                      headers={"Client-Id": self.cid, "Authorization": f"Bearer {self._token}"})
            except FetchError as e:
                if str(e) == "401" and attempt == 0:
                    self._token = None  # token revoked/expired early: refresh once
                    continue
                raise

    async def resolve_games(self, session):
        if self._games and time.time() - self._games[2] < 6 * 3600:
            return self._games[0], self._games[1]
        forever_ids, fallback = set(), None
        names = C.TWITCH_GAME_NAMES + [C.TWITCH_FALLBACK_GAME]
        j = await self.get(session, "games", [("name", n) for n in names])
        for g in (j or {}).get("data", []):
            n = normalize(g.get("name"))
            if n == normalize(C.TWITCH_FALLBACK_GAME):
                fallback = g["id"]
            elif "forever" in n:
                forever_ids.add(g["id"])
        if not forever_ids:  # names didn't match exactly: search instead
            for q in ("world of warcraft forever", "wow forever"):
                try:
                    s = await self.get(session, "search/categories", {"query": q, "first": 20})
                except FetchError:
                    continue
                for g in (s or {}).get("data", []):
                    n = normalize(g.get("name"))
                    if "forever" in n and ("warcraft" in n or "wow" in n.split()):
                        forever_ids.add(g["id"])
                if forever_ids:
                    break
        if not forever_ids and not fallback:
            raise FetchError("no Twitch category found")
        ev(log, "twitch_categories", forever_ids=",".join(sorted(forever_ids)) or "none", fallback_id=fallback,
           mode="forever_category" if forever_ids else "wow_category_title_match")
        self._games = (forever_ids, fallback, time.time())
        return forever_ids, fallback

    async def resolve_users(self, session, logins):
        need = [l.lower() for l in logins if l.lower() not in self._users]
        for i in range(0, len(need), 100):
            j = await self.get(session, "users", [("login", l) for l in need[i:i + 100]])
            found = {u["login"].lower(): (u["id"], u.get("display_name") or u["login"]) for u in j.get("data", [])}
            self._users.update(found)
            for l in need[i:i + 100]:
                if l not in found:
                    ev(log, "twitch_login_not_found", logging.WARNING, login=l, hint="renamed or banned? edit STREAMERS in content.py")
                    self._users[l] = (None, l)
        return {l: self._users[l.lower()] for l in logins if self._users.get(l.lower(), (None,))[0]}

    async def top_clips(self, session, limit=6) -> list[dict]:
        forever_ids, fallback = await self.resolve_games(session)
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw, pinned = {}, set()

        async def grab(params, is_pinned=False):
            try:
                j = await self.get(session, "clips", {**params, "started_at": since, "first": 20})
            except FetchError as e:
                ev(log, "twitch_clips_failed", logging.WARNING, params=str(params), error=str(e)[:120])
                return
            for c in (j or {}).get("data", []):
                raw.setdefault(c["id"], c)
                if is_pinned:
                    pinned.add(c["id"])

        tasks = [grab({"game_id": g}) for g in forever_ids]
        if not forever_ids and fallback:
            tasks.append(grab({"game_id": fallback}))
        users = await self.resolve_users(session, C.STREAMERS)
        tasks += [grab({"broadcaster_id": uid}, True) for uid, _ in users.values()]
        await asyncio.gather(*tasks)

        out, loose, drop_topic, drop_clean = [], [], 0, 0
        for cid, c in raw.items():
            title = (c.get("title") or "").strip()
            gid = c.get("game_id")
            strict = gid in forever_ids or is_forever(title)
            # 1.3: until Twitch has a Forever category, also accept WoW-category clips from the
            # streamers we follow. They're labeled as WoW clips, never as Forever.
            is_loose = (not strict and C.CLIPS_LOOSE_UNTIL_CATEGORY and not forever_ids
                        and cid in pinned and fallback and gid == fallback)
            if not title or not (strict or is_loose):
                drop_topic += 1
                continue
            if not is_clean(title):
                drop_clean += 1
                continue
            score = c.get("view_count", 0) * (1.5 if cid in pinned else 1.0)
            item = {"id": "twitch:" + cid, "url": c["url"], "title": title,
                    "author": c.get("broadcaster_name") or "", "views": c.get("view_count", 0),
                    "published": c.get("created_at"), "_score": score}
            if is_loose:
                item["loose"] = True
            (out if strict else loose).append(item)
        for lst in (out, loose):
            lst.sort(key=lambda x: x["_score"], reverse=True)
        # 1.6.1: one Forever clip per streamer, skip near-duplicate titles and barely-watched clips
        kept, authors, titles = [], set(), []
        for o in out:
            t = normalize(o["title"])
            if o["author"].lower() in authors or o["views"] < C.CLIP_MIN_VIEWS:
                continue
            if any(t == x or (len(t) > 8 and (t in x or x in t)) for x in titles):
                continue
            kept.append(o)
            authors.add(o["author"].lower())
            titles.append(t)
        out = kept
        # Forever clips first; top up with at most C.CLIPS_LOOSE_MAX WoW clips, one per streamer
        seen_authors = set()
        for o in loose:
            if len(out) >= limit or sum(1 for x in out if x.get("loose")) >= C.CLIPS_LOOSE_MAX:
                break
            if o["author"] in seen_authors or o["author"].lower() in authors:
                continue
            seen_authors.add(o["author"])
            out.append(o)
        for o in out:
            o.pop("_score", None)
        ev(log, "twitch_clips", raw=len(raw), pinned_streamers=len(users), from_pinned=len(pinned),
           kept=len(out), loose=sum(1 for x in out if x.get("loose")), dropped_off_topic=drop_topic,
           dropped_profanity=drop_clean, top=(out[0]["author"] + ":" + str(out[0]["views"])) if out else "-")
        return out[:limit]


# ======================================================================= YouTube Data API (auto top videos)
class YouTube:
    """Finds the most-viewed Forever videos of the last 24h.
    Free quota is 10,000 units/day; a search costs 100, so we search at most every 2 hours
    (~1,250 units/day) and reuse the result in between."""
    API = "https://www.googleapis.com/youtube/v3"
    SEARCH_EVERY = 2 * 3600
    QUERY = '"wow forever"|"world of warcraft forever"|"wow: forever"'

    def __init__(self, api_key: str):
        self.key = real_secret(api_key)
        self._last, self._last_at = None, 0.0

    @property
    def configured(self):
        return bool(self.key)

    async def _get(self, session, path, params):
        try:
            return await http_get(session, f"{self.API}/{path}", params={**params, "key": self.key}, want_json=True)
        except FetchError as e:
            if str(e).startswith("403"):  # quota used up or key restricted: back off until next window
                self._last_at = time.time()
                ev(log, "youtube_403", logging.ERROR, path=path,
                   hint="quota used up, or key not enabled/restricted for YouTube Data API v3")
                raise FetchError("403 (quota exceeded or key not enabled for YouTube Data API v3)")
            raise

    async def top_videos(self, session, limit=5) -> list[dict]:
        if self._last is not None and time.time() - self._last_at < self.SEARCH_EVERY:
            ev(log, "youtube_cached", logging.DEBUG, videos=len(self._last),
               next_search_min=(self.SEARCH_EVERY - (time.time() - self._last_at)) / 60)
            return self._last
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        s = await self._get(session, "search", {
            "part": "snippet", "q": self.QUERY, "type": "video", "order": "viewCount",
            "publishedAfter": since, "maxResults": 25, "relevanceLanguage": "en", "safeSearch": "moderate"})
        items = [i for i in (s or {}).get("items", []) if (i.get("id") or {}).get("videoId")]
        if not items:
            self._last, self._last_at = [], time.time()
            return []
        ids = [i["id"]["videoId"] for i in items]
        stats = {}
        try:  # 1 unit; full description + view counts
            v = await self._get(session, "videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids)})
            stats = {x["id"]: x for x in (v or {}).get("items", [])}
        except FetchError as e:
            ev(log, "youtube_stats_failed", logging.WARNING, error=str(e)[:120], fallback="search order")
        out, drop = [], {"off_topic": 0, "profanity": 0, "short": 0}
        for rank, it in enumerate(items):
            vid = it["id"]["videoId"]
            full = stats.get(vid, {})
            sn = full.get("snippet") or it.get("snippet") or {}
            title = html.unescape(sn.get("title", "")).strip()
            desc = sn.get("description", "")
            dur = (full.get("contentDetails") or {}).get("duration", "")
            if not title or not is_forever(title, desc, " ".join(sn.get("tags", []) or [])):
                drop["off_topic"] += 1
                continue
            if not is_clean(title):
                drop["profanity"] += 1
                continue
            if re.fullmatch(r"PT(\d|[1-5]\d)S", dur or ""):  # skip Shorts (<60s)
                drop["short"] += 1
                continue
            views = int((full.get("statistics") or {}).get("viewCount", 0) or 0)
            out.append({"id": "yt:" + vid, "url": f"https://www.youtube.com/watch?v={vid}", "title": title,
                        "author": sn.get("channelTitle", ""), "description": excerpt(desc, 200),
                        "views": views, "published": sn.get("publishedAt"), "_rank": (-views, rank)})
        out.sort(key=lambda x: x["_rank"])
        for o in out:
            o.pop("_rank", None)
        self._last, self._last_at = out[:limit], time.time()
        ev(log, "youtube_search", results=len(items), kept=len(out), quota_units=101,
           **{f"dropped_{k}": v for k, v in drop.items()},
           top=(out[0]["author"] + ":" + str(out[0]["views"])) if out else "-")
        return self._last


# ======================================================================= YouTube (RSS, pinned channels, no key)
async def fetch_youtube(session) -> list[dict]:
    out, errors = [], []
    for name, cid in C.YOUTUBE_CHANNELS.items():
        try:
            text = await http_get(session, "https://www.youtube.com/feeds/videos.xml", params={"channel_id": cid})
            for e in feedparser.parse(text).entries[:10]:
                title = strip_html(e.get("title", ""))
                desc = e.get("media_description") or e.get("summary") or ""
                link = e.get("link")
                age = _age_hours(_entry_time(e))
                if not (title and link) or (age is not None and age > NEWS_MAX_AGE_HOURS):
                    continue
                if not is_forever(title, desc) or not is_clean(title):
                    continue
                out.append({"id": "yt:" + (e.get("yt_videoid") or canonical_url(link)), "url": link,
                            "title": title, "author": e.get("author") or name,
                            "description": excerpt(desc, 200), "published": _entry_time(e)})
        except FetchError as e:
            errors.append(f"{name}: {e}")
    if errors and not out and len(errors) == len(C.YOUTUBE_CHANNELS):
        raise FetchError("; ".join(errors[:3]))
    out.sort(key=lambda i: i.get("published") or "", reverse=True)
    return out


# ======================================================================= aggregate
async def _guarded(store, key, coro_fn):
    """Run one source. Success -> cache. Failure -> last good result if fresh enough."""
    t = Timer().__enter__()
    try:
        data = await coro_fn()
        store.cache_put(key, data)
        ev(log, "source_ok", source=key, items=len(data), ms=t.elapsed_ms)
        return data, "ok"
    except Exception as e:  # noqa: BLE001 -- isolation is the point
        unexpected = not isinstance(e, FetchError)
        cached, at = store.cache_get(key)
        if cached is not None and at and time.time() - at < STALE_OK_HOURS * 3600:
            age_h = int((time.time() - at) / 3600)
            ev(log, "source_stale", logging.WARNING, exc_info=e if unexpected else None, source=key,
               using_cache_h=age_h, items=len(cached), error=str(e)[:160], ms=t.elapsed_ms)
            return cached, f"stale ({age_h}h old): {str(e)[:80]}"
        ev(log, "source_down", logging.ERROR if unexpected else logging.WARNING, exc_info=e if unexpected else None,
           source=key, error=str(e)[:160], ms=t.elapsed_ms)
        return [], f"down: {str(e)[:100]}"


async def _youtube_combined(session, yt):
    """API top videos (if keyed) plus pinned-channel RSS; one failing doesn't sink the other."""
    results, errors = [], []
    if yt and yt.configured:
        try:
            results += await yt.top_videos(session)
        except FetchError as e:
            errors.append(f"api: {e}")
    if C.YOUTUBE_CHANNELS:
        try:
            results += await fetch_youtube(session)
        except FetchError as e:
            errors.append(f"rss: {e}")
    if errors and not results:
        raise FetchError("; ".join(errors))
    seen, out = set(), []
    for v in results:
        if v["id"] not in seen:
            seen.add(v["id"])
            out.append(v)
    out.sort(key=lambda v: v.get("views", 0), reverse=True)
    return out


async def refresh_all(store, twitch: Twitch | None, youtube: "YouTube | None" = None) -> dict:
    run, t = new_run_id(), Timer().__enter__()
    async with aiohttp.ClientSession() as session:
        jobs = {}
        for src in C.NEWS_SOURCES:
            jobs["news:" + src["name"]] = (lambda s=src: fetch_news_source(session, s))
        if twitch and twitch.configured:
            jobs["twitch"] = lambda: twitch.top_clips(session)
        if C.SHOW_YOUTUBE and ((youtube and youtube.configured) or C.YOUTUBE_CHANNELS):
            jobs["youtube"] = lambda: _youtube_combined(session, youtube)
        keys = list(jobs)
        results = await asyncio.gather(*(_guarded(store, k, jobs[k]) for k in keys))

    snap = {"news": [], "clips": [], "videos": [], "health": {}, "fetched_at": time.time()}
    for k, (data, status) in zip(keys, results):
        snap["health"][k] = status
        if k.startswith("news:"):
            snap["news"].extend(data)
        elif k == "twitch":
            snap["clips"] = data
        elif k == "youtube":
            snap["videos"] = data
    snap["news"] = dedupe_news(snap["news"])
    if not (twitch and twitch.configured):
        snap["health"]["twitch"] = "not configured"
    if "youtube" not in snap["health"]:
        snap["health"]["youtube"] = "off" if not C.SHOW_YOUTUBE else "not configured"
    h = snap["health"]
    ev(log, "refresh_done", run=run, ms=t.elapsed_ms,
       ok=sum(v == "ok" for v in h.values()), total=len(h),
       down=",".join(k for k, v in h.items() if v.startswith("down")) or "-",
       stale=",".join(k for k, v in h.items() if v.startswith("stale")) or "-",
       news=len(snap["news"]), clips=len(snap["clips"]), videos=len(snap["videos"]))
    return snap
