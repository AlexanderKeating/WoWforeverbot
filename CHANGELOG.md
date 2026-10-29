# Changelog

## 1.8.0 (2026-10-29)
Let servers trim the post. On Oct 28 two servers left within 20 minutes of seeing their first post.
- **New `/clips [on]`** (admins): turn the Twitch clips under each post off or back on. On by default. Applies to full posts, check-ins, `/preview` and `/postnow`. `/status` shows "clips off" when it's off.
- **Welcome card lists the settings that matter.** New servers now see a short "Make it fit your server" list: `/preview`, `/verbosity`, `/clips`, `/frequency`, `/hold` and `/skipnews`, `/statusalerts`.
- New log event: `clips_set`.

## 1.7.1 (2026-10-28)
Gentler first day. On Oct 28 two servers set up after noon and got the noon full post backdated (37 and 146 minutes late, about 2,000 characters plus clips); one left 11 minutes later.
- **No stale catch-up after setup.** Setting up (📍 Post here or a first `/setup`) after today's post time skips the slots that already passed instead of sending them late.
- **Short first look instead.** The channel gets a check-in-sized post right away (countdown, a tip, a class spotlight, a did-you-know; no news or clips) that says when the full daily post starts. Skipped if the next scheduled post is within an hour.
- The late-post warning now says "bot restarted or was down at post time".
- New log events: `setup_skipped_slots`, `first_post_skipped`, `first_post_blocked`, `first_post_failed`; the first look logs as `post_sent type=first`.

## 1.7.0 (2026-10-28)
Make setup obvious. On Oct 28 a new server tried seven commands in 22 minutes, never found `/setup`, and left.
- **Welcome card on join.** The bot posts a short hello in the server's system channel (or the first channel it can post in) with a **📍 Post here** button. One click by someone with Manage Server sets up the daily post in that channel at the default time (noon Central). The button disappears once it's used.
- **Setup reminder.** In a server that isn't set up yet, using a member command adds a private one-liner: admins get the **📍 Post here** button, everyone else is told to ask an admin. At most once every 6 hours per person. Commands-only installs get the invite link instead.
- **`/setup` channel is optional.** Leave it empty to use the channel you're in.
- **`/help` says "⭐ Start here"** at the top of every page until the server is set up, with the **📍 Post here** button for admins.
- New log events: `welcome_sent`, `welcome_no_channel`, `welcome_failed`, `quick_setup`, `setup_nudge`.

## 1.6.1 (2026-10-27)
- **Clips:** never two from the same streamer in one post (Forever clips included), near-duplicate titles are dropped, and clips under 20 views are skipped.
- **Did you know:** 15 new lore and dungeon facts (Varian in Alcaz Prison, Dalaran's dome, Hyjal's old exploits, the Southshore vs Tarren Mill rivalry...). Retired 4 that just repeated tips.
- **No repeats inside a post:** a fact about something the post already covers (same place, or the day's topic) is skipped; a pro tip that repeats the day's 🧙 paragraph is swapped for an on-topic line from that day's deep dive; check-in facts avoid the tip and class spotlight.
- Horde-only Skyborne mount vendor tip is labeled on neutral servers; "Pvp tip" reads "PvP tip".

## 1.6.0 (2026-10-27)
- **WoW: Forever status alerts.** Every 5 minutes the bot reads Blizzard Support's official Bluesky feed and keeps posts about Forever (or Battle.net-wide outages). Problems, maintenance and the follow-up "fixed" posts go to each server's countdown channel; "all good" posts never do. No pings.
- Starts in **watch-only mode** (`STATUS_POST_TO_CHANNELS = False`): it logs `event=status_would_post` so the matching can be checked on real posts first.
- New `/statusalerts [on]` (admins) to turn alerts off or on per server. On by default.

## 1.5.2 (2026-10-27) · hotfix
- Servers that added only Forever Sherpa's commands (not the bot) now get a clear message with the full invite link when they run `/setup`, `/preview`, `/postnow`, `/frequency`, `/verbosity` or `/pinpost`, instead of an error. Two servers hit this on day one.

## 1.5.1 (2026-10-27) · hotfix
- `/setup` (and `/pinpost`) on a channel the bot can't see, usually a private one, now explains how to add Forever Sherpa to that channel instead of "Something went wrong." Two new servers hit this on day one.

## 1.5.0 (2026-10-27)
More depth, from Blizzard's PvP and Legacy posts plus Warcraft Tavern's profession, Legacy and camping guides.
- 40 new tips: leveling +4, PvP +6, camping +5, professions +6, travel +2, and new **gold** (5) and **legacy** (7) topics in `/tips`.
- Two new post-launch topics with deep dives: **The Legacy System** and **Camping 101**. The rotation now covers 7 topics between launch and raids.
- Post-launch posts now include a highlight from the day's deep dive (1 at Standard, 2 at Detailed).
- 9 new did-you-knows (Legacy, PvP ranks, recipes, camping, Shaman PvP sets).
- Fixed: daily rotation got stuck on one item when a list had exactly 7 (or 14, 21...) entries.
- New `/dungeons`: Forever's nine new dungeons with level ranges, locations and how to get in (Blizzard's preview).
- New `/addons`: starter picks that work on Forever, install steps, and what to skip (WeakAuras, Classic versions, combat-log addons).
- Alliance support on class cards: Alliance race lists (Dwarf Shaman, Human Hunter, Gnome Priest, Alliance Skyborne Mage are new) and Alliance racial PvP tips. Neutral servers see both race lists.
- Fixed: Plus One quiz called Shaman "Horde-only"; Dwarves can be Shamans on Alliance in Forever.
## 1.4.3 (2026-10-27) · hotfix
- New `/rollcall`: who's playing what in this server, grouped by class (names shown, nobody pinged). Private by default; `share:True` posts it in the channel.

