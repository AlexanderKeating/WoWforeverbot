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

from . import classes as K
from . import content as C
from . import guides as G

DESC_SOFT_CAP = 2800     # main post: fuller vets lines (1.1.2); hard limit is 4096
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
        w = _words(item if isinstance(item, str) else " ".join(map(str, item)))
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
    vids = [v for v in snap.get("videos", []) if unseen_ids is None or v["id"] in unseen_ids][:MAX_VIDEOS] if C.SHOW_YOUTUBE else []
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
    cls, ctip = pick(K.SPOTLIGHT, today, salt=slot * 17 + 5)
    desc = "\n".join([head, "", f"💡 **{topic.capitalize()} tip:** {tip}", "",
                      f"🎯 **Class spotlight · {cls}:** {ctip}", "", f"❓ **Did you know?** {dyk}",
                      "", f"-# More: /tips {topic} · /classtips {cls.lower()} · /help"])
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

    ping = f"<@&{cfg.ping_role_id}>" if (C.NOTIFY and cfg.ping_role_id) else ""
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
        "blurb": "New to Azeroth? Six quick steps to be ready for Nov 4.",
        "flavor": "A grizzled orc slams a scroll on the table. \"Read it. Then we ride.\"",
        "spells": [
            ("faq", "", "Step 1 · Instant", "What Forever is, what to buy (nothing), and which ruleset to pick."),
            ("tips", "topic:basics", "Step 2 · Instant · Private", "The essentials every new player should know."),
            ("whichclass", "", "Step 3 · Instant · Private", "Not sure what to play? A 5-question quiz."),
            ("classtips", "class", "Step 4 · Instant · Private", "What's different about your class in Forever."),
            ("keybinds", "[class] [topic]", "Step 5 · Instant · Private", "Stop clicking: what to bind and where."),
            ("pickaclass", "", "Step 6 · Instant", "Tell the server what you're rolling. Change it anytime."),
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
            ("classtips", "class", "Instant · Private", "Forever changes, leveling and PvP tips, and key talents for any class."),
            ("keybinds", "[class] [topic]", "Instant · Private", "Keybind basics, what each class should bind first, and controller setup."),
            ("macros", "class", "Instant · Private", "Copy-paste macros like mouseover heals and interrupts."),
            ("rotation", "class", "Instant · Private", "Simple leveling priorities for every spec."),
            ("whichclass", "", "Instant · Private", "A quick quiz that suggests a class for you."),
        ],
        "extra": "🔎 **Deep dive** buttons on daily posts open a private, detailed breakdown of that day's topic.",
    },
    "rollcall": {
        "label": "Roll call", "emoji": "⚔️", "admin": False,
        "blurb": "See who's rolling what before launch night.",
        "flavor": "Every warband needs a healer. Somebody please play a healer.",
        "spells": [
            ("pickaclass", "", "Instant · Private", "Pick your class. You get its Forever tips right away."),
            ("classtips", "class", "Instant · Private", "Tips for any class, even ones you're not playing."),
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
            ("pinpost", "[channel]", "Instant", "Post a \"start here\" card to pin. It updates itself after every post."),
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


# ======================================================================= /classtips
def tourney_line(cls: str) -> str | None:
    for c, won, played, series in C.TOURNEY["winrates"]:
        if c == cls:
            return f"{won}–{played - won} in duels vs other classes ({round(won / played * 100)}%) · series {series}"
    return None


def classtips_embed(cls: str, faction: str = "horde") -> dict | None:
    d = K.CLASSES.get(cls)
    if not d:
        return None
    bullets = lambda xs: "\n".join(f"• {x}" for x in xs)[:1024]
    fields = [
        {"name": "🧙 What's new in Forever", "value": bullets(d["new"]), "inline": False},
        {"name": "🌱 Leveling", "value": bullets(d["leveling"]), "inline": False},
        {"name": "⚔️ PvP" + (" (Horde)" if faction == "horde" else ""), "value": bullets(d["pvp"]), "inline": False},
        {"name": "⭐ Talents worth knowing", "value": bullets(d["talents"]), "inline": False},
    ]
    tl = tourney_line(cls)
    footer = (f"Beta tournament finals (level 30): {tl} · " if tl else "") + "Beta info; Blizzard may still tune things. Buttons: keybinds, macros, rotation"
    race_label = "Horde races" if faction == "horde" else "Races"
    return {"title": f"{cls} in WoW: Forever", "color": K.COLORS.get(cls, C.BRAND_COLOR),
            "description": f"{d['role']}\n-# {race_label}: {d['races']}", "fields": fields,
            "footer": {"text": footer[:2048]}}


# ======================================================================= keybinds / macros / rotations
def _b(xs):
    return "\n".join(f"• {x}" for x in xs)[:1024]


def keybinds_embed(cls: str | None = None, topic: str = "basics") -> dict:
    if topic == "controller":
        return {"title": "🎮 Playing WoW: Forever on a controller", "color": C.GREEN,
                "description": "\n".join(f"• {x}" for x in G.CONTROLLER)[:4000],
                "footer": {"text": "Gamepad UI is labeled Alpha; details may change."}}
    if cls and cls in G.CLASS_GUIDES:
        g = G.CLASS_GUIDES[cls]
        first = "\n".join(f"• **{a}**: {why}" for a, why in g["bind_first"])[:1024]
        grid = "```\n" + "\n".join(f"{k:<12}{a}" for k, a in g["layout"]) + "\n```"
        return {"title": f"⌨️ {cls} keybinds", "color": K.COLORS.get(cls, C.BRAND_COLOR),
                "description": "Start here, then adjust to your hands. The point is: **never click these in a fight.**",
                "fields": [{"name": "Bind these first", "value": first, "inline": False},
                           {"name": "A starter layout to copy", "value": grid[:1024], "inline": False}],
                "footer": {"text": "Some abilities unlock later or come from talents. /keybinds for general tips · /macros for mouseover macros"}}
    B = G.KEYBIND_BASICS
    return {"title": "⌨️ Keybinds 101", "color": C.GREEN,
            "description": G.KEYBIND_BASICS["howto"],
            "fields": [{"name": "🌱 The basics", "value": _b(B["new"]), "inline": False},
                       {"name": "🗺️ Where to put things", "value": _b(B["layout"]), "inline": False},
                       {"name": "🎯 Targeting", "value": _b(B["targeting"]), "inline": False}],
            "footer": {"text": "/keybinds class:<yours> for what to bind first · /keybinds topic:controller for gamepad"}}


def macros_embed(cls: str) -> dict | None:
    ms = G.MACROS.get(cls)
    if not ms:
        return None
    fields = []
    for title, text, what, verified in ms:
        tag = "" if verified else " · ⚠️ test in-game"
        fields.append({"name": f"{title}{tag}", "value": f"```\n{text}\n```{what}"[:1024], "inline": False})
    return {"title": f"🧩 {cls} macros", "color": K.COLORS.get(cls, C.BRAND_COLOR), "description": G.MACRO_HOWTO,
            "fields": fields,
            "footer": {"text": "⚠️ = standard Classic macro syntax not yet confirmed for Forever. Others use syntax confirmed working in Forever."}}


def rotation_embed(cls: str) -> dict | None:
    rs = G.ROTATIONS.get(cls)
    if not rs:
        return None
    fields = [{"name": spec, "value": "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))[:1024], "inline": False}
              for spec, steps in rs]
    return {"title": f"🔁 {cls}: what to press", "color": K.COLORS.get(cls, C.BRAND_COLOR),
            "description": "Simple leveling priorities. Not min-maxed; just a solid place to start.",
            "fields": fields,
            "footer": {"text": "Numbers in parentheses = talent points needed. Beta info; Blizzard may still tune things."}}


def quiz_embed(qi: int) -> dict:
    q, opts = G.QUIZ[qi]
    return {"title": f"🧭 Which class fits you? · {qi + 1}/{len(G.QUIZ)}", "description": f"**{q}**",
            "color": C.BRAND_COLOR, "footer": {"text": "Just for fun. Every class is viable in Forever."}}


def quiz_result_embed(answers: list[int], faction: str = "horde") -> dict:
    ranked = G.score_quiz(answers)
    top, runner = ranked[0][0], ranked[1][0] if len(ranked) > 1 else None
    d = K.CLASSES[top]
    lines = [f"**Your match: {top}**", d["role"], f"-# Horde races: {d['races']}" if faction == "horde" else ""]
    if runner:
        lines += ["", f"**Also worth a look: {runner}**", K.CLASSES[runner]["role"]]
    lines += ["", "Use the buttons for tips, or run `/pickaclass` to join the roll call."]
    return {"title": "🧭 Your Forever class", "description": "\n".join(l for l in lines if l is not None),
            "color": K.COLORS.get(top, C.BRAND_COLOR)}


# ======================================================================= pinned "start here" card
def _schedule_text(times: list[tuple[int, int]], tz: str) -> str:
    def fmt(h, m):
        ap = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {ap}" if m else f"{h12} {ap}"
    zone = {"America/Chicago": "Central", "America/New_York": "Eastern", "America/Denver": "Mountain",
            "America/Los_Angeles": "Pacific", "America/Phoenix": "Arizona"}.get(tz, tz.split("/")[-1].replace("_", " "))
    first = fmt(*times[0])
    rest = ", ".join(fmt(*t) for t in times[1:])
    return f"Full post daily at **{first}**" + (f", check-ins at **{rest}**" if rest else "") + f" ({zone} time)"


def pinned_embed(cfg, times, now: datetime, latest_url: str | None = None, ping_role_id: int | None = None) -> dict:
    kind, days = phase(cfg.tz, now)
    if kind == "launch":
        head = f"**Launch:** <t:{ts(C.LAUNCH)}:F> · <t:{ts(C.LAUNCH)}:R>"
    elif kind == "raids":
        head = f"**WoW: Forever is live.** Raids open {_fmt_date(_d(C.RAIDS_DATE))}."
    else:
        head = "**WoW: Forever is live and raids are open.**"
    today = local_today(cfg.tz, now)
    dates = []
    for iso, text in C.KEY_DATES:
        d = _d(iso)
        if text == "Launch":
            dates.append(f"{'~~' if C.LAUNCH < now else ''}<t:{ts(C.LAUNCH)}:D> · Launch{'~~' if C.LAUNCH < now else ''}")
        else:
            strike = "~~" if d < today else ""
            dates.append(f"{strike}{_fmt_date(d)} · {text}{strike}")
    lines = [
        head, "",
        "**📅 What happens here**",
        _schedule_text(times, cfg.tz) + ".",
        "Each full post has the day's topic for new players 🌱 and veterans 🧙, a pro tip, a 🔎 deep dive, "
        "news, top clips, and a class roll call.", "",
        "**🧭 New here? Start with**",
        "`/faq` → `/whichclass` → `/classtips` → `/keybinds` → `/pickaclass`", "",
        "**🗓️ Key dates**", *dates, "",
        "**📖 Everything else:** `/help` opens the full command spellbook.",
    ]
    if ping_role_id:
        lines += ["", f"**🔔 Pings:** the daily post pings <@&{ping_role_id}>. Use the button below to opt in or out."]
    if latest_url:
        lines += ["", f"**Latest post:** [jump to it]({latest_url})"]
    title = (f"⏳ WoW: Forever · {days} day{'s' if days != 1 else ''} to go" if kind == "launch" and days
             else "⏳ WoW: Forever · start here")
    return {"title": title, "description": "\n".join(lines)[:4000], "color": C.BRAND_COLOR,
            "footer": {"text": "Pin this message · it updates itself after every post"}}


def health_text(snap: dict | None) -> str:
    if not snap:
        return "⚠️ No data fetched yet."
    h = {k: v for k, v in snap.get("health", {}).items() if v != "off"}
    ok = sum(1 for v in h.values() if v == "ok")
    bad = [f"`{k}` {v}" for k, v in h.items() if v != "ok"]
    when = datetime.fromtimestamp(snap.get("fetched_at", 0), tz=timezone.utc)
    head = f"{'✅' if not bad else '⚠️'} {ok}/{len(h)} sources OK · fetched <t:{ts(when)}:R>"
    return head + ("\n" + "\n".join(bad) if bad else "")
