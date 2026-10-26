"""
Forever Sherpa: a multi-server Discord bot. Run: python -m forever_bot.bot

Loops
  refresh   every 30 min: fetch news/clips/videos once, shared by every server
  schedule  every 60 s:   per server, staging preview 1h before post time, then the daily post
  launch    every 30 s:   T-60m, T-10m and go-time pings on launch night
"""
import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord import app_commands
from discord.ext import commands, tasks

from . import __version__
from . import classes as K
from . import content as C
from . import guides as G
from . import plusone as P
from . import render as R
from .fetchers import Twitch, YouTube, refresh_all
from .logsetup import Timer, ev, setup_logging
from .store import GuildConfig, Store

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

setup_logging()
log = logging.getLogger("forever.bot")
slog = logging.getLogger("forever.sched")
clog = logging.getLogger("forever.cmd")

VERSION = (os.getenv("RENDER_GIT_COMMIT") or os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("GIT_SHA") or "dev")[:7]
STARTED = time.time()

POST_GRACE = timedelta(hours=3)        # bot was down at post time? still post within 3h
STAGING_LEAD = timedelta(minutes=60)
SNAP_MAX_AGE = 45 * 60
MILESTONE_WINDOW = timedelta(minutes=15)


def perm_fix_hint(channel, problem: str) -> str:
    if channel is None:
        return "Run `/setup` again and pick a channel I can see."
    return ("**Fix:** right-click the channel → **Edit Channel → Permissions → +** → add **"
            f"{channel.guild.me.display_name}** → allow **View Channel, Send Messages, Embed Links** "
            "(and Read Message History) → save. If the channel is synced to a private category, add me there. "
            "Then run `/postnow`.")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_hhmm(s: str):
    m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*", (s or "").lower())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h < 24 and 0 <= mi < 60):
        return None
    return h, mi


MAX_POSTS_PER_DAY = 4
MIN_GAP = timedelta(hours=2)
FREQUENCY_PRESETS = {  # times per day -> default times
    1: "12:00",
    2: "12:00,19:00",
    3: "09:00,13:00,19:00",
    4: "09:00,12:00,16:00,20:00",
}


def parse_times(s: str):
    """'12pm, 7:30pm' or '12:00,19:30' -> sorted [(h, m)], or None if anything is invalid.
    Accepts commas, semicolons, slashes, ' and ' or spaces between times."""
    parts = [p for p in re.split(r"\s*(?:,|;|/|\band\b|\s(?=\d))\s*", (s or "").strip().lower()) if p]
    out = []
    for p in parts:
        hm = parse_hhmm(p)
        if hm is None:
            return None
        if hm not in out:
            out.append(hm)
    out.sort()
    return out or None


def check_times(times) -> str | None:
    if not times:
        return "Times should look like `12:00` or `12pm, 7pm`."
    if len(times) > MAX_POSTS_PER_DAY:
        return f"Up to {MAX_POSTS_PER_DAY} posts a day."
    for (h1, m1), (h2, m2) in zip(times, times[1:]):
        if (h2 * 60 + m2) - (h1 * 60 + m1) < MIN_GAP.total_seconds() / 60:
            return "Keep posts at least 2 hours apart."
    return None


def fmt_times(times) -> str:
    return ", ".join(f"{h:02d}:{m:02d}" for h, m in times)


def guild_times(cfg: GuildConfig):
    return parse_times(cfg.post_time) or [(12, 0)]


def post_dt(cfg: GuildConfig, day, hm=None) -> datetime:
    h, mi = hm or guild_times(cfg)[0]
    return datetime(day.year, day.month, day.day, h, mi, tzinfo=ZoneInfo(cfg.tz))


def current_slot(cfg: GuildConfig, now: datetime) -> int:
    """Most recent slot whose time has passed today (0 if none yet)."""
    today = R.local_today(cfg.tz, now)
    local_now = now.astimezone(ZoneInfo(cfg.tz))
    slot = 0
    for i, hm in enumerate(guild_times(cfg)):
        if post_dt(cfg, today, hm) <= local_now:
            slot = i
    return slot


# ======================================================================= buttons
class DeepDiveButton(discord.ui.DynamicItem[discord.ui.Button], template=r"dd:(?P<key>[a-z0-9_-]{1,20})"):
    """🔎 Deep dive: answers privately so the channel stays clean. Survives restarts."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(discord.ui.Button(label="More detail", emoji="📖", style=discord.ButtonStyle.primary,
                                           custom_id=f"dd:{key}", row=2))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["key"])

    async def callback(self, interaction: discord.Interaction):
        try:
            lvl = level_for(interaction)
            e = R.deep_dive_embed(self.key, lvl)
        except Exception as exc:  # noqa: BLE001 - always answer inside Discord's 3-second window
            ev(clog, "more_detail_failed", logging.ERROR, exc_info=exc, key=self.key)
            e, lvl = None, "standard"
        if not e:
            return await interaction.response.send_message("That deep dive isn't available anymore. Try `/tips`.", ephemeral=True)
        await interaction.response.send_message(embed=E(e, lvl), ephemeral=True)
        ev(clog, "more_detail", guild=interaction.guild_id, user=interaction.user.id, key=self.key, detail=lvl)


def _who(interaction: discord.Interaction) -> str:
    u = interaction.user
    return (getattr(u, "display_name", None) or getattr(u, "name", "") or "?")[:40]


def _args(interaction: discord.Interaction) -> str | None:
    """Command options as k=v, for the log (e.g. page=plusone, cls=Mage)."""
    try:
        opts = (interaction.data or {}).get("options") or []
        flat = []
        for o in opts:
            if o.get("type") in (1, 2):  # subcommand / group
                opts += o.get("options") or []
                continue
            flat.append(f"{o.get('name')}:{str(o.get('value'))[:30]}")
        return ",".join(flat) or None
    except Exception:  # noqa: BLE001
        return None


def _control_name(cid: str, interaction: discord.Interaction) -> str:
    """Readable name for a button or dropdown. Our persistent ones have prefixes; ephemeral ones get
    random ids, so fall back to the message they're on."""
    names = {"dd": "more_detail", "cg": "class_guide", "po": "plusone", "pd": "panic", "ping": "ping_toggle",
             "rc": "rollcall"}
    head, _, rest = cid.partition(":")
    if head in names and rest:
        return f"{names[head]}:{rest}"[:60]
    msg = getattr(interaction, "message", None)
    title = ""
    if msg and msg.embeds:
        title = (msg.embeds[0].title or "")[:40]
    return f"other:{title or (msg.content[:40] if msg and msg.content else 'unknown')}"


def E(d: dict, lvl: str | None = None) -> discord.Embed:
    """Embed from a render dict, in plain words when the person picked Plus One's level."""
    return discord.Embed.from_dict(P.plainify(d) if lvl == "plain" else d)


def level_for(interaction: discord.Interaction) -> str:
    """Person's own setting, else the server's post verbosity, else Standard."""
    try:
        mine = bot.store.get_user_detail(interaction.user.id)
        if mine in R.LEVELS or mine == "plain":
            return mine
        c = bot.store.get_guild(interaction.guild_id) if interaction.guild_id else None
        return R.norm_level(c.verbosity if c else None)
    except Exception:  # noqa: BLE001 -- never let a settings lookup break a reply
        return "standard"


GUIDE_KINDS = {"tips": ("Class tips", "🎯"), "keys": ("Keybinds", "⌨️"), "macros": ("Macros", "🧩"), "rot": ("Rotation", "🔁")}


def guide_embed(cls: str, kind: str, faction: str = "horde", level: str = "standard") -> dict | None:
    return {"tips": lambda: R.classtips_embed(cls, faction, level), "keys": lambda: R.keybinds_embed(cls, "basics", level),
            "macros": lambda: R.macros_embed(cls), "rot": lambda: R.rotation_embed(cls, level)}.get(kind, lambda: None)()


