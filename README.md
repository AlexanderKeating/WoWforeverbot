# Forever Countdown

A Discord bot that counts down to **World of Warcraft: Forever** (Nov 4, 2026, 3 PM PST) and then to raid
opening (Dec 9). One daily post per server, written for both brand-new players (🌱) and veterans (🧙), with
the latest Forever headlines, top Twitch clips, a class roll call, and launch-night pings.

Works in any number of servers. Each server picks its own channel, ping role, post time, time zone and faction.

---

## What it posts

- **1 to 4 posts a day**, set per server with `/frequency` (default once, 12:00 PM America/Chicago).
  The first post each day is the full rundown below; later ones are short **check-ins** with a new tip, a
  did-you-know, a deep dive button, and only news and clips that haven't been posted yet. Check-ins don't ping.
- **Full daily post**
  - Countdown with a live, auto-localized timestamp
  - "Next up" key date, and day-of callouts (name reservation, launch)
  - Today's rundown in four layers: 🌱 plain English · 🧙 vet detail · ⚔️ pro tip ·
    🔎 **Deep dive** button (5–6 detailed bullets, shown privately so the channel stays clean)
  - Day 10: the Forever Open tournament recap with the class win-rate table
  - New-player tip and a did-you-know
  - **📰 Since yesterday:** up to 3 Forever headlines, title + link only, never reworded
  - **📺 Top video:** the most-viewed Forever video of the last 24h on YouTube (Shorts skipped), with the
    creator's own title and the start of their description
  - **🎬 Top clips:** up to 2 Twitch clips from the last 24h, title exactly as the streamer wrote it, as a
    separate message so Discord shows playable previews
  - Roll call buttons for all 9 classes, with live counts
- **Launch night:** pings at T-60 min, T-10 min, and go time
- **After launch:** keeps posting a raid countdown through Dec 9, rotating leveling, professions, travel, gold
  and PvP topics with their own pro tips and deep dives, then stops

## Commands

| Who | Command | Does |
|---|---|---|
| Admins | `/setup` | Channel, ping role, staging channel, post time, time zone, faction |
| Admins | `/frequency` | 1–4 posts a day from presets, or exact times like `12pm, 7pm` (2h apart min) |
| Admins | `/preview` | Privately shows today's post and data-source health |
| Admins | `/postnow` | Posts today's full post now, or the current check-in if the full post is already up |
| Admins | `/hold` · `/resume` | Skip or un-skip all of today's posts |
| Admins | `/skipnews` | Post today without the news section |
| Admins | `/status` | Settings and source health |
| Everyone | `/help` or `/spellbook` | A WoW-style spellbook of every command: flip pages with a dropdown, tap a command to use it. New players get a "Quest log" page; the Officer page only shows for admins |
| Everyone | `/classtips class:<name> [share]` | Forever changes, leveling and Horde PvP tips, key talents and beta-tournament record for any class (private unless `share:true`) |
| Admins | `/pinpost [channel]` | Posts a "start here" card to pin; it updates itself after every post. Includes a 🔔 ping opt-in button |
| Everyone | `/keybinds [class] [topic]` · `/macros class` · `/rotation class` | Keybind basics + class starter layouts + controller setup; copy-paste macros; leveling priorities per spec |
| Everyone | `/whichclass` | 5-question quiz that suggests a class |
| Everyone | `/tips [topic]` | Tips by topic: basics, leveling, pvp, camping, professions, travel (private) |
| Everyone | `/countdown` `/tourney` `/faq` `/dates` `/pickaclass` | |

"Admins" means anyone with **Manage Server**. Server owners can change this under Server Settings → Integrations.

## How it stays reliable without anyone watching

- News, clips and videos are fetched **once every 30 minutes** and shared by every server.
- Each source is isolated: its own timeout, 3 retries with backoff, and rate-limit handling.
- Each news site has backup feed URLs, then **auto-discovers** the site's RSS link if those move.
- Twitch: tries several category names, then searches categories, then falls back to the main WoW
  category with title matching. Unknown or renamed streamer logins are skipped and logged.
- Forever matching tolerates "WoW: Forever", "World of Warcraft Forever", "#WoWForever", "Classic+",
  zone and race names, and bare "Forever" next to a WoW word.
- If a source fails, it reuses its last good result for up to 36 hours, then quietly drops that section.
- Every headline and clip is remembered per server, so nothing repeats.
- Posts are deduped in SQLite, so restarts never double-post. If the bot is down at post time, it still
  posts if it comes back within 3 hours.
- Optional **staging channel** gets a preview plus source health an hour before each post.
- Clip titles with slurs or heavy profanity are skipped. All third-party titles are markdown-escaped.

---

## Setup (about 20 minutes)

### 1. Create the Discord bot
1. Go to <https://discord.com/developers/applications> → **New Application** → name it.
2. **Bot** tab → **Reset Token** → copy it. This is `DISCORD_TOKEN`. Keep it secret.
3. Same tab: leave **Public Bot** ON so other servers can add it with your link. No privileged intents needed.
4. **Installation** tab → Install Link: *Discord Provided Link*. Guild Install scopes: `bot`, `applications.commands`.
   Permissions: **View Channels, Send Messages, Embed Links**.