## 1.4.2 (2026-10-27)
- Faction-neutral by default. Posts, More detail, `/tips` and `/faq` no longer assume Horde unless the server picks Horde in `/setup`. Labeled Horde-only facts (racials, Horde Skyborne, vendors) stay as-is.
- Existing servers that never chose a faction (they got the old Horde default) were reset to neutral once. `/setup faction:Horde` brings Horde wording back.
- Fixed: the name-reservation deep dive said the bot "pings"; it posts a heads-up, no pings.

## 1.4.1 (2026-10-27)
- Terms and Privacy pages moved to https://foreversherpa.github.io (their own repo, ForeverSherpa/foreversherpa.github.io). Bot links updated; `/docs` removed from this repo.

## 1.4.0 (2026-10-27)
App Directory prep.
- Terms of Service and Privacy Policy pages in `/docs`, served by GitHub Pages: /terms.html, /privacy.html, plus a small landing page with the invite link.
- `/mydata`: shows everything stored about you. `/forgetme`: deletes your detail setting and roll-call picks in every server (with a confirm button).
- Removing the bot from a server now deletes that server's settings, roll call, post history and seen-news records (before: only switched off).
- Help spellbook links the Terms and Privacy pages.

## 1.3.3 (2026-10-27)
- Name reservation alerts are back as plain channel posts (no @role pings): 30 minutes before (2:30 PM Central), when it opens (3 PM Central, Oct 27), and on the last day (Nov 3, 10 AM Central). Each posts once per server.
- New `EVENT_POSTS` flag in content.py controls them separately from `NOTIFY`.

## 1.3.2 (2026-10-26)
- Logging: every button press and dropdown pick now logs `event=click` with the control (e.g. `panic:Hunter:heal`, `more_detail:professions`, spellbook page picks), what was picked, and who.
- `event=command` lines now include the person's display name (`who=`) and the options they used (`args=page:plusone`).

## 1.3.1 (2026-10-26)
- 🌿 Plain words button on `/draggedalong` is now a toggle (press again to turn it off), and its confirmation has an ↩️ Undo button.

## 1.3.0 (2026-10-26)
**Plus One mode**, for people whose partner, friend or roommate talked them into WoW.
- `/draggedalong`: a private hub with the night-one survival kit and six buttons:
  - 🧭 Survival kit: moving, quests, five keys, dying, grouping up, world PvP, eating between fights
  - 🆘 I'm dying: pick your class, get three panic buttons (Heal me / Get me out / Get help) that stay put mid-fight
  - 💞 Pick a class together: three questions, a class that pairs with your partner's, and a runner-up
  - 📖 What does that mean?: the first-week starter list
  - 💌 A card for my partner: tips for the person who brought you, postable in the channel (no pings)
  - 🌿 Plain words everywhere: switches your replies to the new level
- `/whatdoesthatmean [term]`: 65+ WoW words and slang with autocomplete, from aggro to zug zug.
- New personal level in `/mysettings`: **Plain words**. Private replies drop the veteran sections and explain jargon the first time it appears.
- Help spellbook has a 💞 Plus One page; the pinned card points newcomers to `/draggedalong`.

