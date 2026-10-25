# Changelog

## 1.1.0 (in progress, branch `release/1.1`)
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
- Database migrates automatically from 1.0 (adds pinned-message columns).

## 1.0.0 (2026-10-25)
- Daily countdown posts with 🌱/🧙 layers, pro tips and deep dives; configurable 1–4 posts/day.
- News (Wowhead, Warcraft Tavern, MassivelyOP), top Twitch clips, top YouTube video.
- Class roll call, `/tips`, `/tourney`, `/faq`, `/dates`, `/countdown`, `/help` spellbook.
- Launch-night pings; raid countdown after launch.
- Structured logging, `/status` diagnostics, Render deploy.