5. Your invite link (replace `APP_ID` with the Application ID from General Information):
   ```
   https://discord.com/oauth2/authorize?client_id=APP_ID&scope=bot+applications.commands&permissions=19456
   ```
   This is the link you share. It isn't listed anywhere unless you post it.

   **Optional extras:** to let the bot pin its start-here card and run the 🔔 ping opt-in button, use this link
   instead (adds **Manage Messages** and **Manage Roles**). After adding, drag the bot's role *above* your ping
   role in Server Settings → Roles:
   ```
   https://discord.com/oauth2/authorize?client_id=APP_ID&scope=bot+applications.commands&permissions=268463104
   ```

### 2. Twitch keys (for clips)
1. <https://dev.twitch.tv/console> → **Register Your Application**.
2. OAuth Redirect URL: `http://localhost` · Category: anything · Client Type: **Confidential**.
3. Copy the **Client ID** and generate a **Client Secret**.

### 2b. YouTube key (for top videos)
1. <https://console.cloud.google.com> → project dropdown (top left) → **New Project** → name it → Create.
2. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
3. **APIs & Services → Credentials** → **Create credentials → API key**. Copy it.
4. Click the key → **API restrictions → Restrict key → YouTube Data API v3** → Save.
   No billing needed; the free 10,000 units/day covers this (the bot uses about 1,250).

### 3. Deploy on Render (~$7.25/mo)
1. <https://render.com> → sign up with GitHub → add a payment method (workers have no free tier).
2. **New → Blueprint** → connect **WoWforeverbot**. Render reads `render.yaml` and creates a background
   worker with a 1 GB disk at `/data`.
3. Fill in the secrets it asks for: `DISCORD_TOKEN` (required), Twitch and YouTube keys (optional; leave
   blank and add later under the service's **Environment** tab).
4. **Apply**. Open the service → **Logs** and wait for `ready as …`.

Every push to `main` redeploys automatically.

### 3 (alternative). Deploy on Railway (~$5/mo Hobby plan)
1. Put this folder in a GitHub repo (private is fine).
2. <https://railway.com> → **New Project** → **Deploy from GitHub repo** → pick it. It builds from the Dockerfile.
3. Service → **Variables**: add `DISCORD_TOKEN`, `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `YOUTUBE_API_KEY`,
   `DB_PATH=/data/forever.db`.
4. Service → right-click → **Attach Volume** → mount path `/data`. This keeps roll call and post history
   across deploys.
5. Deploy. Logs should show `ready as ForeverCountdown#…`.

### 4. In each Discord server
1. Open the invite link and add the bot.
2. Create a role like `@Forever Hype` and enable **Allow anyone to @mention this role** (or the ping won't fire).
3. Run `/setup channel:#forever-countdown ping_role:@Forever Hype staging:#bot-staging`
   (posts once a day at 12:00 Central by default; add `post_time:12pm, 7pm` and `timezone:` to change it,
   or use `/frequency` any time later).
4. `/preview` to check, then `/postnow` if you want today's post right away.

Slash commands can take up to an hour to appear the first time. To test instantly in your own server,
set `DEV_GUILD_ID` to your server's ID.

---

## Debugging

Every log line is one event with `key=value` fields. In Render → **Logs**, search for:

| Search | Shows |
|---|---|
| `event=post_sent` | Every post: server, slot, size, news/clip/video counts, message id |
| `event=refresh_done` | Each data refresh: sources ok/down/stale, item counts, duration |
| `event=source_down` / `event=source_stale` | A news site, Twitch or YouTube failing, and whether cache covered it |
| `event=feed_ok` | Which feed URL worked per site, entries vs kept vs off-topic |
| `event=twitch_clips` / `event=youtube_search` | Raw vs kept counts and why items were dropped |
| `event=slot_late` / `event=slot_missed` | Posts that went out late or not at all (bot was offline) |
| `event=post_blocked` | Missing channel permissions |
| `event=command` / `event=command_error` | Who ran what, and failures with tracebacks |
| `event=heartbeat` | Every 30 min: uptime, servers, latency, next post, loops healthy |
| `level=ERROR` | Anything that needs attention |
| `guild=<server id>` | Everything for one server |

Settings: `LOG_LEVEL=DEBUG` adds every HTTP request with status and timing; `LOG_FORMAT=json` emits JSON lines
for log tools. Tokens and API keys are scrubbed from every line.

In Discord, `/status` shows the schedule, next post, recent posts, permission problems, source health and the
running version.

## Editing what it says

Everything is in `forever_bot/content.py`: daily rundowns, pro tips, deep dives, tips by topic, did-you-knows, tournament data, FAQ,
key dates, news sources, pinned streamers, and the clip-title blocklist. Push the change and Railway redeploys.

Preview any day offline before pushing:
```
pip install -r requirements.txt
python -m forever_bot.preview --date 2026-10-25
python -m forever_bot.preview --all          # every day through Dec 9
python -m forever_bot.preview --live         # real news and clips (set Twitch keys first)
python tests/test_bot.py                     # offline tests
```

## Sharing it widely

Hosting cost barely changes with more servers because data is fetched once. Discord requires a free
verification (identity check plus a short form) once the bot reaches **100 servers**; new servers can't add it
until that's done.

## Accuracy notes

Facts come from Blizzard's announcements and coverage as of Oct 24, 2026. Forever is not retail or Classic:
there are no realms (one world per ruleset per region), the PvP ruleset locks an account to one faction,
and PvP ranks are a personal weekly-capped track, not the old ladder. Tournament numbers are level-30 beta
duels, labeled as such in every post. Update `content.py` if Blizzard changes something.
