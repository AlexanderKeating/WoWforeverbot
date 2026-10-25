"""
Forever Countdown: a multi-server Discord bot. Run: python -m forever_bot.bot

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

from . import content as C
from . import render as R
from .fetchers import Twitch, YouTube, refresh_all
from .store import GuildConfig, Store

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("forever")

POST_GRACE = timedelta(hours=3)        # bot was down at post time? still post within 3h
STAGING_LEAD = timedelta(minutes=60)
SNAP_MAX_AGE = 45 * 60
MILESTONE_WINDOW = timedelta(minutes=15)


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
        super().__init__(discord.ui.Button(label="Deep dive", emoji="🔎", style=discord.ButtonStyle.primary,
                                           custom_id=f"dd:{key}", row=2))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["key"])

    async def callback(self, interaction: discord.Interaction):
        e = R.deep_dive_embed(self.key)
        if not e:
            return await interaction.response.send_message("That deep dive isn't available anymore. Try `/tips`.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed.from_dict(e), ephemeral=True)


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
                if interaction.message and interaction.message.author.id == self.bot.user.id:
                    await interaction.response.edit_message(
                        view=RollcallView(self.bot, counts, _deep_key_from(interaction.message)))
                    await interaction.followup.send(f"Locked in: **{cls}**. Change anytime.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Locked in: **{cls}**.", ephemeral=True)
            except discord.HTTPException as e:
                log.warning("rollcall update failed: %s", e)
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

    async def setup_hook(self):
        self.add_view(RollcallView(self))  # persistent: buttons keep working after restarts
        self.add_dynamic_items(DeepDiveButton)
        cached = self.store.cache_get("_snapshot")[0]
        if cached:
            self.snap = cached
        dev = os.getenv("DEV_GUILD_ID")
        if dev:
            g = discord.Object(id=int(dev))
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        try:
            synced = await self.tree.sync()
            self.cmd_ids = {c.name: c.id for c in synced}  # for clickable </cmd:id> mentions in /help
        except discord.HTTPException as e:
            log.warning("command sync failed: %s", e)
        self.refresh_loop.start()
        self.schedule_loop.start()
        self.launch_loop.start()

    async def on_ready(self):
        log.info("ready as %s in %d servers", self.user, len(self.guilds))

    async def on_guild_remove(self, guild):
        self.store.remove_guild(guild.id)

    # ---------------------------------------------------------- data
    async def refresh(self, force=False):
        async with self._refresh_lock:
            if not force and self.snap and time.time() - self.snap.get("fetched_at", 0) < 60:
                return self.snap
            try:
                self.snap = await asyncio.wait_for(refresh_all(self.store, self.twitch, self.youtube), timeout=120)
                self.store.cache_put("_snapshot", self.snap)
                log.info("refreshed: %s", self.snap["health"])
            except Exception as e:  # noqa: BLE001
                log.exception("refresh failed entirely: %s", e)
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
        await channel.send(content=post.content or None,
                           embeds=[discord.Embed.from_dict(e) for e in post.embeds],
                           view=view,
                           allowed_mentions=mentions)
        if post.followup:
            try:
                await channel.send(post.followup, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException as e:
                log.warning("followup failed in %s: %s", channel.guild.id, e)

    async def post_daily(self, cfg: GuildConfig, now: datetime, force=False, slot: int = 0) -> str:
        if self.snap is None or time.time() - self.snap.get("fetched_at", 0) > SNAP_MAX_AGE:
            await self.refresh(force=True)
        post = self.build(cfg, now, slot)
        if post is None:
            return "Nothing to post: the countdown is finished."
        if not force and self.store.was_posted(cfg.guild_id, "daily", post.key):
            return "Already posted for this time slot."
        channel = self.get_channel(cfg.channel_id)
        problem = self._can_post(channel)
        if problem:
            await self.notify_staging(cfg, f"⚠️ Couldn't post the daily countdown: {problem}.")
            return problem
        await self.send_post(channel, post, cfg.ping_role_id)
        self.store.mark_posted(cfg.guild_id, "daily", post.key)
        self.store.mark_seen(cfg.guild_id, post.used_ids)
        log.info("posted %s to guild %s", post.key, cfg.guild_id)
        return "Posted."

    async def notify_staging(self, cfg: GuildConfig, text: str):
        ch = self.get_channel(cfg.staging_channel_id) if cfg.staging_channel_id else None
        if ch and not self._can_post(ch):
            try:
                await ch.send(text, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass

    @tasks.loop(seconds=60)
    async def schedule_loop(self):
        now = now_utc()
        for cfg in self.store.all_guilds():
            try:
                await self._tick_guild(cfg, now)
            except Exception as e:  # noqa: BLE001 -- one bad server never blocks the rest
                log.exception("guild %s tick failed: %s", cfg.guild_id, e)
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
            if post and not self._can_post(ch):
                extra = f" · then {len(times) - 1} check-in(s) at {fmt_times(times[1:])}" if len(times) > 1 else ""
                await ch.send(f"👀 **Preview** · posts <t:{int(first.timestamp())}:R>{extra} · `/hold` to skip "
                              f"today, `/skipnews` to drop news\n{R.health_text(self.snap)}",
                              allowed_mentions=discord.AllowedMentions.none())
                await self.send_post(ch, post)
            self.store.mark_posted(cfg.guild_id, "staging", today.isoformat())
        if cfg.hold_date == today.isoformat():
            return
        kind, _ = R.phase(cfg.tz, now)
        if kind == "done":
            return
        # each slot: post if due, within grace, and before the next slot starts
        for slot, due in enumerate(dues):
            window_end = min(due + POST_GRACE, dues[slot + 1] if slot + 1 < len(dues) else due + POST_GRACE)
            if due <= local_now < window_end and not self.store.was_posted(
                    cfg.guild_id, "daily", f"{kind}:{today.isoformat()}:{slot}"):
                await self.post_daily(cfg, now, slot=slot)

    @tasks.loop(seconds=30)
    async def launch_loop(self):
        now = now_utc()
        for minutes, _ in R.MILESTONES:
            at = C.LAUNCH - timedelta(minutes=minutes)
            if not (at <= now < at + MILESTONE_WINDOW):
                continue
            for cfg in self.store.all_guilds():
                if self.store.was_posted(cfg.guild_id, "milestone", str(minutes)):
                    continue
                ch = self.get_channel(cfg.channel_id)
                if self._can_post(ch):
                    continue
                try:
                    text = R.milestone_text(minutes, cfg.faction)
                    ping = f"<@&{cfg.ping_role_id}> " if cfg.ping_role_id else ""
                    await ch.send(ping + text + f"\n<t:{int(C.LAUNCH.timestamp())}:R>",
                                  allowed_mentions=discord.AllowedMentions(
                                      roles=[discord.Object(cfg.ping_role_id)]) if cfg.ping_role_id else discord.AllowedMentions.none())
                    self.store.mark_posted(cfg.guild_id, "milestone", str(minutes))
                except discord.HTTPException as e:
                    log.warning("milestone %s guild %s: %s", minutes, cfg.guild_id, e)
                await asyncio.sleep(0.5)

    @refresh_loop.before_loop
    @schedule_loop.before_loop
    @launch_loop.before_loop
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
        return await interaction.response.send_message(f"I can't post in {channel.mention}: {problem}.", ephemeral=True)
    if staging and bot._can_post(staging):
        return await interaction.response.send_message(f"I can't post in {staging.mention}: {bot._can_post(staging)}.", ephemeral=True)
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
    setup = (f"Channel <#{cfg.channel_id}> · {len(guild_times(cfg))}x a day at {fmt_times(guild_times(cfg))} {cfg.tz} · {cfg.faction}"
             f"{' · ON HOLD today' if cfg.hold_date == R.local_today(cfg.tz, now_utc()).isoformat() else ''}"
             if cfg and cfg.channel_id else "Not set up. Run `/setup`.")
    await interaction.response.send_message(f"{setup}\n{R.health_text(bot.snap)}", ephemeral=True,
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
        embed=discord.Embed.from_dict(R.tips_embed(topic.value if topic else "basics")), ephemeral=True)


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
    log.exception("command error: %s", error)
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
        raise SystemExit("DISCORD_TOKEN is not set. See .env.example.")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