**Clips:** until Twitch has a Forever category, posts also show up to 2 WoW clips from the streamers we follow (one each), labeled "not necessarily Forever". Turn off with `CLIPS_LOOSE_UNTIL_CATEGORY` in content.py.

## 1.2.2 (2026-10-26)
- Class cards: every leveling and PvP tip is now "**do this** → benefit". Beta tournament records stay as plain facts.
- New-player tips rewritten the same way. Dropped the ones a Horde PvP player already knows (eat between fights, what a dungeon group is, world PvP exists).
- Renamed the leftover "Forever Countdown" text to Forever Sherpa (audit-log reasons, pin reason, web user agent, README).

## 1.2.1 (2026-10-26)
- Fixed: the 📖 More detail button showed "application didn't respond in time". A log line crashed before the reply was sent.
- Fixed: `/verbosity` saved your choice but never confirmed it (same cause).
- Logging can no longer break a reply, and there's a regression test for the button.

## 1.2.0
- **Detail levels: Brief, Standard, Detailed.**
  - `/verbosity` (admins): how detailed this server's channel posts are.
    Brief = countdown, 🌱 line, pro tip. Standard = adds 🧙 context, new-player tip, did-you-know.
    Detailed = adds deep-dive highlights.
  - `/mysettings` (everyone): your own level for everything the bot sends you privately, in every server.
    Unset = follows the server's level.
  - **📖 More detail** button (replaces 🔎 Deep dive) answers at the reader's level: Brief gets the essentials,
    Standard adds the veteran context, Detailed adds the pro tip and every point.
  - Class tips, keybinds, rotations, `/tips` and quiz results all scale with your level
    (e.g. Detailed class cards add "bind these first" and a starter rotation).
- Database migrates automatically (adds server verbosity and a per-user settings table).

## 1.1.2
- **Notifications off** (`NOTIFY = False` in `content.py`): no @role pings on any post, no standalone
  name-reservation or launch-countdown posts, and no 🔔 button on the pinned card. Daily posts still go out on schedule.
- 🧙 veteran lines rewritten with fuller context: why each change matters, not just what changed.
- ⚔️ pro tips and 🔎 deep dives now use "**do this** → what you get" so every point is actionable.

## 1.1.1
- YouTube videos removed from posts (and no longer fetched). Twitch clips and news stay.
  Flip `SHOW_YOUTUBE` in `content.py` to bring them back.

## 1.1.0 (2026-10-25)
- **Class tips for all nine classes** (`/classtips class:<name>`): what's new in Forever, leveling tips,
  Horde PvP tips, talents worth knowing, and each class's beta-tournament record. Private by default;
  `share:true` posts it for everyone.
- **Roll call → tips:** picking a class on the daily post (or `/pickaclass`) now replies with that class's tips.
- **Class spotlight** in every check-in post, rotating through all classes.
- **`/pinpost`:** posts a "start here" card (countdown, schedule, how to start, key dates, commands) that
  **updates itself after every post** with a link to the latest one. Pins itself if the bot can manage messages.
- **🔔 Toggle pings** button on the card lets members opt in/out of the ping role (needs Manage Roles).
- Spellbook (`/help`) updated: Quest log is now 4 steps, new commands listed; a test fails if any command
  is missing from it.
- **`/keybinds`**: keyboard basics, what each class should bind first plus a starter layout to copy,
  and controller (Gamepad UI) setup.
- **`/macros`**: 2–3 copy-paste macros per class (mouseover heals, interrupts, Cat/Dash…). Macros using
  syntax not yet confirmed for Forever are marked ⚠️ test in-game.
- **`/rotation`**: simple leveling priorities for every spec, using Forever's versions of each class.
- **`/whichclass`**: 5-question quiz that suggests a class (every class can come up), with tip buttons.
- **Class card buttons:** every class card links to that class's tips, keybinds, macros and rotation.
- **Name reservation pings:** 30 minutes before and when it opens (Oct 27, 1 PM Pacific), and on the last day (Nov 3).
- Quest log in `/help` is now 6 steps; pinned card points new players to the quiz and keybinds.
- Database migrates automatically from 1.0 (adds pinned-message columns).

## 1.0.0 (2026-10-25)
- Daily countdown posts with 🌱/🧙 layers, pro tips and deep dives; configurable 1–4 posts/day.
- News (Wowhead, Warcraft Tavern, MassivelyOP), top Twitch clips, top YouTube video.
- Class roll call, `/tips`, `/tourney`, `/faq`, `/dates`, `/countdown`, `/help` spellbook.
- Launch-night pings; raid countdown after launch.
- Structured logging, `/status` diagnostics, Render deploy.