class ClassGuideButton(discord.ui.DynamicItem[discord.ui.Button], template=r"cg:(?P<cls>[A-Za-z]{4,10}):(?P<kind>tips|keys|macros|rot)"):
    """Buttons under class cards: open that class's tips / keybinds / macros / rotation privately."""

    def __init__(self, cls: str, kind: str, label: str | None = None):
        self.cls, self.kind = cls, kind
        name, emoji = GUIDE_KINDS[kind]
        super().__init__(discord.ui.Button(label=label or name, emoji=emoji, style=discord.ButtonStyle.secondary,
                                           custom_id=f"cg:{cls}:{kind}"))

    @classmethod
    async def from_custom_id(cls_, interaction, item, match):
        return cls_(match["cls"], match["kind"])

    async def callback(self, interaction: discord.Interaction):
        c = bot.store.get_guild(interaction.guild_id) if interaction.guild_id else None
        lvl = level_for(interaction)
        e = guide_embed(self.cls, self.kind, c.faction if c else "horde", lvl)
        e = P.plainify(e) if (e and lvl == "plain") else e
        if not e:
            return await interaction.response.send_message("I don't have that one. Try `/help`.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed.from_dict(e), view=class_guide_view(self.cls, exclude=self.kind),
                                                ephemeral=True)
        ev(clog, "guide_button", guild=interaction.guild_id, user=interaction.user.id, cls=self.cls, kind=self.kind)


def class_guide_view(cls: str, exclude: str | None = None) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for kind in GUIDE_KINDS:
        if kind != exclude:
            v.add_item(ClassGuideButton(cls, kind))
    return v


class QuizView(discord.ui.View):
    """/whichclass: one question at a time, private to the person taking it."""

    def __init__(self, user_id: int, faction: str, answers: list[int] | None = None, level: str = "standard"):
        super().__init__(timeout=600)
        self.user_id, self.faction, self.answers, self.level = user_id, faction, answers or [], level
        q, opts = G.QUIZ[len(self.answers)]
        for i, (label, _) in enumerate(opts):
            b = discord.ui.Button(label=label[:80], style=discord.ButtonStyle.secondary, row=i // 3)
            b.callback = self._pick(i)
            self.add_item(b)

    def _pick(self, i: int):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("Run `/whichclass` to take your own quiz.", ephemeral=True)
            answers = self.answers + [i]
            if len(answers) < len(G.QUIZ):
                await interaction.response.edit_message(embed=discord.Embed.from_dict(R.quiz_embed(len(answers))),
                                                        view=QuizView(self.user_id, self.faction, answers, self.level))
                return
            ranked = G.score_quiz(answers)
            top = ranked[0][0]
            runner = ranked[1][0] if len(ranked) > 1 else None
            v = discord.ui.View(timeout=None)
            v.add_item(ClassGuideButton(top, "tips", f"{top} tips"))
            v.add_item(ClassGuideButton(top, "keys", f"{top} keybinds"))
            if runner:
                v.add_item(ClassGuideButton(runner, "tips", f"{runner} tips"))
            await interaction.response.edit_message(
                embed=E(R.quiz_result_embed(answers, self.faction, self.level), self.level), view=v)
            ev(clog, "quiz_done", guild=interaction.guild_id, user=interaction.user.id, top=top, runner=runner,
               answers="".join(map(str, answers)))
        return cb


class PingToggleButton(discord.ui.DynamicItem[discord.ui.Button], template=r"ping:(?P<role>[0-9]{5,25})"):
    """On the pinned card: lets members opt in/out of the ping role themselves."""

    def __init__(self, role_id: int):
        self.role_id = int(role_id)
        super().__init__(discord.ui.Button(label="Toggle pings", emoji="🔔", style=discord.ButtonStyle.secondary,
                                           custom_id=f"ping:{self.role_id}"))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["role"]))

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id) if guild else None
        if not role:
            return await interaction.response.send_message("That ping role doesn't exist anymore. Ask an admin to re-run `/pinpost`.", ephemeral=True)
        member = interaction.user
        try:
            if role in getattr(member, "roles", []):
                await member.remove_roles(role, reason="Forever Sherpa: opted out of pings")
                msg = f"🔕 Removed {role.mention}. You won't be pinged."
            else:
                await member.add_roles(role, reason="Forever Sherpa: opted in to pings")
                msg = f"🔔 Added {role.mention}. You'll get the daily ping."
            ev(clog, "ping_toggle", guild=guild.id, user=member.id, role=role.id, now_has=role not in member.roles)
        except discord.Forbidden:
            ev(clog, "ping_toggle_forbidden", logging.WARNING, guild=guild.id, role=role.id)
            msg = (f"I can't change {role.mention} yet. An admin needs to give me **Manage Roles** and drag my role "
                   f"**above** {role.mention} in Server Settings → Roles.")
        await interaction.response.send_message(msg, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


def _deep_key_from(message) -> str | None:
    for row in getattr(message, "components", None) or []:
        for comp in getattr(row, "children", []):
            cid = getattr(comp, "custom_id", None) or ""
            if cid.startswith("dd:"):
                return cid[3:]
    return None


class RollcallView(discord.ui.View):
    def __init__(self, bot: "ForeverBot", counts: dict | None = None, deep_key: str | None = None):
        super().__init__(timeout=None)
        self.bot = bot
        for i, cls in enumerate(C.CLASSES):
            n = (counts or {}).get(cls)
            label = f"{cls} · {n}" if counts is not None else cls
            btn = discord.ui.Button(label=label, custom_id=f"rc:{cls}", row=i // 5,
                                    style=discord.ButtonStyle.secondary)
            btn.callback = self._make_cb(cls)
            self.add_item(btn)
        if deep_key:
            self.add_item(DeepDiveButton(deep_key))

    def _make_cb(self, cls):
        async def cb(interaction: discord.Interaction):
            if not interaction.guild_id:
                return await interaction.response.send_message("Use this in a server.", ephemeral=True)
            try:
                self.bot.store.set_class(interaction.guild_id, interaction.user.id, cls)
                counts = self.bot.store.class_counts(interaction.guild_id)
                cfg = self.bot.store.get_guild(interaction.guild_id)
                lvl = level_for(interaction)
                tips = R.classtips_embed(cls, cfg.faction if cfg else "horde", lvl)
                extra = {"embed": E(tips, lvl)} if tips else {}
                if interaction.message and interaction.message.author.id == self.bot.user.id:
                    await interaction.response.edit_message(
                        view=RollcallView(self.bot, counts, _deep_key_from(interaction.message)))
                    await interaction.followup.send(f"Locked in: **{cls}**. Change anytime. Here's what's new for you:",
                                                    ephemeral=True, **extra)
                else:
                    await interaction.response.send_message(f"Locked in: **{cls}**.", ephemeral=True, **extra)
                ev(clog, "rollcall", guild=interaction.guild_id, user=interaction.user.id, cls=cls,
                   total=sum(counts.values()))
            except discord.HTTPException as e:
                ev(clog, "rollcall_failed", logging.WARNING, guild=interaction.guild_id, cls=cls, error=str(e)[:160])
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"Saved as **{cls}**.", ephemeral=True)
        return cb


