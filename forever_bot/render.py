"""
Builds every message the bot sends. Pure functions (no Discord, no network) so the exact output
can be previewed and tested offline. Embeds are plain dicts in Discord's JSON shape.

Discord limits enforced here: embed description 4096, title 256, 6000 chars across all embeds
per message, 2000 chars message content. Links inside embeds don't unfurl, so clips/videos go in
a follow-up message where Discord renders playable previews.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import content as C

DESC_SOFT_CAP = 1900     # keep the main post ~2 phone screens
EMBED_TOTAL_CAP = 5800   # Discord hard cap is 6000
CONTENT_CAP = 1900       # Discord hard cap is 2000
MAX_NEWS = 3
MAX_CLIPS = 2
MAX_VIDEOS = 1

_MD = str.maketrans({c: "\\" + c for c in "\\*_~`|>[]()#"})


def esc(text: str) -> str:
    """Escape Discord markdown in third-party titles so they render exactly as written."""
    return (text or "").translate(_MD).replace("@", "@​")


def ts(dt: datetime) -> int:
    return int(dt.timestamp())


def _d(iso: str) -> date:
    return date.fromisoformat(iso)


def _fmt_date(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"


def _rel_days(n: int) -> str:
    return "today" if n == 0 else "tomorrow" if n == 1 else f"in {n} days"


def _ago(iso: str | None, now: datetime) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    h = (now - dt).total_seconds() / 3600
    if h < 1:
        return "just now"
    if h < 24:
        return f"{int(h)}h ago"
    return f"{int(h // 24)}d ago"


def bar(pct: float, width: int = 10) -> str:
    filled = max(0, min(width, int(pct * width / 100 + 0.5)))
    return "█" * filled + "░" * (width - filled)


def pick(seq, d: date, salt: int = 0, avoid: str = ""):
    """Deterministic daily rotation: preview and real post always match.
    `avoid`: text already in the post; skips items that mostly repeat it."""
    if not seq:
        return None
    start = (d.toordinal() * 7 + salt) % len(seq)
    seen = _words(avoid)
    for i in range(len(seq)):
        item = seq[(start + i) % len(seq)]
        w = _words(item)
        if not seen or not w or len(w & seen) / len(w) < 0.4:
            return item
    return seq[start]


def _words(text: str) -> set:
    import re
    return {w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if len(w) > 4}


# ======================================================================= phase logic
def local_today(tz: str, now: datetime) -> date:
    return now.astimezone(ZoneInfo(tz)).date()


def phase(tz: str, now: datetime):
    """('launch', days_left) before/at launch day, ('raids', days_left) after, or ('done', None)."""
    today = local_today(tz, now)
    launch_local = C.LAUNCH.astimezone(ZoneInfo(tz)).date()
    if today <= launch_local:
        return "launch", (launch_local - today).days
    raids = _d(C.RAIDS_DATE)
    if today <= raids:
        return "raids", (raids - today).days
    return "done", None


def next_key_date(today: date, skip_launch: bool):
    for iso, text in C.KEY_DATES:
        d = _d(iso)
        if d > today and not (skip_launch and text == "Launch"):
            return d, text
    return None


# ======================================================================= tables
def winrate_table() -> str:
    rows = []
    for cls, won, played, series in C.TOURNEY["winrates"]:
        pct = won / played * 100
        rows.append(f"{cls:<8}{bar(pct)} {round(pct):>3}%  {series:>5}")
    return "```\n" + "\n".join(rows) + "\n```"


def top8_table() -> str:
    rows = [f"{p:<4}{name:<12}{cls}" for p, name, cls in C.TOURNEY["top8"]]
    return "```\n" + "\n".join(rows) + "\n```"


# ======================================================================= the daily post
@dataclass
class Post:
    content: str
    embeds: list = field(default_factory=list)
    followup: str | None = None
    used_ids: list = field(default_factory=list)
    rollcall: bool = False
    key: str = ""
    deep_key: str | None = None


def _media(snap, unseen_ids, now, include_news):
    """News embed + clip/video follow-up, shared by the full post and check-ins."""
    embeds, used, follow = [], [], []
    if include_news:
        fresh = [n for n in snap.get("news", []) if unseen_ids is None or n["id"] in unseen_ids][:MAX_NEWS]
        if fresh:
            body = []
            for n in fresh:
                meta = " · ".join(x for x in (n.get("source"), _ago(n.get("published"), now)) if x)
                body.append(f"[{esc(n['title'])}]({n['url']})\n-# {meta}")
            embeds.append({"title": "📰 New since last post", "description": "\n".join(body)[:4000],
                           "color": C.NEWS_COLOR})
            used += [n["id"] for n in fresh]
    clips = [c for c in snap.get("clips", []) if unseen_ids is None or c["id"] in unseen_ids][:MAX_CLIPS]
    if clips:
        follow.append("🎬 **Top clips, last 24h**")
        for c in clips:
            follow.append(f"{esc(c['title'])} · {esc(c['author'])} · {c['views']:,} views\n{c['url']}")
        used += [c["id"] for c in clips]
    vids = [v for v in snap.get("videos", []) if unseen_ids is None or v["id"] in unseen_ids][:MAX_VIDEOS]
    for v in vids:
        views = f" · {v['views']:,} views" if v.get("views") else ""
        follow.append(f"📺 **{esc(v['title'])}** · {esc(v['author'])}{views}")
        if v.get("description"):
            follow.append("> " + esc(v["description"]).replace("\n", " "))
        follow.append(v["url"])
        used.append(v["id"])
    return embeds, used, ("\n".join(follow)[:CONTENT_CAP] if follow else None)


CHECKIN_TOPICS = ["leveling", "pvp", "camping", "professions", "travel"]


def build_checkin(cfg, now: datetime, snap: dict | None, slot: int,
                  unseen_ids: set | None = None, include_news: bool = True) -> Post | None:
    """Later posts in the day: countdown, a fresh tip and fact, and only what's new. No repeats of the rundown."""
    kind, days = phase(cfg.tz, now)
    if kind == "done":
        return None
    today = local_today(cfg.tz, now)
    faction = (cfg.faction or "neutral").lower()
    if kind == "launch":
        title = ("WoW: Forever is live" if days == 0 and now >= C.LAUNCH else
                 f"{days} day{'s' if days != 1 else ''} until WoW: Forever" if days else "Launch day check-in")
        head = f"<t:{ts(C.LAUNCH)}:R>"
    else:
        title = f"{days} day{'s' if days != 1 else ''} until raids open" if days else "Raids are open"
        head = f"Barrow Deeps and Hyjal Summit · {_fmt_date(_d(C.RAIDS_DATE))}"
    topic = pick(CHECKIN_TOPICS, today, salt=slot * 5)
    tip = pick(C.TIPS[topic], today, salt=slot * 11 + 2)
    dyk_pool = [t for tag, t in C.DID_YOU_KNOW if tag != "horde" or faction == "horde"]
    dyk = pick(dyk_pool, today, salt=3 + slot * 13, avoid=tip)
    desc = "\n".join([head, "", f"💡 **{topic.capitalize()} tip:** {tip}", "", f"❓ **Did you know?** {dyk}",
                      "", f"-# More: /tips {topic} · /help"])
    embeds, used, followup = _media(snap or {}, unseen_ids, now, include_news)
    return Post(content="", embeds=[{"title": title, "description": desc, "color": C.BRAND_COLOR}] + embeds,
                followup=followup, used_ids=used, rollcall=False,
                key=f"{kind}:{today.isoformat()}:{slot}", deep_key=topic if topic in C.DEEP_DIVES else None)


