# Changelog

## 1.1.2
- 🧙 veteran lines and 🔎 deep dives rewritten with fuller context: why each change matters, not just what changed.

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