# ======================================================================= bot
class ForeverBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents,
                         allowed_mentions=discord.AllowedMentions.none())
        self.store = Store(os.getenv("DB_PATH", "forever.db"))
        self.twitch = Twitch(os.getenv("TWITCH_CLIENT_ID", ""), os.getenv("TWITCH_CLIENT_SECRET", ""))
        self.youtube = YouTube(os.getenv("YOUTUBE_API_KEY", ""))
        self.snap: dict | None = None
        self._refresh_lock = asyncio.Lock()
        self.cmd_ids: dict[str, int] = {}
        self._said: set = set()  # (guild, day, slot, reason) already logged: keeps the 60s loop from spamming

    async def setup_hook(self):
        self.add_view(RollcallView(self))  # persistent: buttons keep working after restarts
        self.add_dynamic_items(DeepDiveButton, PingToggleButton, ClassGuideButton, PlusOneButton, PanicButton)
        cached = self.store.cache_get("_snapshot")[0]
        if cached:
            self.snap = cached
        st = self.store.stats()
        ev(log, "startup", release=__version__, version=VERSION, discord_py=discord.__version__, db=os.getenv("DB_PATH", "forever.db"),
           twitch=self.twitch.configured, youtube=self.youtube.configured, dev_guild=bool(os.getenv("DEV_GUILD_ID")),
           configured_guilds=st["guilds"], posts_logged=st["posts"], rollcall_entries=st["rollcall"],
           cached_snapshot=bool(cached), launch=C.LAUNCH.isoformat())
        dev = os.getenv("DEV_GUILD_ID")
        if dev:
            g = discord.Object(id=int(dev))
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        try:
            synced = await self.tree.sync()
            self.cmd_ids = {c.name: c.id for c in synced}  # for clickable </cmd:id> mentions in /help
            ev(log, "commands_synced", count=len(synced))
        except discord.HTTPException as e:
            ev(log, "commands_sync_failed", logging.ERROR, error=str(e)[:200])
        self.refresh_loop.start()
        self.schedule_loop.start()
        self.launch_loop.start()
        self.heartbeat_loop.start()

    async def on_ready(self):
        ev(log, "ready", user=str(self.user), guilds=len(self.guilds), latency_ms=self.latency * 1000,
           servers=",".join(f"{g.name}({g.id})" for g in self.guilds[:10]) or "-")

    async def on_resumed(self):
        ev(log, "gateway_resumed")

    async def on_disconnect(self):
        ev(log, "gateway_disconnected", logging.WARNING, hint="discord.py reconnects automatically")

    async def on_guild_join(self, guild):
        ev(log, "guild_join", guild=guild.id, name=guild.name, members=guild.member_count, total=len(self.guilds))

    async def on_guild_remove(self, guild):
        self.store.remove_guild(guild.id)
        ev(log, "guild_remove", guild=guild.id, name=guild.name, total=len(self.guilds))

    async def on_app_command_completion(self, interaction: discord.Interaction, command):
        ev(clog, "command", name=command.qualified_name, guild=interaction.guild_id, user=interaction.user.id,
           who=_who(interaction), args=_args(interaction),
           ms=(discord.utils.utcnow() - interaction.created_at).total_seconds() * 1000)

    async def on_interaction(self, interaction: discord.Interaction):
        """1.3.2: one line for every button press and dropdown pick, on any message."""
        try:
            if interaction.type != discord.InteractionType.component:
                return
            data = interaction.data or {}
            cid = str(data.get("custom_id", ""))
            vals = data.get("values") or []
            ev(clog, "click", guild=interaction.guild_id, user=interaction.user.id, who=_who(interaction),
               control=_control_name(cid, interaction), picked=",".join(map(str, vals))[:80] or None,
               kind="dropdown" if vals else "button")
        except Exception:  # noqa: BLE001 - logging must never get in the way
            pass

    def say_once(self, logger, dedupe: tuple, event: str, level=logging.INFO, /, **fields):
        if dedupe not in self._said:
            self._said.add(dedupe)
            if len(self._said) > 5000:
                self._said.clear()
            ev(logger, event, level, **fields)

    # ---------------------------------------------------------- data
    async def refresh(self, force=False):
        async with self._refresh_lock:
            if not force and self.snap and time.time() - self.snap.get("fetched_at", 0) < 60:
                return self.snap
            try:
                self.snap = await asyncio.wait_for(refresh_all(self.store, self.twitch, self.youtube), timeout=120)
                self.store.cache_put("_snapshot", self.snap)
            except asyncio.TimeoutError:
                ev(log, "refresh_timeout", logging.ERROR, timeout_s=120, keeping="previous snapshot")
            except Exception as e:  # noqa: BLE001
                ev(log, "refresh_crashed", logging.ERROR, exc_info=e, keeping="previous snapshot")
            return self.snap

    @tasks.loop(minutes=30)
    async def refresh_loop(self):
        await self.refresh(force=True)
        self.store.prune_seen()

    # ---------------------------------------------------------- posting
    def _can_post(self, channel) -> str | None:
        if channel is None:
            return "channel not found (deleted, or bot can't see it)"
        perms = channel.permissions_for(channel.guild.me)
        missing = [n for n, ok in (("View Channel", perms.view_channel), ("Send Messages", perms.send_messages),
                                   ("Embed Links", perms.embed_links)) if not ok]
        return f"missing permissions: {', '.join(missing)}" if missing else None

    def build(self, cfg: GuildConfig, now: datetime, slot: int = 0):
        snap = self.snap or {}
        ids = [x["id"] for k in ("news", "clips", "videos") for x in snap.get(k, [])]
        unseen = self.store.unseen(cfg.guild_id, ids)
        today = R.local_today(cfg.tz, now).isoformat()
        return R.build_daily(cfg, now, snap, self.store.class_counts(cfg.guild_id), unseen,
                             include_news=(cfg.news_off_date != today), slot=slot)

    async def send_post(self, channel, post: R.Post, ping_role_id=None):
        mentions = discord.AllowedMentions(roles=[discord.Object(ping_role_id)]) if ping_role_id else discord.AllowedMentions.none()
        counts = self.store.class_counts(channel.guild.id) if post.rollcall else None
        view = None
        if post.rollcall:
            view = RollcallView(self, counts, post.deep_key)
        elif post.deep_key:
            view = discord.ui.View(timeout=None)
            view.add_item(DeepDiveButton(post.deep_key))
        msg = await channel.send(content=post.content or None,
                                 embeds=[discord.Embed.from_dict(e) for e in post.embeds],
                                 view=view,
                                 allowed_mentions=mentions)
        follow_id = None
        if post.followup:
            try:
                follow_id = (await channel.send(post.followup, allowed_mentions=discord.AllowedMentions.none())).id
            except discord.HTTPException as e:
                ev(log, "followup_failed", logging.WARNING, guild=channel.guild.id, channel=channel.id,
                   status=getattr(e, "status", None), error=str(e)[:160])
        return msg.id, follow_id

    async def post_daily(self, cfg: GuildConfig, now: datetime, force=False, slot: int = 0) -> str:
        if self.snap is None or time.time() - self.snap.get("fetched_at", 0) > SNAP_MAX_AGE:
            await self.refresh(force=True)
        t = Timer().__enter__()
        post = self.build(cfg, now, slot)
        if post is None:
            return "Nothing to post: the countdown is finished."
        if not force and self.store.was_posted(cfg.guild_id, "daily", post.key):
            ev(slog, "post_skipped", logging.DEBUG, guild=cfg.guild_id, key=post.key, reason="already_posted")
            return "Already posted for this time slot."
        channel = self.get_channel(cfg.channel_id)
        problem = self._can_post(channel)
        if problem:
            self.say_once(slog, (cfg.guild_id, post.key, "noperm"), "post_blocked", logging.ERROR,
                          guild=cfg.guild_id, channel=cfg.channel_id, key=post.key, reason=problem)
            hint = perm_fix_hint(channel, problem)
            await self.notify_staging(cfg, f"⚠️ Couldn't post the daily countdown: {problem}.\n{hint}")
            return f"⚠️ I can't post in <#{cfg.channel_id}>: {problem}.\n{hint}"
        try:
            msg_id, follow_id = await self.send_post(channel, post, cfg.ping_role_id)
        except discord.HTTPException as e:
            ev(slog, "post_failed", logging.ERROR, exc_info=e, guild=cfg.guild_id, channel=cfg.channel_id,
               key=post.key, status=getattr(e, "status", None), code=getattr(e, "code", None))
            await self.notify_staging(cfg, f"⚠️ Discord rejected the countdown post: {str(e)[:150]}")
            return f"Discord rejected the post: {str(e)[:150]}"
        self.store.mark_posted(cfg.guild_id, "daily", post.key)
        self.store.mark_seen(cfg.guild_id, post.used_ids)
        n_news = sum(1 for i in post.used_ids if i.startswith("news:"))
        n_clips = sum(1 for i in post.used_ids if i.startswith("twitch:"))
        n_vids = sum(1 for i in post.used_ids if i.startswith("yt:"))
        ev(slog, "post_sent", guild=cfg.guild_id, guild_name=getattr(channel.guild, "name", "?"), channel=channel.id,
           key=post.key, slot=slot, type="full" if slot == 0 else "checkin", forced=force,
           chars=sum(len(e.get("description", "")) for e in post.embeds), embeds=len(post.embeds),
           news=n_news, clips=n_clips, videos=n_vids, ping=bool(post.content), message=msg_id,
           followup=follow_id, ms=t.elapsed_ms)
        await self.refresh_pin(cfg, f"https://discord.com/channels/{cfg.guild_id}/{channel.id}/{msg_id}")
        return "Posted."

    def pin_view(self, cfg: GuildConfig):
        if not (C.NOTIFY and cfg.ping_role_id):
            return None
        v = discord.ui.View(timeout=None)
        v.add_item(PingToggleButton(cfg.ping_role_id))
        return v

    async def refresh_pin(self, cfg: GuildConfig, latest_url: str | None = None):
        """Keep the pinned start-here card current. Never raises."""
        if not (cfg.pin_channel_id and cfg.pin_message_id):
            return
        ch = self.get_channel(cfg.pin_channel_id)
        try:
            if ch is None:
                raise LookupError("pin channel gone")
            msg = ch.get_partial_message(cfg.pin_message_id)
            embed = R.pinned_embed(cfg, guild_times(cfg), now_utc(), latest_url, cfg.ping_role_id if C.NOTIFY else None)
            await msg.edit(embed=discord.Embed.from_dict(embed), view=self.pin_view(cfg))
            ev(slog, "pin_refreshed", logging.DEBUG, guild=cfg.guild_id, message=cfg.pin_message_id)
        except (discord.NotFound, LookupError):
            ev(slog, "pin_missing", logging.WARNING, guild=cfg.guild_id, message=cfg.pin_message_id,
               action="forgetting it; run /pinpost to make a new one")
            cfg.pin_channel_id = cfg.pin_message_id = None
            self.store.upsert_guild(cfg)
        except discord.HTTPException as e:
            ev(slog, "pin_refresh_failed", logging.WARNING, guild=cfg.guild_id, status=getattr(e, "status", None),
               error=str(e)[:160])

    async def notify_staging(self, cfg: GuildConfig, text: str):
        ch = self.get_channel(cfg.staging_channel_id) if cfg.staging_channel_id else None
        if ch and not self._can_post(ch):
            try:
                await ch.send(text, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException as e:
                ev(log, "staging_notify_failed", logging.WARNING, guild=cfg.guild_id, error=str(e)[:120])
        else:
            ev(log, "staging_unavailable", logging.DEBUG, guild=cfg.guild_id, note=text[:120])

    @tasks.loop(seconds=60)
    async def schedule_loop(self):
        now = now_utc()
        for cfg in self.store.all_guilds():
            try:
                await self._tick_guild(cfg, now)
            except Exception as e:  # noqa: BLE001 -- one bad server never blocks the rest
                ev(slog, "tick_crashed", logging.ERROR, exc_info=e, guild=cfg.guild_id)
            await asyncio.sleep(0.5)  # gentle fan-out

    async def _tick_guild(self, cfg: GuildConfig, now: datetime):
        today = R.local_today(cfg.tz, now)
        local_now = now.astimezone(ZoneInfo(cfg.tz))
        times = guild_times(cfg)
        dues = [post_dt(cfg, today, hm) for hm in times]
        first = dues[0]
        # staging preview: full post only, an hour before the first slot
        if cfg.staging_channel_id and first - STAGING_LEAD <= local_now < first \
                and not self.store.was_posted(cfg.guild_id, "staging", today.isoformat()):
            await self.refresh()
            post = self.build(cfg, now + (first - local_now), 0)  # render as of post time
            ch = self.get_channel(cfg.staging_channel_id)
            problem = self._can_post(ch)
            if post and not problem:
                extra = f" · then {len(times) - 1} check-in(s) at {fmt_times(times[1:])}" if len(times) > 1 else ""
                try:
                    await ch.send(f"👀 **Preview** · posts <t:{int(first.timestamp())}:R>{extra} · `/hold` to skip "
                                  f"today, `/skipnews` to drop news\n{R.health_text(self.snap)}",
                                  allowed_mentions=discord.AllowedMentions.none())
                    await self.send_post(ch, post)
                    ev(slog, "staging_preview_sent", guild=cfg.guild_id, channel=ch.id, posts_at=first.isoformat())
                except discord.HTTPException as e:
                    ev(slog, "staging_preview_failed", logging.WARNING, guild=cfg.guild_id, error=str(e)[:160])
            elif problem:
                ev(slog, "staging_preview_blocked", logging.WARNING, guild=cfg.guild_id, reason=problem)
            self.store.mark_posted(cfg.guild_id, "staging", today.isoformat())
        if cfg.hold_date == today.isoformat():
            self.say_once(slog, (cfg.guild_id, today, "hold"), "day_on_hold", guild=cfg.guild_id, day=today.isoformat())
            return
        kind, _ = R.phase(cfg.tz, now)
        if kind == "done":
            return
        # each slot: post if due, within grace, and before the next slot starts
        for slot, due in enumerate(dues):
            window_end = min(due + POST_GRACE, dues[slot + 1] if slot + 1 < len(dues) else due + POST_GRACE)
            key = f"{kind}:{today.isoformat()}:{slot}"
            if due <= local_now < window_end and not self.store.was_posted(cfg.guild_id, "daily", key):
                late_min = (local_now - due).total_seconds() / 60
                if late_min > 5:
                    self.say_once(slog, (cfg.guild_id, key, "late"), "slot_late", logging.WARNING, guild=cfg.guild_id,
                                  key=key, late_min=late_min, hint="bot was offline or busy at post time")
                await self.post_daily(cfg, now, slot=slot)
            elif local_now >= window_end and not self.store.was_posted(cfg.guild_id, "daily", key):
                self.say_once(slog, (cfg.guild_id, key, "missed"), "slot_missed", logging.WARNING, guild=cfg.guild_id,
                              key=key, due=due.isoformat(), window_end=window_end.isoformat(),
                              hint="bot was offline for the whole window; /postnow to send it")

    @tasks.loop(seconds=30)
    async def launch_loop(self):
        if not C.NOTIFY:
            return  # 1.1.2: no standalone reminder / countdown posts
        now = now_utc()
        for iso, key, text in C.EVENT_PINGS:
            at = datetime.fromisoformat(iso)
            if at <= now < at + MILESTONE_WINDOW:
                await self.send_event_ping(key, text)
        for minutes, _ in R.MILESTONES:
            at = C.LAUNCH - timedelta(minutes=minutes)
            if not (at <= now < at + MILESTONE_WINDOW):
                continue
            for cfg in self.store.all_guilds():
                if self.store.was_posted(cfg.guild_id, "milestone", str(minutes)):
                    continue
                ch = self.get_channel(cfg.channel_id)
                problem = self._can_post(ch)
                if problem:
                    self.say_once(slog, (cfg.guild_id, "milestone", minutes), "milestone_blocked", logging.ERROR,
                                  guild=cfg.guild_id, minutes=minutes, reason=problem)
                    continue
                try:
                    text = R.milestone_text(minutes, cfg.faction)
                    ping = f"<@&{cfg.ping_role_id}> " if cfg.ping_role_id else ""
                    await ch.send(ping + text + f"\n<t:{int(C.LAUNCH.timestamp())}:R>",
                                  allowed_mentions=discord.AllowedMentions(
                                      roles=[discord.Object(cfg.ping_role_id)]) if cfg.ping_role_id else discord.AllowedMentions.none())
                    self.store.mark_posted(cfg.guild_id, "milestone", str(minutes))
                    ev(slog, "milestone_sent", guild=cfg.guild_id, minutes_before=minutes)
                except discord.HTTPException as e:
                    ev(slog, "milestone_failed", logging.ERROR, guild=cfg.guild_id, minutes_before=minutes,
                       status=getattr(e, "status", None), error=str(e)[:160])
                await asyncio.sleep(0.5)

    async def send_event_ping(self, key: str, text: str):
        for cfg in self.store.all_guilds():
            if self.store.was_posted(cfg.guild_id, "event", key):
                continue
            ch = self.get_channel(cfg.channel_id)
            problem = self._can_post(ch)
            if problem:
                self.say_once(slog, (cfg.guild_id, "event", key), "event_blocked", logging.ERROR,
                              guild=cfg.guild_id, event_key=key, reason=problem)
                continue
            ping = f"<@&{cfg.ping_role_id}> " if cfg.ping_role_id else ""
            try:
                await ch.send(ping + text, allowed_mentions=discord.AllowedMentions(
                    roles=[discord.Object(cfg.ping_role_id)]) if cfg.ping_role_id else discord.AllowedMentions.none())
                self.store.mark_posted(cfg.guild_id, "event", key)
                ev(slog, "event_sent", guild=cfg.guild_id, event_key=key)
            except discord.HTTPException as e:
                ev(slog, "event_failed", logging.ERROR, guild=cfg.guild_id, event_key=key, error=str(e)[:160])
            await asyncio.sleep(0.5)

    def next_post(self, cfg: GuildConfig, now: datetime):
        """Next scheduled (slot, datetime) for this server, looking up to 2 days ahead."""
        local_now = now.astimezone(ZoneInfo(cfg.tz))
        for add in (0, 1, 2):
            day = (local_now + timedelta(days=add)).date()
            for slot, hm in enumerate(guild_times(cfg)):
                due = post_dt(cfg, day, hm)
                if due > local_now:
                    return slot, due
        return None

    @tasks.loop(minutes=30)
    async def heartbeat_loop(self):
        now = now_utc()
        cfgs = self.store.all_guilds()
        nxt = [n for c in cfgs if (n := self.next_post(c, now))]
        soonest = min((d for _, d in nxt), default=None)
        snap_age = (time.time() - self.snap["fetched_at"]) / 60 if self.snap else None
        ev(log, "heartbeat", release=__version__, version=VERSION, uptime_h=(time.time() - STARTED) / 3600, guilds=len(self.guilds),
           configured=len(cfgs), latency_ms=self.latency * 1000, snapshot_age_min=snap_age,
           next_post=soonest.isoformat() if soonest else "-",
           loops_ok=all(l.is_running() for l in (self.refresh_loop, self.schedule_loop, self.launch_loop)))
        for name, loop in (("refresh", self.refresh_loop), ("schedule", self.schedule_loop), ("launch", self.launch_loop)):
            if not loop.is_running():
                ev(log, "loop_stopped", logging.ERROR, loop=name, action="restarting")
                loop.restart()

    @refresh_loop.error
    @schedule_loop.error
    @launch_loop.error
    async def _loop_error(self, error):
        ev(log, "loop_crashed", logging.ERROR, exc_info=error, note="heartbeat will restart it")

    @refresh_loop.before_loop
    @schedule_loop.before_loop
    @launch_loop.before_loop
    @heartbeat_loop.before_loop
    async def _wait_ready(self):
        await self.wait_until_ready()


bot = ForeverBot()


def cfg_for(interaction) -> GuildConfig:
    return bot.store.get_guild(interaction.guild_id) or GuildConfig(guild_id=interaction.guild_id)


def tz_of(interaction) -> str:
    c = bot.store.get_guild(interaction.guild_id) if interaction.guild_id else None
    return c.tz if c else C.DEFAULT_TZ


# ======================================================================= admin commands
admin = app_commands.default_permissions(manage_guild=True)


@bot.tree.command(name="setup", description="Set the countdown channel, ping role and post time")
@app_commands.guild_only()
@admin
@app_commands.describe(channel="Where the daily countdown posts", ping_role="Role to ping (optional)",
                       staging="Private channel for previews and alerts (optional)",
                       post_time="Post time(s), like 12pm or 12pm, 7pm (up to 4)", timezone="IANA zone, like America/Chicago",
                       faction="Which faction your server leans")
@app_commands.choices(faction=[app_commands.Choice(name=n, value=n.lower()) for n in ("Horde", "Alliance", "Neutral")])
async def setup_cmd(interaction: discord.Interaction, channel: discord.TextChannel,
                    ping_role: discord.Role | None = None, staging: discord.TextChannel | None = None,
                    post_time: str = C.DEFAULT_POST_TIME, timezone: str = C.DEFAULT_TZ,
                    faction: app_commands.Choice[str] | None = None):
    times = parse_times(post_time)
    err = check_times(times)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return await interaction.response.send_message(
            "Unknown time zone. Use one like `America/Chicago`, `America/New_York`, `Europe/London`.", ephemeral=True)
    problem = bot._can_post(channel)
    if problem:
        return await interaction.response.send_message(
            f"I can't post in {channel.mention}: {problem}.\n{perm_fix_hint(channel, problem)}", ephemeral=True)
    if staging and bot._can_post(staging):
        return await interaction.response.send_message(
            f"I can't post in {staging.mention}: {bot._can_post(staging)}.\n{perm_fix_hint(staging, '')}", ephemeral=True)
    cfg = cfg_for(interaction)
    cfg.channel_id, cfg.ping_role_id = channel.id, ping_role.id if ping_role else None
    cfg.staging_channel_id = staging.id if staging else None
    cfg.post_time, cfg.tz, cfg.enabled = fmt_times(times).replace(" ", ""), timezone, True
    if faction:
        cfg.faction = faction.value
    bot.store.upsert_guild(cfg)
    if ping_role and not ping_role.mentionable and not channel.permissions_for(interaction.guild.me).mention_everyone:
        warn = f"\n⚠️ {ping_role.mention} isn't mentionable. Turn on *Allow anyone to @mention this role* or the ping won't fire."
    else:
        warn = ""
    await interaction.response.send_message(
        f"✅ Countdown posts in {channel.mention} daily at **{fmt_times(times)}** ({timezone})."
        f"{' The first is the full post; the rest are short check-ins.' if len(times) > 1 else ''}"
        f"{' Pinging ' + ping_role.mention + '.' if ping_role else ''}"
        f"{' Previews go to ' + staging.mention + '.' if staging else ''}\n"
        f"Try `/preview` to see today's post, or `/postnow` to post it right away.{warn}",
        ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="preview", description="Privately preview today's countdown post")
@app_commands.guild_only()
@admin
async def preview_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    await bot.refresh()
    cfg = cfg_for(interaction)
    post = bot.build(cfg, now_utc())
    if not post:
        return await interaction.followup.send("The countdown is finished.", ephemeral=True)
    times = guild_times(cfg)
    sched = f"Schedule: {fmt_times(times)} {cfg.tz}" + (" (first = full post, rest = check-ins)" if len(times) > 1 else "")
    await interaction.followup.send(content=f"{sched}\n{R.health_text(bot.snap)}",
                                    embeds=[discord.Embed.from_dict(e) for e in post.embeds], ephemeral=True)
    if post.followup:
        await interaction.followup.send(post.followup, ephemeral=True)


@bot.tree.command(name="frequency", description="How many times a day the countdown posts")
@app_commands.guild_only()
@admin
@app_commands.describe(per_day="Posts per day (uses sensible default times)",
                       times="Or exact times, like 12pm, 7pm (overrides per_day)")
@app_commands.choices(per_day=[app_commands.Choice(name=f"{n}x a day ({FREQUENCY_PRESETS[n].replace(',', ', ')})", value=n)
                               for n in sorted(FREQUENCY_PRESETS)])
async def frequency_cmd(interaction: discord.Interaction, per_day: app_commands.Choice[int] | None = None,
                        times: str | None = None):
    cfg = bot.store.get_guild(interaction.guild_id)
    if not cfg or not cfg.channel_id:
        return await interaction.response.send_message("Run `/setup` first.", ephemeral=True)
    if not per_day and not times:
        cur = guild_times(cfg)
        return await interaction.response.send_message(
            f"Posting **{len(cur)}x a day** at {fmt_times(cur)} ({cfg.tz}). Pick `per_day` or set `times` to change it.",
            ephemeral=True)
    parsed = parse_times(times) if times else parse_times(FREQUENCY_PRESETS[per_day.value])
    err = check_times(parsed)
    if err:
        return await interaction.response.send_message(err, ephemeral=True)
    cfg.post_time = fmt_times(parsed).replace(" ", "")
    bot.store.upsert_guild(cfg)
    await bot.refresh_pin(cfg)
    note = " The first is the full post; the rest are short check-ins with a new tip, a fact, and only fresh news and clips." \
        if len(parsed) > 1 else ""
    await interaction.response.send_message(
        f"✅ Now posting **{len(parsed)}x a day** at {fmt_times(parsed)} ({cfg.tz}).{note}\n"
        f"-# Slots that already passed today won't fire until tomorrow; `/postnow` posts one right away.",
        ephemeral=True)


@bot.tree.command(name="postnow", description="Post now (today's full post first, then check-ins)")
@app_commands.guild_only()
@admin
async def postnow_cmd(interaction: discord.Interaction):
    cfg = bot.store.get_guild(interaction.guild_id)
    if not cfg or not cfg.channel_id:
        return await interaction.response.send_message("Run `/setup` first.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    now = now_utc()
    kind, _ = R.phase(cfg.tz, now)
    today = R.local_today(cfg.tz, now).isoformat()
    slot = 0
    if bot.store.was_posted(cfg.guild_id, "daily", f"{kind}:{today}:0"):
        slot = max(1, current_slot(cfg, now))
        if slot >= len(guild_times(cfg)):
            return await interaction.followup.send(
                "Today's full post is already up, and you're on 1 post a day. Use `/frequency` to add check-ins.",
                ephemeral=True)
    msg = await bot.post_daily(cfg, now, slot=slot)
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(name="hold", description="Skip today's countdown post")
@app_commands.guild_only()
@admin
async def hold_cmd(interaction: discord.Interaction):
    cfg = cfg_for(interaction)
    cfg.hold_date = R.local_today(cfg.tz, now_utc()).isoformat()
    bot.store.upsert_guild(cfg)
    await interaction.response.send_message("⏸️ All of today's posts are on hold. `/resume` to undo.", ephemeral=True)


@bot.tree.command(name="resume", description="Undo /hold for today")
@app_commands.guild_only()
@admin
async def resume_cmd(interaction: discord.Interaction):
    cfg = cfg_for(interaction)
    cfg.hold_date = None
    bot.store.upsert_guild(cfg)
    await interaction.response.send_message("▶️ Back on. Today's post goes out on schedule.", ephemeral=True)


@bot.tree.command(name="skipnews", description="Post today without the news section")
@app_commands.guild_only()
@admin
async def skipnews_cmd(interaction: discord.Interaction):
    cfg = cfg_for(interaction)
    cfg.news_off_date = R.local_today(cfg.tz, now_utc()).isoformat()
    bot.store.upsert_guild(cfg)
    await interaction.response.send_message("📰 News is off for today's post.", ephemeral=True)


@bot.tree.command(name="status", description="Bot settings and data source health")
@app_commands.guild_only()
@admin
async def status_cmd(interaction: discord.Interaction):
    cfg = bot.store.get_guild(interaction.guild_id)
    now = now_utc()
    lines = []
    if cfg and cfg.channel_id:
        lines.append(f"**Setup:** <#{cfg.channel_id}> · {len(guild_times(cfg))}x a day at {fmt_times(guild_times(cfg))} "
                     f"{cfg.tz} · {cfg.faction} · posts: {R.LEVEL_LABEL[R.norm_level(cfg.verbosity)]}"
                     f"{' · ⏸️ ON HOLD today' if cfg.hold_date == R.local_today(cfg.tz, now).isoformat() else ''}")
        nxt = bot.next_post(cfg, now)
        if nxt:
            slot, due = nxt
            lines.append(f"**Next post:** <t:{int(due.timestamp())}:F> (<t:{int(due.timestamp())}:R>) · "
                         f"{'full post' if slot == 0 else 'check-in'}")
        recent = bot.store.recent_posts(cfg.guild_id, 4)
        if recent:
            lines.append("**Recent:** " + " · ".join(f"{k} `{key}` <t:{int(at)}:R>" for k, key, at in recent))
        problem = bot._can_post(bot.get_channel(cfg.channel_id))
        if problem:
            lines.append(f"⚠️ **Can't post:** {problem}")
    else:
        lines.append("Not set up. Run `/setup`.")
    lines.append(R.health_text(bot.snap))
    lines.append(f"-# v{__version__} (`{VERSION}`) · up {(time.time() - STARTED) / 3600:.1f}h · latency {bot.latency * 1000:.0f}ms · "
                 f"{len(bot.guilds)} server(s)")
    await interaction.response.send_message("\n".join(lines)[:1990], ephemeral=True,
                                            allowed_mentions=discord.AllowedMentions.none())


# ======================================================================= public commands
@bot.tree.command(name="countdown", description="How long until WoW: Forever")
async def countdown_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed.from_dict(R.countdown_embed(tz_of(interaction), now_utc())))


@bot.tree.command(name="tourney", description="Forever Open $100K beta duel tournament results")
async def tourney_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed.from_dict(R.tourney_embed()))