def build_daily(cfg, now: datetime, snap: dict | None, counts: dict | None,
                unseen_ids: set | None = None, include_news: bool = True, slot: int = 0) -> Post | None:
    """cfg needs .tz .faction .ping_role_id. unseen_ids=None means 'treat everything as new'.
    slot 0 = the full daily post; slot 1+ = a short check-in."""
    if slot > 0:
        return build_checkin(cfg, now, snap, slot, unseen_ids, include_news)
    kind, days = phase(cfg.tz, now)
    if kind == "done":
        return None
    today = local_today(cfg.tz, now)
    snap = snap or {}
    faction = (cfg.faction or "neutral").lower()
    lines = []

    # ---- header
    if kind == "launch":
        title = ("Launch day: WoW: Forever opens today" if days == 0
                 else f"{days} day{'s' if days != 1 else ''} until WoW: Forever")
        lines.append(f"<t:{ts(C.LAUNCH)}:F> · <t:{ts(C.LAUNCH)}:R>")
    else:
        title = ("Raids open today" if days == 0 else
                 f"{days} day{'s' if days != 1 else ''} until raids open")
        lines.append(f"Barrow Deeps (10) and Hyjal Summit (20) · {_fmt_date(_d(C.RAIDS_DATE))}")
    nxt = next_key_date(today, skip_launch=(kind == "launch"))
    if nxt and not (kind == "raids" and nxt[0] == _d(C.RAIDS_DATE)):
        nd, ntext = nxt
        if not (kind == "launch" and nd > C.LAUNCH.astimezone(ZoneInfo(cfg.tz)).date()):
            lines.append(f"-# Next up: {ntext}, {_fmt_date(nd)} ({_rel_days((nd - today).days)})")

    callout = C.TODAY_CALLOUTS.get(today.isoformat())
    if callout:
        lines.append("")
        lines.append(callout)

    # ---- rundown
    rd = C.RUNDOWNS.get(days) if kind == "launch" else None
    if kind == "launch" and rd is None:  # more than 11 days out: rotate the explainers
        rd = C.RUNDOWNS[11]
    if rd:
        lines += ["", f"**{'Today' if days == 0 else f'Day {days}'} · {rd['title']}**",
                  f"🌱 {rd['new']}", f"🧙 {rd['vets']}"]
        pro = C.PRO_TIPS.get(days if days in C.RUNDOWNS else 11)
        if pro:
            lines.append(f"⚔️ **Pro tip:** {pro}")
        if rd.get("special") == "tourney":
            lines += ["", "**Finals: duels won vs other classes**", winrate_table(),
                      f"-# % = duels won · then series W–L · mirror matches excluded · {C.TOURNEY['caveat']}",
                      "", f"**Why locks won:** {C.TOURNEY['why']}"]

    # ---- post-launch: rotate topic, pro tip from that topic's bank
    deep_key = str(days if days in C.DEEP_DIVES else 11) if kind == "launch" else None
    if kind == "raids":
        topic = pick(C.POST_LAUNCH_TOPICS, today)
        deep_key = topic
        lines += ["", f"**Today · {C.DEEP_DIVES[topic][0]}**",
                  f"⚔️ **Pro tip:** {pick(C.TIPS.get(topic, C.NEWBIE_TIPS), today, salt=1)}"]

    # ---- tip + did you know
    if days not in (0,) or kind == "raids":
        tip = pick(C.NEWBIE_TIPS, today, avoid="\n".join(lines))
        if tip:
            lines += ["", f"💡 **New player tip:** {tip}"]
    dyk_pool = [t for tag, t in C.DID_YOU_KNOW if tag != "horde" or faction == "horde"]
    dyk = pick(dyk_pool, today, salt=3, avoid="\n".join(lines))
    if dyk:
        lines += ["", f"❓ **Did you know?** {dyk}"]

    # ---- roll call line
    if counts is not None:
        total = sum(counts.values())
        who = {"horde": "Horde main", "alliance": "Alliance main"}.get(faction, "main")
        lines += ["", f"**Roll call:** what's your {who}? {total} in so far. Tap a class below."]

    lines += ["", "-# 🔎 Deep dive button below · /help for all commands"]
    desc = "\n".join(lines)
    if len(desc) > DESC_SOFT_CAP:  # drop optional blocks before ever truncating mid-sentence
        desc = "\n".join(l for l in lines if not l.startswith("💡"))
    desc = desc[:4000]
    main = {"title": title[:256], "description": desc, "color": C.BRAND_COLOR}
    embeds = [main]
    used = []

    # ---- news embed (headlines + links only) and clips/videos follow-up
    media_embeds, media_used, followup = _media(snap, unseen_ids, now, include_news)
    embeds += media_embeds
    used += media_used

    # enforce total embed budget
    while sum(len(e.get("title", "")) + len(e.get("description", "")) for e in embeds) > EMBED_TOTAL_CAP and len(embeds) > 1:
        embeds.pop()

    ping = f"<@&{cfg.ping_role_id}>" if cfg.ping_role_id else ""
    return Post(content=ping, embeds=embeds, followup=followup, used_ids=used,
                rollcall=counts is not None, key=f"{kind}:{today.isoformat()}:0", deep_key=deep_key)


