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
LEVELS = ("brief", "standard", "detailed")
LEVEL_LABEL = {"brief": "Brief", "standard": "Standard", "detailed": "Detailed", "plain": "Plain words"}


def norm_level(level: str | None) -> str:
    return level if level in LEVELS else "standard"


def level_footer(level: str, extra: str = "") -> dict:
    t = f"Detail: {LEVEL_LABEL[norm_level(level)]} · change with /mysettings"
    return {"text": (extra + " · " + t) if extra else t}


# ------------------------------------------------------------------ 1.4.2 faction-neutral by default
# Content was written for a Horde PvP server. Unless a server picks Horde in /setup, these swaps make
# the advice faction-neutral. Labeled Horde-only facts (racials, Horde vendors) are left as they are.
_FACTION_SWAPS = [
    ("which is one more reason to lock in your Horde name early", "which is one more reason to lock in your name early"),
    ("We're on **PvP, Horde**.", "Pick the one your group agreed on."),
    ("pick **PvP ruleset → Horde**", "pick the **ruleset and faction** your group agreed on"),
    ("PvP ruleset → Horde → your reserved name", "your ruleset → your faction → your reserved name"),
    ("PvP ruleset → Horde. Creating", "Pick your ruleset and faction. Creating"),
    ("Agree on PvP + Horde with your friends", "Agree on a ruleset and faction with your friends"),
    ("One Alliance test character on the PvP ruleset locks your whole account out of Horde there.",
     "One test character on the wrong faction on the PvP ruleset locks your whole account to that faction there."),
    ("**Make your PvP Horde character first.**", "**Make your main PvP character first.**"),
    ("make your Horde character first", "make your main character first"),
    ("**Order matters on PvP:** make your Horde character first", "**Order matters on PvP:** make your main character first"),
    ("agree on PvP Horde", "agree on a ruleset and faction"),
    ("**Character creation:** PvP ruleset, then Horde, then your character.",
     "**Character creation:** your ruleset, then your faction, then your character."),
    ("**Create:** PvP ruleset → Horde → your reserved name.", "**Create:** your ruleset → your faction → your reserved name."),
    ("On the PvP ruleset, Alliance can attack you", "On the PvP ruleset, the other faction can attack you"),
    ("watch for Alliance in contested zones", "watch for the other faction in contested zones"),
    ("Alliance can attack you anywhere outside cities", "the other faction can attack you anywhere outside cities"),
    ("a big quest hub like the Crossroads,", "a big quest hub like the Crossroads or Lakeshire,"),
    ("Undead vs a Warlock:", "Undead (Horde) vs a Warlock:"),
    ("Darkspear Raiders base at Merchant Coast", "Darkspear Raiders base at Merchant Coast (Horde)"),
    ("Pick the **PvP** ruleset and **Horde**.", "Pick a ruleset (Normal, PvP or Roleplay) and a faction with your group."),
]


def fit_faction(text, faction):
    if not text or (faction or "").lower() == "horde":
        return text
    for a, b in _FACTION_SWAPS:
        text = text.replace(a, b)
    return text