@bot.tree.command(name="faq", description="New to WoW: Forever? Start here")
async def faq_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed.from_dict(R.faq_embed()))


@bot.tree.command(name="dates", description="Key WoW: Forever dates")
async def dates_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed.from_dict(R.dates_embed(tz_of(interaction), now_utc())))


@bot.tree.command(name="tips", description="Tips and tricks by topic")
@app_commands.describe(topic="What do you want tips on?")
@app_commands.choices(topic=[app_commands.Choice(name=t.capitalize(), value=t) for t in R.TIP_TOPICS])
async def tips_cmd(interaction: discord.Interaction, topic: app_commands.Choice[str] | None = None):
    await interaction.response.send_message(
        embed=E(R.tips_embed(topic.value if topic else "basics", lvl := level_for(interaction)), lvl), ephemeral=True)


@bot.tree.command(name="classtips", description="Forever changes and tips for a class")
@app_commands.describe(cls="Which class?", share="Post it for everyone instead of just you")
@app_commands.rename(cls="class")
@app_commands.choices(cls=[app_commands.Choice(name=c, value=c) for c in K.CLASSES])
async def classtips_cmd(interaction: discord.Interaction, cls: app_commands.Choice[str], share: bool = False):
    c = bot.store.get_guild(interaction.guild_id) if interaction.guild_id else None
    lvl = level_for(interaction)
    e = R.classtips_embed(cls.value, c.faction if c else "horde", lvl)
    await interaction.response.send_message(embed=E(e, lvl if not share else "standard"), ephemeral=not share,
                                            view=class_guide_view(cls.value, exclude="tips"))