def deep_dive_embed(key: str) -> dict | None:
    k = int(key) if str(key).lstrip("-").isdigit() else key
    dd = C.DEEP_DIVES.get(k)
    if not dd:
        return None
    title, bullets = dd
    return {"title": f"🔎 {title}", "description": "\n".join(f"• {b}" for b in bullets)[:4000],
            "color": C.BRAND_COLOR}


TIP_TOPICS = list(C.TIPS)


def tips_embed(topic: str) -> dict:
    topic = topic if topic in C.TIPS else "basics"
    tips = C.TIPS[topic]
    desc = "\n".join(f"• {t}" for t in tips)
    if topic in C.DEEP_DIVES:
        desc += "\n\n" + "\n".join(f"• {b}" for b in C.DEEP_DIVES[topic][1])
    return {"title": f"💡 Tips: {topic}", "description": desc[:4000], "color": C.GREEN,
            "footer": {"text": "Topics: " + " · ".join(TIP_TOPICS)}}


# ======================================================================= launch-night pings
MILESTONES = [  # (minutes before launch, message)
    (60, "⏳ **One hour.** Launcher open, patch done, snacks ready. PvP ruleset → Horde."),
    (10, "🔔 **Ten minutes.** Log in to the launcher and get ready to mash that Play button."),
    (0, "🚀 **WoW: Forever is live.** See you in Azeroth. For the Horde."),
]


