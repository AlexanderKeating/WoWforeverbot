"""
WoW: Forever service status (1.6).

There's no official status API for Forever (it's realmless, so Blizzard's realm status page doesn't
list it). The official source is Blizzard Customer Support, which posts outages, maintenance and
fixes on Bluesky. Bluesky has a free public API, no key needed.

The watcher keeps only posts about Forever, or about Battle.net-wide outages that would also take
Forever down. "All good" posts are never news, so only problems, maintenance and the follow-up
"resolved" posts go out.

Starts in watch-only mode (C.STATUS_POST_TO_CHANNELS = False): it logs event=status_would_post so
we can check the matching on real posts before anything reaches a channel.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

from . import content as C
from .fetchers import FetchError, http_get, is_forever
from .logsetup import ev

log = logging.getLogger("forever.status")

BSKY_FEED = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"

_PROBLEM = re.compile(r"\b(investigat\w*|outage|issue[s]?|problem[s]?|disconnect\w*|latency|lag|unable|"
                      r"can(?:no|')t (?:log|connect)|login|queue[s]?|down|error[s]?|degraded|unavailable)\b", re.I)
_MAINT = re.compile(r"\b(maintenance|restart\w*|patch(?:ing)?|offline for)\b", re.I)
_RESOLVED = re.compile(r"\b(resolved|fixed|restored|back (?:up|online)|now (?:be )?able|is now available|"
                       r"(?:has|have) (?:been )?completed|complete[d]? (?:and|now)|stable again)\b", re.I)
_WIDE = re.compile(r"\b(battle\.net|all (?:blizzard )?games|account services|log ?in services)\b", re.I)


def classify(text: str) -> str | None:
    """'resolved' | 'maintenance' | 'problem' | None (not something worth posting)."""
    if _RESOLVED.search(text):
        return "resolved"
    if _MAINT.search(text):
        return "maintenance"
    if _PROBLEM.search(text):
        return "problem"
    return None


def relevant(text: str) -> bool:
    """About Forever, or a Battle.net-wide outage that would hit Forever too."""
    if is_forever(text):
        return True
    return bool(_WIDE.search(text) and (_PROBLEM.search(text) or _MAINT.search(text)))


def post_url(uri: str, handle: str) -> str:
    return f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}"


async def fetch_bluesky(session, handle: str, limit: int = 30) -> list[dict]:
    """Recent original posts (no reposts or replies) from one Bluesky account."""
    j = await http_get(session, BSKY_FEED, params={"actor": handle, "limit": str(limit),
                                                   "filter": "posts_no_replies"}, want_json=True)
    if not isinstance(j, dict) or "feed" not in j:
        raise FetchError("unexpected Bluesky response shape")
    out = []
    for item in j.get("feed", []):
        if item.get("reason"):  # a repost
            continue
        p = item.get("post") or {}
        rec = p.get("record") or {}
        text = (rec.get("text") or "").strip()
        if not text or not p.get("uri"):
            continue
        out.append({"id": "bsky:" + p["uri"], "text": text, "created": rec.get("createdAt") or p.get("indexedAt"),
                    "url": post_url(p["uri"], (p.get("author") or {}).get("handle") or handle)})
    return out


def _age_h(iso: str | None, now: datetime) -> float:
    try:
        t = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return (now - t).total_seconds() / 3600
    except ValueError:
        return 999.0


def pick_updates(posts: list[dict], seen: set, now: datetime, max_age_h: float = C.STATUS_MAX_AGE_H) -> list[dict]:
    """New, recent, relevant, non-'all good' posts, oldest first, each tagged with its kind."""
    out = []
    for p in posts:
        if p["id"] in seen or _age_h(p["created"], now) > max_age_h:
            continue
        if not relevant(p["text"]):
            continue
        kind = classify(p["text"])
        if not kind:
            continue
        out.append({**p, "kind": kind})
    return sorted(out, key=lambda p: p["created"] or "")


KIND_STYLE = {"problem": ("⚠️", "Blizzard is looking into a problem", 0xE8A33D),
              "maintenance": ("🛠️", "Maintenance", 0x5B8DEF),
              "resolved": ("✅", "Fixed", 0x3BA55D)}


def status_embed(update: dict, source_name: str) -> dict:
    emoji, label, color = KIND_STYLE[update["kind"]]
    when = ""
    try:
        t = datetime.fromisoformat(update["created"].replace("Z", "+00:00"))
        when = f" · <t:{int(t.timestamp())}:R>"
    except (ValueError, AttributeError):
        pass
    text = update["text"]
    return {"title": f"{emoji} WoW: Forever service update · {label}", "color": color,
            "description": f"> {text[:1500].replace(chr(10), chr(10) + '> ')}\n\n[Read it from {source_name}]({update['url']}){when}",
            "footer": {"text": "Official Blizzard Support post · Turn these off with /statusalerts"}}


async def check(session, store) -> list[dict]:
    """Fetch every source, return the new updates to post. Marks everything fetched as seen."""
    seen = set((store.cache_get("status_seen") or (None, None))[0] or [])
    first_run = not seen
    now = datetime.now(timezone.utc)
    updates, fetched_ids = [], []
    for src in C.STATUS_SOURCES:
        try:
            posts = await fetch_bluesky(session, src["handle"])
        except FetchError as e:
            ev(log, "status_source_down", logging.WARNING, source=src["name"], error=str(e)[:150])
            continue
        fetched_ids += [p["id"] for p in posts]
        new = pick_updates(posts, seen, now)
        ev(log, "status_check", source=src["name"], posts=len(posts), relevant=len(new), first_run=first_run)
        for u in new:
            u["source"] = src["name"]
        updates += new
    if fetched_ids:
        store.cache_put("status_seen", list((seen | set(fetched_ids)))[-500:])
    if first_run:
        # don't replay old news on the very first check; only things from the last couple of hours
        updates = [u for u in updates if _age_h(u["created"], now) <= 2]
    return updates