CLASS_CHOICES = [app_commands.Choice(name=c, value=c) for c in K.CLASSES]


@bot.tree.command(name="keybinds", description="What to bind and where. Stop clicking!")
@app_commands.describe(cls="Get a starter layout for a class", topic="General basics, or controller setup")
@app_commands.rename(cls="class")
@app_commands.choices(cls=CLASS_CHOICES, topic=[app_commands.Choice(name="Keyboard basics", value="basics"),
                                                app_commands.Choice(name="Controller / gamepad", value="controller")])
async def keybinds_cmd(interaction: discord.Interaction, cls: app_commands.Choice[str] | None = None,
                       topic: app_commands.Choice[str] | None = None):
    t = topic.value if topic else "basics"
    lvl = level_for(interaction)
    e = R.keybinds_embed(cls.value if cls and t != "controller" else None, t, lvl)
    e = P.plainify(e) if lvl == "plain" else e
    view = class_guide_view(cls.value, exclude="keys") if cls and t != "controller" else None
    await interaction.response.send_message(embed=discord.Embed.from_dict(e), ephemeral=True,
                                            **({"view": view} if view else {}))


@bot.tree.command(name="macros", description="Copy-paste macros for a class")
@app_commands.describe(cls="Which class?")
@app_commands.rename(cls="class")
@app_commands.choices(cls=CLASS_CHOICES)
async def macros_cmd(interaction: discord.Interaction, cls: app_commands.Choice[str]):
    await interaction.response.send_message(embed=discord.Embed.from_dict(R.macros_embed(cls.value)), ephemeral=True,
                                            view=class_guide_view(cls.value, exclude="macros"))