def milestone_text(minutes: int, faction: str) -> str:
    for m, text in MILESTONES:
        if m == minutes:
            if faction != "horde":
                text = text.replace(" PvP ruleset → Horde.", "").replace(" For the Horde.", "")
            return text
    return ""


# ======================================================================= commands
def tourney_embed() -> dict:
    T = C.TOURNEY
    desc = "\n".join([
        T["summary"], "",
        "**Top 8**", top8_table(),
        "**Finals: duels won vs other classes**", winrate_table(),
        "-# % = duels won · then series W–L · mirror matches excluded", "",
        f"**Why locks won:** {T['why']}", "",
        f"**Best run:** {T['story']}", "",
        f"**Prizes:** {T['prizes']}", "",
        f"-# {T['caveat']}",
    ])
    return {"title": "🏆 The Forever Open: $100K beta duel tournament", "description": desc[:4000],
            "color": C.BRAND_COLOR}


def faq_embed() -> dict:
    desc = "\n\n".join(f"**{q}**\n{a}" for q, a in C.FAQ)
    return {"title": "❓ WoW: Forever FAQ", "description": desc[:4000], "color": C.GREEN}


def dates_embed(tz: str, now: datetime) -> dict:
    today = local_today(tz, now)
    lines = []
    for iso, text in C.KEY_DATES:
        d = _d(iso)
        if text == "Launch":
            lines.append(f"**Launch:** <t:{ts(C.LAUNCH)}:F> (<t:{ts(C.LAUNCH)}:R>)")
        else:
            mark = "~~" if d < today else ""
            lines.append(f"{mark}**{_fmt_date(d)}:** {text}{mark}")
    lines += [f"**{when}:** {what}" for when, what in C.LATER]
    return {"title": "📅 Key dates", "description": "\n".join(lines), "color": C.BRAND_COLOR}


def countdown_embed(tz: str, now: datetime) -> dict:
    kind, days = phase(tz, now)
    if kind == "launch":
        t = "Launch day!" if days == 0 else f"{days} day{'s' if days != 1 else ''} until WoW: Forever"
        d = f"<t:{ts(C.LAUNCH)}:F> · <t:{ts(C.LAUNCH)}:R>"
    elif kind == "raids":
        t = f"WoW: Forever is live · raids in {days} day{'s' if days != 1 else ''}"
        d = f"Barrow Deeps and Hyjal Summit open {_fmt_date(_d(C.RAIDS_DATE))}"
    else:
        t, d = "WoW: Forever is live", "Raids are open. Go get that legendary."
    return {"title": t, "description": d, "color": C.BRAND_COLOR}