def fit_faction_embed(e, faction):
    if not e or (faction or "").lower() == "horde":
        return e
    e = dict(e)
    for k in ("title", "description"):
        if e.get(k):
            e[k] = fit_faction(e[k], faction)
    if e.get("fields"):
        e["fields"] = [{**f, "name": fit_faction(f["name"], faction), "value": fit_faction(f["value"], faction)}
                       for f in e["fields"]]
    if e.get("footer"):
        e["footer"] = {**e["footer"], "text": fit_faction(e["footer"].get("text", ""), faction)}
    return e


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
    n = len(seq)
    # step 7 per day keeps the original rotation, but 7 must not share a factor with n or it gets stuck
    start = ((d.toordinal() * 7 if n % 7 else d.toordinal()) + salt) % n
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
        strict = [c for c in clips if not c.get("loose")]
        loose = [c for c in clips if c.get("loose")]
        if strict:
            follow.append("🎬 **Top Forever clips, last 24h**")
            for c in strict:
                follow.append(f"{esc(c['title'])} · {esc(c['author'])} · {c['views']:,} views\n{c['url']}")
        if loose:
            follow.append("🎬 **WoW clips from streamers we follow**\n-# Not necessarily Forever. Forever clips take over once Twitch adds its category.")
            for c in loose:
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
    level = norm_level(getattr(cfg, "verbosity", None))
    parts = [head, "", f"💡 **{topic.capitalize()} tip:** {tip}", "", f"🎯 **Class spotlight · {cls}:** {ctip}"]
    if level != "brief":
        parts += ["", f"❓ **Did you know?** {dyk}"]
    if level == "detailed" and topic in C.DEEP_DIVES:
        parts += ["", f"🔎 **{C.DEEP_DIVES[topic][0]}:** {pick(C.DEEP_DIVES[topic][1], today, salt=slot)}"]
    parts += ["", f"-# 📖 More detail below, at your level · /classtips {cls.lower()} · /help"]
    desc = "\n".join(parts)
    embeds, used, followup = _media(snap or {}, unseen_ids, now, include_news)
    return Post(content="", embeds=[{"title": title, "description": desc, "color": C.BRAND_COLOR}] + embeds,
                followup=followup, used_ids=used, rollcall=False,
                key=f"{kind}:{today.isoformat()}:{slot}", deep_key=topic if topic in C.DEEP_DIVES else None)