@bot.tree.command(name="rotation", description="Simple leveling priorities for every spec of a class")
@app_commands.describe(cls="Which class?")
@app_commands.rename(cls="class")
@app_commands.choices(cls=CLASS_CHOICES)
async def rotation_cmd(interaction: discord.Interaction, cls: app_commands.Choice[str]):
    await interaction.response.send_message(embed=E(R.rotation_embed(cls.value, lvl := level_for(interaction)), lvl), ephemeral=True,
                                            view=class_guide_view(cls.value, exclude="rot"))


@bot.tree.command(name="whichclass", description="Not sure what to play? Take a quick quiz")
async def whichclass_cmd(interaction: discord.Interaction):
    c = bot.store.get_guild(interaction.guild_id) if interaction.guild_id else None
    await interaction.response.send_message(embed=discord.Embed.from_dict(R.quiz_embed(0)), ephemeral=True,
                                            view=QuizView(interaction.user.id, c.faction if c else "horde", level=level_for(interaction)))


LEVEL_CHOICES = [app_commands.Choice(name="Brief: just the essentials", value="brief"),
                 app_commands.Choice(name="Standard: the full picture", value="standard"),
                 app_commands.Choice(name="Detailed: everything, with extra context", value="detailed")]


@bot.tree.command(name="verbosity", description="How detailed this server's countdown posts are")
@app_commands.guild_only()
@admin
@app_commands.describe(level="Brief, Standard or Detailed")
@app_commands.choices(level=LEVEL_CHOICES)
async def verbosity_cmd(interaction: discord.Interaction, level: app_commands.Choice[str] | None = None):
    cfg = bot.store.get_guild(interaction.guild_id)
    if not cfg or not cfg.channel_id:
        return await interaction.response.send_message("Run `/setup` first.", ephemeral=True)
    if not level:
        return await interaction.response.send_message(
            f"Posts here are **{R.LEVEL_LABEL[R.norm_level(cfg.verbosity)]}**. Pick a `level` to change it.\n"
            "-# Brief: countdown, the beginner line and a pro tip. Standard: adds the veteran context, a new-player tip "
            "and a did-you-know. Detailed: adds highlights from the deep dive.", ephemeral=True)
    cfg.verbosity = level.value
    bot.store.upsert_guild(cfg)
    ev(clog, "verbosity_set", guild=cfg.guild_id, detail=level.value, by=interaction.user.id)
    await interaction.response.send_message(
        f"✅ Posts here are now **{R.LEVEL_LABEL[level.value]}**, starting with the next one.\n"
        "-# Everyone can still pick their own level for private replies with `/mysettings`, "
        "and the 📖 More detail button on each post answers at their level.", ephemeral=True)


