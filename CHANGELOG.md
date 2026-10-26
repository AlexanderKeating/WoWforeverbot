# Changelog

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