def _build_daily_raw(cfg, now: datetime, snap: dict | None, counts: dict | None,
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
    level = norm_level(getattr(cfg, "verbosity", None))
    if rd:
        lines += ["", f"**{'Today' if days == 0 else f'Day {days}'} · {rd['title']}**", f"🌱 {rd['new']}"]
        if level != "brief":
            lines.append(f"🧙 {rd['vets']}")
        pro = C.PRO_TIPS.get(days if days in C.RUNDOWNS else 11)
        if pro:
            lines.append(f"⚔️ **Pro tip:** {pro}")
        dd = C.DEEP_DIVES.get(days if days in C.DEEP_DIVES else 11)
        if level == "detailed" and dd:
            lines += ["", f"🔎 **From the deep dive:**"] + [f"• {b}" for b in dd[1][:2]]
        if rd.get("special") == "tourney" and level == "brief":
            lines.append(f"-# Warlocks went 26–7 vs other classes in the finals. Full table: /tourney")
        elif rd.get("special") == "tourney":
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
        # 1.5: a highlight or two from the topic's deep dive, so post-launch days have some substance
        n_dd = {"brief": 0, "standard": 1}.get(level, 2)
        if n_dd:
            dd_items = C.DEEP_DIVES[topic][1]
            first = pick(dd_items, today, salt=5)
            picks = [first] + [x for x in dd_items if x != first][:n_dd - 1]
            lines += ["", "🔎 **From the deep dive:**"] + [f"• {b}" for b in picks]

    # ---- tip + did you know (skipped in Brief)
    if level != "brief" and (days not in (0,) or kind == "raids"):
        tip = pick(C.NEWBIE_TIPS, today, avoid="\n".join(lines))
        if tip:
            lines += ["", f"💡 **New player tip:** {tip}"]
    dyk_pool = [t for tag, t in C.DID_YOU_KNOW if tag != "horde" or faction == "horde"]
    dyk = pick(dyk_pool, today, salt=3, avoid="\n".join(lines))
    if dyk and level != "brief":
        lines += ["", f"❓ **Did you know?** {dyk}"]

    # ---- roll call line
    if counts is not None:
        total = sum(counts.values())
        who = {"horde": "Horde main", "alliance": "Alliance main"}.get(faction, "main")
        lines += ["", f"**Roll call:** what's your {who}? {total} in so far. Tap a class below."]

    lines += ["", "-# 📖 More detail below, at your own level (/mysettings) · /help for all commands"]
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


def deep_dive_embed(key: str, level: str = "standard") -> dict | None:
    """📖 More detail: today's topic at the reader's own level."""
    level = norm_level(level)
    k = int(key) if str(key).lstrip("-").isdigit() else key
    dd = C.DEEP_DIVES.get(k)
    if not dd:
        return None
    title, bullets = dd
    rd = C.RUNDOWNS.get(k) if isinstance(k, int) else None
    pro = C.PRO_TIPS.get(k) if isinstance(k, int) else None
    parts = []
    if rd:
        parts.append(f"🌱 {rd['new']}")
        if level != "brief":
            parts.append(f"🧙 {rd['vets']}")
    if pro and level == "detailed":
        parts.append(f"⚔️ **Pro tip:** {pro}")
    shown = bullets[:3] if level == "brief" else bullets
    parts.append("\n".join(f"• {b}" for b in shown))
    if level == "brief" and len(bullets) > 3:
        parts.append(f"-# {len(bullets) - 3} more in Standard or Detailed")
    if not rd and k in C.TIPS and level == "detailed":
        parts.append("**More tips**\n" + "\n".join(f"• {t}" for t in C.TIPS[k][:4]))
    return {"title": f"📖 {title}", "description": "\n\n".join(parts)[:4000], "color": C.BRAND_COLOR,
            "footer": level_footer(level)}


TIP_TOPICS = list(C.TIPS)


def tips_embed(topic: str, level: str = "standard") -> dict:
    level = norm_level(level)
    topic = topic if topic in C.TIPS else "basics"
    tips = C.TIPS[topic][:3] if level == "brief" else C.TIPS[topic]
    desc = "\n".join(f"• {t}" for t in tips)
    if level == "detailed" and topic in C.DEEP_DIVES:
        desc += "\n\n" + "\n".join(f"• {b}" for b in C.DEEP_DIVES[topic][1])
    return {"title": f"💡 Tips: {topic}", "description": desc[:4000], "color": C.GREEN,
            "footer": level_footer(level, "Topics: " + " · ".join(TIP_TOPICS))}


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
            ("dungeons", "", "Instant · Private", "Forever's nine new dungeons: levels, where they are, and how to get in."),
            ("addons", "[topic]", "Instant · Private", "Starter addons that work in Forever, how to install them, and what to skip."),
            ("whichclass", "", "Instant · Private", "A quick quiz that suggests a class for you."),
            ("mysettings", "[detail]", "Instant · Private", "Choose Brief, Standard or Detailed for everything the bot sends you."),
            ("mydata", "", "Instant · Private", "See everything the bot has stored about you (spoiler: very little)."),
            ("forgetme", "", "Instant · Private", "Delete your settings and roll-call picks everywhere."),
        ],
        "extra": "🔎 **Deep dive** buttons on daily posts open a private, detailed breakdown of that day's topic.\n"
                 f"-# [Terms]({C.TERMS_URL}) · [Privacy]({C.PRIVACY_URL})",
    },
    "plusone": {
        "label": "Plus One mode", "emoji": "💞", "admin": False,
        "blurb": "For anyone whose partner, best friend or roommate said \"you'll love it\". Private and jargon-free.",
        "flavor": "Someone promised to show you everything. We'll fill in the gaps.",
        "spells": [
            ("draggedalong", "", "Instant · Private", "The survival kit, plus panic buttons, a class quiz for two, and a card for your partner."),
            ("whatdoesthatmean", "[term]", "Instant · Private", "Explains WoW words and slang, from aggro to zug zug."),
        ],
        "extra": "Want every private reply in plain words? `/mysettings` → **Plain words**.",
    },
    "rollcall": {
        "label": "Roll call", "emoji": "⚔️", "admin": False,
        "blurb": "See who's rolling what before launch night.",
        "flavor": "Every warband needs a healer. Somebody please play a healer.",
        "spells": [
            ("pickaclass", "", "Instant · Private", "Pick your class. You get its Forever tips right away."),
            ("rollcall", "[share]", "Instant · Private", "See who's playing what in this server. Add share:True to post it in the channel."),
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
            ("verbosity", "[level]", "Instant", "How detailed channel posts are: Brief, Standard or Detailed."),
            ("preview", "", "Instant · Private", "See today's post plus data source health."),
            ("postnow", "", "Instant", "Post today's full post now, or the current check-in."),
            ("hold", "", "Instant · Lasts today", "Skip all of today's posts. /resume undoes it."),
            ("resume", "", "Instant", "Undo /hold."),
            ("skipnews", "", "Instant · Lasts today", "Post today without the news section."),
            ("status", "", "Instant · Private", "Current settings and which sources are working."),
            ("pinpost", "[channel]", "Instant", "Post a \"start here\" card to pin. It updates itself after every post."),
            ("statusalerts", "[on]", "Instant", "Post Blizzard's Forever outage, maintenance and fix updates here (on by default)."),
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


def classtips_embed(cls: str, faction: str = "horde", level: str = "standard") -> dict | None:
    level = norm_level(level)
    if cls not in K.CLASSES:
        return None
    d = K.class_view(cls, faction)  # 1.5: faction-aware races, role and PvP tips
    bullets = lambda xs: "\n".join(f"• {x}" for x in xs)[:1024]
    cut = (lambda xs, n: xs[:n]) if level == "brief" else (lambda xs, n: xs)
    fields = [
        {"name": "🧙 What's new in Forever", "value": bullets(cut(d["new"], 3)), "inline": False},
        {"name": "🌱 Leveling", "value": bullets(cut(d["leveling"], 2)), "inline": False},
        {"name": d["pvp_label"], "value": bullets(cut(d["pvp"], 2)), "inline": False},
    ]
    if level != "brief":
        fields.append({"name": "⭐ Talents worth knowing", "value": bullets(d["talents"]), "inline": False})
    if level == "detailed":
        g = G.CLASS_GUIDES.get(cls)
        if g:
            fields.append({"name": "⌨️ Bind these first", "value": bullets(f"**{a}**: {why}" for a, why in g["bind_first"][:4]),
                           "inline": False})
        rot = G.ROTATIONS.get(cls)
        if rot:
            spec, steps = rot[0]
            fields.append({"name": f"🔁 {spec}", "value": "\n".join(f"{i}. {x}" for i, x in enumerate(steps, 1))[:1024],
                           "inline": False})
    tl = tourney_line(cls)
    extra = (f"Beta finals (lvl 30): {tl}" if tl else "") + " · Beta info; may still be tuned"
    race_label = d["races_label"]
    return {"title": f"{cls} in WoW: Forever", "color": K.COLORS.get(cls, C.BRAND_COLOR),
            "description": f"{d['role']}\n-# {race_label}: {d['races']}", "fields": fields,
            "footer": level_footer(level, extra.strip(" ·"))}


# ======================================================================= keybinds / macros / rotations
def _b(xs):
    return "\n".join(f"• {x}" for x in list(xs))[:1024]


def keybinds_embed(cls: str | None = None, topic: str = "basics", level: str = "standard") -> dict:
    level = norm_level(level)
    if topic == "controller":
        items = G.CONTROLLER[:4] if level == "brief" else G.CONTROLLER
        return {"title": "🎮 Playing WoW: Forever on a controller", "color": C.GREEN,
                "description": "\n".join(f"• {x}" for x in items)[:4000],
                "footer": level_footer(level, "Gamepad UI is labeled Alpha")}
    if cls and cls in G.CLASS_GUIDES:
        g = G.CLASS_GUIDES[cls]
        bf = g["bind_first"][:4] if level == "brief" else g["bind_first"]
        lay = g["layout"][:7] if level == "brief" else g["layout"]
        first = "\n".join(f"• **{a}**: {why}" for a, why in bf)[:1024]
        grid = "```\n" + "\n".join(f"{k:<12}{a}" for k, a in lay) + "\n```"
        fields = [{"name": "Bind these first", "value": first, "inline": False},
                  {"name": "A starter layout to copy", "value": grid[:1024], "inline": False}]
        if level == "detailed":
            ms = G.MACROS.get(cls, [])
            if ms:
                title, text, what, verified = ms[0]
                fields.append({"name": f"🧩 Try this macro: {title}" + ("" if verified else " (test in-game)"),
                               "value": f"```\n{text}\n```{what}"[:1024], "inline": False})
        return {"title": f"⌨️ {cls} keybinds", "color": K.COLORS.get(cls, C.BRAND_COLOR),
                "description": "Start here, then adjust to your hands. The point is: **never click these in a fight.**",
                "fields": fields, "footer": level_footer(level, "Some abilities come from talents or unlock later")}
    B = G.KEYBIND_BASICS
    fields = [{"name": "🌱 The basics", "value": _b(B["new"]), "inline": False}]
    if level != "brief":
        fields += [{"name": "🗺️ Where to put things", "value": _b(B["layout"]), "inline": False},
                   {"name": "🎯 Targeting", "value": _b(B["targeting"]), "inline": False}]
    return {"title": "⌨️ Keybinds 101", "color": C.GREEN, "description": G.KEYBIND_BASICS["howto"],
            "fields": fields, "footer": level_footer(level, "/keybinds class:<yours> for a starter layout")}


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


def rotation_embed(cls: str, level: str = "standard") -> dict | None:
    level = norm_level(level)
    rs = G.ROTATIONS.get(cls)
    if not rs:
        return None
    cut = 4 if level == "brief" else None
    fields = [{"name": spec, "value": "\n".join(f"{i}. {step}" for i, step in enumerate(steps[:cut], 1))[:1024], "inline": False}
              for spec, steps in rs]
    if level == "detailed":
        g = G.CLASS_GUIDES.get(cls)
        if g:
            fields.append({"name": "⌨️ Keep these on easy keys", "value": _b(f"**{a}**: {why}" for a, why in g["bind_first"][:4]),
                           "inline": False})
    return {"title": f"🔁 {cls}: what to press", "color": K.COLORS.get(cls, C.BRAND_COLOR),
            "description": "Simple leveling priorities. Not min-maxed; just a solid place to start.",
            "fields": fields, "footer": level_footer(level, "(n) = talent points needed")}


def quiz_embed(qi: int) -> dict:
    q, opts = G.QUIZ[qi]
    return {"title": f"🧭 Which class fits you? · {qi + 1}/{len(G.QUIZ)}", "description": f"**{q}**",
            "color": C.BRAND_COLOR, "footer": {"text": "Just for fun. Every class is viable in Forever."}}


def quiz_result_embed(answers: list[int], faction: str = "horde", level: str = "standard") -> dict:
    level = norm_level(level)
    ranked = G.score_quiz(answers)
    top, runner = ranked[0][0], ranked[1][0] if len(ranked) > 1 else None
    d = K.CLASSES[top]
    lines = [f"**Your match: {top}**", d["role"]]
    if faction == "horde":
        lines.append(f"-# Horde races: {d['races']}")
    if runner and level != "brief":
        lines += ["", f"**Also worth a look: {runner}**", K.CLASSES[runner]["role"]]
    if level == "detailed":
        lines += ["", "**Your top 4:** " + " · ".join(f"{c} ({p})" for c, p in ranked[:4])]
    lines += ["", "Use the buttons for tips, or run `/pickaclass` to join the roll call."]
    return {"title": "🧭 Your Forever class", "description": "\n".join(lines),
            "color": K.COLORS.get(top, C.BRAND_COLOR), "footer": level_footer(level)}


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
        "`/faq` → `/whichclass` → `/classtips` → `/keybinds` → `/pickaclass`",
        "💞 Never played, and someone you love talked you into it? `/draggedalong`", "",
        "**🗓️ Key dates**", *dates, "",
        "**📖 Everything else:** `/help` opens the full command spellbook. Set how much detail you get with `/mysettings`.",
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


def build_daily(cfg, *a, **k):
    """Daily post or check-in, faction-neutral unless the server picked Horde (1.4.2)."""
    post = _build_daily_raw(cfg, *a, **k)
    if post is None:  # nothing to post (e.g. after the countdown ends)
        return post
    f = getattr(cfg, "faction", None)
    post.embeds = [fit_faction_embed(e, f) for e in post.embeds]
    post.content = fit_faction(post.content, f)
    post.followup = fit_faction(post.followup, f)
    return post


def rollcall_embed(groups: dict, guild_name: str | None = None) -> dict:
    """/rollcall: who's playing what. Mentions render as names and never ping (sent with no allowed mentions)."""
    total = sum(len(v) for v in groups.values())
    if not total:
        return {"title": "⚔️ Roll call", "color": C.BRAND_COLOR,
                "description": "Nobody's picked a class yet. Be the first: tap a class on the daily post or use `/pickaclass`."}
    order = sorted(C.CLASSES, key=lambda c: (-len(groups.get(c, [])), c))
    fields = []
    for cls in order:
        ids = groups.get(cls, [])
        if not ids:
            continue
        shown = " ".join(f"<@{u}>" for u in ids[:40])
        more = f" +{len(ids) - 40} more" if len(ids) > 40 else ""
        fields.append({"name": f"{cls} · {len(ids)}", "value": (shown + more)[:1024], "inline": False})
    empty = [c for c in C.CLASSES if not groups.get(c)]
    desc = f"**{total}** {'person has' if total == 1 else 'people have'} picked a class."
    if empty:
        desc += f"\n-# Nobody yet: {', '.join(empty)}. Somebody please play a healer."  if any(c in empty for c in ("Priest", "Druid", "Shaman", "Paladin")) else f"\n-# Nobody yet: {', '.join(empty)}."
    return {"title": "⚔️ Roll call" + (f" · {guild_name}" if guild_name else ""), "color": C.BRAND_COLOR,
            "description": desc, "fields": fields[:25],
            "footer": {"text": "Pick or change yours with /pickaclass or the buttons on the daily post"}}


# ======================================================================= 1.5: /dungeons and /addons
def dungeons_embed(level: str = "standard") -> dict:
    level = norm_level(level)
    if level == "brief":
        lines = [f"**{n}** · {lv} · {where}" for n, lv, where, _ in C.DUNGEONS]
        return {"title": "🏰 Forever's new dungeons", "color": C.BRAND_COLOR,
                "description": "\n".join(lines) + "\n\n" + C.RAIDS_INFO,
                "footer": level_footer(level, "Levels and locations from Blizzard's preview")}
    fields = [{"name": f"{n} · {lv}", "value": f"📍 {where}\n{note}"[:1024], "inline": False}
              for n, lv, where, note in C.DUNGEONS]
    return {"title": "🏰 Forever's new dungeons",
            "color": C.BRAND_COLOR,
            "description": "Nine brand-new dungeons, on top of the original ones.\n" + C.RAIDS_INFO,
            "fields": fields, "footer": level_footer(level, "Levels and locations from Blizzard's preview")}


ADDON_TOPICS = ("picks", "install", "avoid")


def addons_embed(topic: str = "picks", level: str = "standard") -> dict:
    level = norm_level(level)
    topic = topic if topic in ADDON_TOPICS else "picks"
    foot = level_footer(level, "Addon support changes with each patch · /addons topic:install for setup")
    if topic == "install":
        return {"title": "🧩 Installing addons for Forever", "color": C.BRAND_COLOR,
                "description": "\n".join(f"{i}. {s}" for i, s in enumerate(C.ADDON_INSTALL, 1))
                               + "\n\n-# Forever runs on the modern client, so get the Forever or retail version of each addon, not Classic.",
                "footer": foot}
    if topic == "avoid":
        return {"title": "🧩 Addons to skip in Forever", "color": C.BRAND_COLOR,
                "description": "\n".join(f"• {s}" for s in C.ADDON_AVOID) + "\n\n" + C.ADDON_BUILTIN, "footer": foot}
    picks = C.ADDON_PICKS[:5] if level == "brief" else C.ADDON_PICKS
    desc = "\n".join(f"**{n}**: {what}" for n, what in picks)
    if level != "brief":
        desc += "\n\n" + C.ADDON_BUILTIN
    return {"title": "🧩 Starter addons for Forever", "color": C.BRAND_COLOR, "description": desc[:4000], "footer": foot}