@bot.tree.command(name="mysettings", description="How much detail you want in the bot's replies to you")
@app_commands.describe(detail="Brief, Standard, Detailed or Plain words (or reset to the server's default)")
@app_commands.choices(detail=LEVEL_CHOICES + [
    app_commands.Choice(name="Plain words: new to WoW, explain everything", value="plain"),
    app_commands.Choice(name="Reset: use the server's default", value="reset")])
async def mysettings_cmd(interaction: discord.Interaction, detail: app_commands.Choice[str] | None = None):
    mine = bot.store.get_user_detail(interaction.user.id)
    c = bot.store.get_guild(interaction.guild_id) if interaction.guild_id else None
    server = R.LEVEL_LABEL[R.norm_level(c.verbosity if c else None)]
    if not detail:
        now_txt = f"**{R.LEVEL_LABEL[mine]}** (your choice)" if mine else f"**{server}** (this server's default)"
        return await interaction.response.send_message(
            f"Your detail level: {now_txt}.\n-# Applies to 📖 More detail, `/classtips`, `/tips`, `/keybinds`, "
            "`/rotation` and quiz results, in every server. Pick `detail` to change it.", ephemeral=True)
    if detail.value == "reset":
        bot.store.set_user_detail(interaction.user.id, None)
        msg = f"Reset. You'll get each server's default (here: **{server}**)."
    else:
        bot.store.set_user_detail(interaction.user.id, detail.value)
        msg = f"✅ You'll get **{R.LEVEL_LABEL[detail.value]}** replies from now on, in every server."
    ev(clog, "mysettings", user=interaction.user.id, detail=detail.value)
    await interaction.response.send_message(msg + "\n-# Channel posts follow the server's setting; tap 📖 More detail "
                                            "on any post to see it at your level.", ephemeral=True)


# ------------------------------------------------------------------ 1.3 Plus One mode
class PlusOneButton(discord.ui.DynamicItem[discord.ui.Button], template=r"po:(?P<what>kit|duo|dying|words|card|plain|plain_off|share)"):
    """Buttons on the /draggedalong hub. Survive restarts."""
    LABELS = {"kit": ("🧭", "Survival kit"), "duo": ("💞", "Pick a class together"), "dying": ("🆘", "I'm dying"),
              "words": ("📖", "What does that mean?"), "card": ("💌", "A card for my partner"),
              "plain": ("🌿", "Plain words on/off"), "plain_off": ("↩️", "Undo"), "share": ("📨", "Post this card here")}

    def __init__(self, what: str):
        self.what = what
        emoji, label = self.LABELS[what]
        style = discord.ButtonStyle.primary if what in ("kit", "dying") else discord.ButtonStyle.secondary
        super().__init__(discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"po:{what}"))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["what"])

    async def callback(self, interaction: discord.Interaction):
        w = self.what
        try:
            if w == "kit":
                await interaction.response.send_message(embed=discord.Embed.from_dict(P.survival_kit_embed()), ephemeral=True)
            elif w == "words":
                await interaction.response.send_message(embed=discord.Embed.from_dict(P.glossary_embed(None)), ephemeral=True)
            elif w == "dying":
                await interaction.response.send_message("🆘 **Okay, deep breath.** What are you playing?", view=PanicClassView(),
                                                        ephemeral=True)
            elif w == "duo":
                await interaction.response.send_message(
                    "💞 **Pick a class together.** Three quick picks, then I'll suggest something that pairs well with your partner.",
                    view=DuoQuizView(interaction.user.id), ephemeral=True)
            elif w == "card":
                v = discord.ui.View(timeout=None)
                v.add_item(PlusOneButton("share"))
                await interaction.response.send_message(
                    "Here's a card for the person who brought you. Tap **Post this card here** to share it in this channel "
                    "(it won't ping anyone).", embed=discord.Embed.from_dict(P.partner_card_embed()), view=v, ephemeral=True)
            elif w == "share":
                e = P.partner_card_embed()
                e["footer"] = {"text": f"Shared by {interaction.user.display_name} · Plus One mode · /draggedalong"}
                await interaction.response.send_message(embed=discord.Embed.from_dict(e),
                                                        allowed_mentions=discord.AllowedMentions.none())
            elif w == "plain":  # toggle: pressing it again turns Plain words off
                if bot.store.get_user_detail(interaction.user.id) == "plain":
                    bot.store.set_user_detail(interaction.user.id, None)
                    await interaction.response.send_message(
                        "↩️ Plain words is off. You're back to this server's normal replies.", ephemeral=True)
                else:
                    bot.store.set_user_detail(interaction.user.id, "plain")
                    v = discord.ui.View(timeout=None)
                    v.add_item(PlusOneButton("plain_off"))
                    await interaction.response.send_message(
                        "🌿 Done. My private replies to you now skip the veteran stuff and explain the jargon as it comes up.\n"
                        "-# Tapped it by accident? Undo below, or use `/mysettings` anytime.", view=v, ephemeral=True)
            elif w == "plain_off":
                bot.store.set_user_detail(interaction.user.id, None)
                await interaction.response.edit_message(
                    content="↩️ Undone. You're back to this server's normal replies.", view=None)
        except discord.HTTPException as e:
            ev(clog, "plusone_failed", logging.WARNING, what=w, error=str(e)[:150])
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went wrong on my end. Try again in a moment.", ephemeral=True)
            return
        ev(clog, "plusone", guild=interaction.guild_id, user=interaction.user.id, what=w)


def plusone_hub_view() -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for w in ("kit", "dying", "duo", "words", "card", "plain"):
        v.add_item(PlusOneButton(w))
    return v


class PanicButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pd:(?P<cls>[A-Za-z]{1,12}):(?P<kind>heal|escape|help)"):
    def __init__(self, cls: str, kind: str):
        self.cls, self.kind = cls, kind
        emoji, label = P.PANIC_KINDS[kind]
        style = {"heal": discord.ButtonStyle.success, "escape": discord.ButtonStyle.primary,
                 "help": discord.ButtonStyle.secondary}[kind]
        super().__init__(discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"pd:{cls}:{kind}"))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["cls"], match["kind"])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=None, embed=discord.Embed.from_dict(P.panic_embed(self.cls, self.kind)),
                                                view=panic_buttons(self.cls))
        ev(clog, "panic", user=interaction.user.id, cls=self.cls, kind=self.kind)


def panic_buttons(cls: str) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for k in P.PANIC_KINDS:
        v.add_item(PanicButton(cls, k))
    return v


class PanicClassView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.select(placeholder="My class is…", options=[discord.SelectOption(label=c, value=c) for c in P.HORDE_CLASSES])
    async def pick(self, interaction: discord.Interaction, select: discord.ui.Select):
        cls = select.values[0]
        await interaction.response.edit_message(
            content=f"🆘 **{cls}.** Tap the one you need. These stay here, so you can come back mid-fight.",
            embed=None, view=panic_buttons(cls))