# ======================================================================= /help spellbook
# (command, args, cast line, what it does). "cast line" is the tooltip flavor under the name.
SPELLBOOK = {
    "quest": {
        "label": "Quest log", "emoji": "📜", "admin": False,
        "blurb": "New to Azeroth? These three get you ready for Nov 4.",
        "flavor": "A grizzled orc slams a scroll on the table. \"Read it. Then we ride.\"",
        "spells": [
            ("faq", "", "Step 1 · Instant", "What Forever is, what to buy (nothing), and which ruleset to pick."),
            ("tips", "topic:basics", "Step 2 · Instant · Private", "The essentials every new player should know."),
            ("pickaclass", "", "Step 3 · Instant", "Tell the server what you're rolling. Change it anytime."),
        ],
    },
    "countdown": {
        "label": "Countdown and dates", "emoji": "⏳", "admin": False,
        "blurb": "How long until the gates open.",
        "flavor": "The hourglass on the Orgrimmar wall is nearly empty.",
        "spells": [
            ("countdown", "", "Instant · No cooldown", "Time until launch, shown in your own time zone. After launch, time until raids."),
            ("dates", "", "Instant", "Every key date: name reservation, launch, raids, Hardcore."),
        ],
    },
    "learn": {
        "label": "Tips and lore", "emoji": "💡", "admin": False,
        "blurb": "Go from fresh level 1 to knowing what you're doing.",
        "flavor": "Knowledge is the only thing you keep when you die on a PvP server.",
        "spells": [
            ("tips", "[topic]", "Instant · Private", "Tips by topic: basics, leveling, pvp, camping, professions, travel."),
            ("faq", "", "Instant", "Quick answers to the questions everyone asks."),
            ("tourney", "", "Instant", "The $100K Forever Open: top 8, class win rates, and why Warlocks won."),
        ],
        "extra": "🔎 **Deep dive** buttons on daily posts open a private, detailed breakdown of that day's topic.",
    },
    "rollcall": {
        "label": "Roll call", "emoji": "⚔️", "admin": False,
        "blurb": "See who's rolling what before launch night.",
        "flavor": "Every warband needs a healer. Somebody please play a healer.",
        "spells": [
            ("pickaclass", "", "Instant · Private", "Pick your class. The counts on the daily post update live."),
        ],
        "extra": "You can also tap a class button right on the daily post.",
    },
    "officer": {
        "label": "Officer commands", "emoji": "🛡️", "admin": True,
        "blurb": "For people with Manage Server. Everything replies privately.",
        "flavor": "With great guild bank access comes great responsibility.",
        "spells": [
            ("setup", "channel [ping_role] [staging] [post_time] [timezone] [faction]", "Channel · One time",
             "Where and when the countdown posts."),
            ("frequency", "[per_day] [times]", "Instant", "Post 1–4 times a day. The first post is full; the rest are check-ins."),
            ("preview", "", "Instant · Private", "See today's post plus data source health."),
            ("postnow", "", "Instant", "Post today's full post now, or the current check-in."),
            ("hold", "", "Instant · Lasts today", "Skip all of today's posts. /resume undoes it."),
            ("resume", "", "Instant", "Undo /hold."),
            ("skipnews", "", "Instant · Lasts today", "Post today without the news section."),
            ("status", "", "Instant · Private", "Current settings and which sources are working."),
        ],
    },
}


def spellbook_pages(is_admin: bool) -> list[str]:
    return [k for k, v in SPELLBOOK.items() if is_admin or not v["admin"]]


def _cmd(name: str, ids: dict) -> str:
    cid = (ids or {}).get(name)
    return f"</{name}:{cid}>" if cid else f"`/{name}`"


def spellbook_embed(page: str, ids: dict | None, is_admin: bool, now: datetime | None = None) -> dict:
    pages = spellbook_pages(is_admin)
    page = page if page in pages else pages[0]
    sec = SPELLBOOK[page]
    lines = [f"*{sec['flavor']}*", "", sec["blurb"], ""]
    for name, args, cast, what in sec["spells"]:
        arg = f" `{args}`" if args else ""
        lines.append(f"**{_cmd(name, ids)}**{arg}\n-# {cast}\n{what}")
        lines.append("")
    if sec.get("extra"):
        lines.append(sec["extra"])
    if now is not None and page in ("quest", "countdown"):
        kind, days = phase(C.DEFAULT_TZ, now)
        if kind == "launch":
            lines += [f"⏳ Launch <t:{ts(C.LAUNCH)}:R>"]
    footer = f"Spellbook · page {pages.index(page) + 1} of {len(pages)} · Tap a blue command to cast it"
    return {"title": f"{sec['emoji']} {sec['label']}", "description": "\n".join(lines).strip()[:4000],
            "color": 0xC69B6D, "footer": {"text": footer}}


def health_text(snap: dict | None) -> str:
    if not snap:
        return "⚠️ No data fetched yet."
    h = snap.get("health", {})
    ok = sum(1 for v in h.values() if v == "ok")
    bad = [f"`{k}` {v}" for k, v in h.items() if v != "ok"]
    when = datetime.fromtimestamp(snap.get("fetched_at", 0), tz=timezone.utc)
    head = f"{'✅' if not bad else '⚠️'} {ok}/{len(h)} sources OK · fetched <t:{ts(when)}:R>"
    return head + ("\n" + "\n".join(bad) if bad else "")