class DuoQuizView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=900)
        self.user_id, self.partner, self.style, self.comfort = user_id, None, None, None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.select(placeholder="1. What does your partner play?", row=0,
                       options=[discord.SelectOption(label=c, value=c) for c in P.HORDE_CLASSES]
                       + [discord.SelectOption(label="Not sure yet", value="none", emoji="🤷")])
    async def partner_sel(self, interaction, select):
        self.partner = None if select.values[0] == "none" else select.values[0]
        await interaction.response.defer()

    @discord.ui.select(placeholder="2. How do you want to fight?", row=1,
                       options=[discord.SelectOption(label=lbl, value=k, emoji=em) for k, (em, lbl) in P.STYLES.items()])
    async def style_sel(self, interaction, select):
        self.style = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(placeholder="3. How do you feel about dying?", row=2,
                       options=[discord.SelectOption(label=lbl, value=k, emoji=em) for k, (em, lbl) in P.COMFORT.items()])
    async def comfort_sel(self, interaction, select):
        self.comfort = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Pick for us", emoji="💞", style=discord.ButtonStyle.primary, row=3)
    async def go(self, interaction, button):
        if not self.style or not self.comfort:
            return await interaction.response.send_message("Pick an answer for questions 2 and 3 first.", ephemeral=True)
        e = P.duo_embed(self.partner, self.style, self.comfort)
        await interaction.response.edit_message(content=None, embed=discord.Embed.from_dict(e), view=None)
        ev(clog, "duo_quiz", user=interaction.user.id, partner=self.partner, style=self.style, comfort=self.comfort)


@bot.tree.command(name="draggedalong", description="New to WoW because someone you love made you? Start here.")
async def draggedalong_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(P.hub_intro(), embed=discord.Embed.from_dict(P.survival_kit_embed()),
                                            view=plusone_hub_view(), ephemeral=True)
    ev(clog, "draggedalong", guild=interaction.guild_id, user=interaction.user.id)


async def _glossary_ac(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=t, value=t) for t in P.glossary_choices(current)]


@bot.tree.command(name="whatdoesthatmean", description="Explain a WoW word or bit of slang, in plain English")
@app_commands.describe(term="The word you heard (leave empty for the first-week starter list)")
@app_commands.autocomplete(term=_glossary_ac)
async def whatdoesthatmean_cmd(interaction: discord.Interaction, term: str | None = None):
    await interaction.response.send_message(embed=discord.Embed.from_dict(P.glossary_embed(term)), ephemeral=True)
    ev(clog, "glossary", user=interaction.user.id, term=(term or "-")[:30], found=bool(P.lookup(term)[0]) if term else True)


@bot.tree.command(name="pinpost", description="Post a 'start here' card to pin (it keeps itself updated)")
@app_commands.guild_only()
@admin
@app_commands.describe(channel="Where to post it (defaults to your countdown channel)")
async def pinpost_cmd(interaction: discord.Interaction, channel: discord.TextChannel | None = None):
    cfg = bot.store.get_guild(interaction.guild_id)
    if not cfg or not cfg.channel_id:
        return await interaction.response.send_message("Run `/setup` first.", ephemeral=True)
    target = channel or bot.get_channel(cfg.channel_id)
    problem = bot._can_post(target)
    if problem:
        return await interaction.response.send_message(
            f"I can't post there: {problem}.\n{perm_fix_hint(target, problem)}", ephemeral=True)
    old = (cfg.pin_channel_id, cfg.pin_message_id)
    embed = R.pinned_embed(cfg, guild_times(cfg), now_utc(), None, cfg.ping_role_id if C.NOTIFY else None)
    msg = await target.send(embed=discord.Embed.from_dict(embed), view=bot.pin_view(cfg),
                            allowed_mentions=discord.AllowedMentions.none())
    cfg.pin_channel_id, cfg.pin_message_id = target.id, msg.id
    bot.store.upsert_guild(cfg)
    ev(clog, "pinpost", guild=cfg.guild_id, channel=target.id, message=msg.id, replaced=old[1])
    note = ""
    if old[1] and old[1] != msg.id:
        note = "\n-# The old card won't update anymore; you can unpin and delete it."
    perms = target.permissions_for(interaction.guild.me)
    can_pin = perms.manage_messages
    if can_pin:
        try:
            await msg.pin(reason="Forever Sherpa start-here card")
            pinned = "✅ Posted and pinned."
        except discord.HTTPException:
            pinned = "✅ Posted. Pin it: hover the message → **⋯** → **Pin Message**."
    else:
        pinned = "✅ Posted. Pin it: hover the message → **⋯** → **Pin Message**."
    ping_note = ""
    if C.NOTIFY and cfg.ping_role_id and not interaction.guild.me.guild_permissions.manage_roles:
        ping_note = ("\n-# The 🔔 button needs me to have **Manage Roles**, with my role above the ping role. "
                     "Without that, members will see a message telling them to ask an admin.")
    await interaction.response.send_message(
        f"{pinned} It updates itself after every post, so you never need to repost it.{note}{ping_note}",
        ephemeral=True)


@bot.tree.command(name="pickaclass", description="Join the roll call: what class are you playing?")
@app_commands.guild_only()
async def pickaclass_cmd(interaction: discord.Interaction):
    counts = bot.store.class_counts(interaction.guild_id)
    await interaction.response.send_message(f"Roll call: {sum(counts.values())} in so far. Pick yours:",
                                            view=RollcallView(bot, counts), ephemeral=True)


class SpellbookView(discord.ui.View):
    """Dropdown to flip spellbook pages. Ephemeral, so only the person who opened it sees it."""

    def __init__(self, is_admin: bool, page: str):
        super().__init__(timeout=600)
        self.is_admin = is_admin
        pages = R.spellbook_pages(is_admin)
        select = discord.ui.Select(placeholder="Turn the page…", options=[
            discord.SelectOption(label=R.SPELLBOOK[p]["label"], value=p, emoji=R.SPELLBOOK[p]["emoji"],
                                 description=R.SPELLBOOK[p]["blurb"][:100], default=(p == page))
            for p in pages])
        select.callback = self._flip
        self.add_item(select)
        self.select = select

    async def _flip(self, interaction: discord.Interaction):
        page = self.select.values[0]
        for o in self.select.options:
            o.default = o.value == page
        await interaction.response.edit_message(
            embed=discord.Embed.from_dict(R.spellbook_embed(page, bot.cmd_ids, self.is_admin, now_utc())), view=self)


def _is_admin(interaction: discord.Interaction) -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    return bool(interaction.guild_id and perms and perms.manage_guild)


async def _open_spellbook(interaction: discord.Interaction, page: str | None):
    admin_ = _is_admin(interaction)
    page = page or "quest"
    await interaction.response.send_message(
        embed=discord.Embed.from_dict(R.spellbook_embed(page, bot.cmd_ids, admin_, now_utc())),
        view=SpellbookView(admin_, page), ephemeral=True)


_PAGE_CHOICES = [app_commands.Choice(name=v["label"], value=k) for k, v in R.SPELLBOOK.items()]


@bot.tree.command(name="help", description="Open your spellbook: every command, by page")
@app_commands.describe(page="Jump straight to a page")
@app_commands.choices(page=_PAGE_CHOICES)
async def help_cmd(interaction: discord.Interaction, page: app_commands.Choice[str] | None = None):
    await _open_spellbook(interaction, page.value if page else None)


@bot.tree.command(name="spellbook", description="Every command, WoW style (same as /help)")
@app_commands.describe(page="Jump straight to a page")
@app_commands.choices(page=_PAGE_CHOICES)
async def spellbook_cmd(interaction: discord.Interaction, page: app_commands.Choice[str] | None = None):
    await _open_spellbook(interaction, page.value if page else None)


@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    expected = isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure))
    ev(clog, "command_error", logging.WARNING if expected else logging.ERROR,
       exc_info=None if expected else error, name=getattr(interaction.command, "qualified_name", "?"),
       guild=interaction.guild_id, user=interaction.user.id, error=type(error).__name__,
       detail=str(getattr(error, "original", error))[:200])
    msg = "You need Manage Server for that." if isinstance(error, app_commands.MissingPermissions) \
        else "Something went wrong. Try again in a minute."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        ev(log, "startup_failed", logging.CRITICAL, reason="DISCORD_TOKEN is not set")
        raise SystemExit("DISCORD_TOKEN is not set. See .env.example.")
    try:
        bot.run(token, log_handler=None)
    except discord.LoginFailure:
        ev(log, "startup_failed", logging.CRITICAL, reason="Discord rejected the token",
           hint="reset the token in the Developer Portal and update DISCORD_TOKEN")
        raise


if __name__ == "__main__":
    main()
