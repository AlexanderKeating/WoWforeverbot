# Changelog

## 1.12.5 (2026-11-10)
Rolling facts check against Blizzard's Nov 9 hotfixes and the Nov 10 PvP faction balance post.
- **Faction balance (Blizzard, Nov 10, us.forums.blizzard.com/en/wow/t/2408781).** Character creation now reacts to each region's overall PvP split instead of point-in-time counts, and it will get increasingly hard to make Horde on NA PvP. Rulesets deep dive tip was "try again later, Blizzard recalculates through the day" → now "plan for it to stay hard for a while". New did-you-know: ~55/45 split in the most lopsided region, goal 50/50. `test_new_facts_present` guards the new wording.
- **Nov 9 hotfixes (us.forums.blizzard.com/en/wow/t/2403040, post #5).** New PvP tip: Nifty Stopwatch no longer shares a cooldown with Sprint, Dash or Blink. New Warlock tip: finished "Summon Felsteed" before the fix → summon it once for the riding skill (expires Dec 9). New did-you-know: player cap lowered in congested zones, more on PvP.
- **Enhancement (Blizzard, "Class Tuning Incoming - November 10", t/2404092).** New Shaman leveling tip: collect Strength and Attack Power gear; Blizzard is making Strength Enhancement's best stat. The Nov 10 tuning has no numbers yet; the existing "Tuesday tuning" line stays (expires Nov 16).
- **Raid countdown check.** Dec 9 for all three raids still matches every source; Blizzard still hasn't given an unlock hour. The Dec 9 callout said "Raids are open" in the noon post and the evening check-in title said "Raids are open", which may be before unlock: now "Raid day … all open today" and "Raid day". Countdown titles on Dec 7–10 checked with the preview (2 days, 1 day, Raids open today, Day 37 + Next up: Hardcore). New test guards it.
- **Re-verified** 13 of the 15 oldest Druid and Hunter class-card lines against Blizzard's Hunter and Druid class deep dive (news.blizzard.com 24301515). Not verified: the Tauren War Stomp 90-second cooldown and the Druid tournament record; no source found today, left for the next run.

## 1.12.4 (2026-11-09)
Rolling facts check, and the Nov 8 refusal loop. 6 new tests.
- **Discord refusals (20062) aren't retried every minute.** Nov 8: one server's noon post got 403/20062 every minute for the 3-hour window (180 ERRORs with tracebacks), then `slot_missed` said the bot was offline. Now the first refusal marks the slot `refused`, logs `post_refused` once (ERROR once a week per channel, INFO after, no traceback), tells staging once, and `slot_missed` says `reason=refused`. `/postnow` still tries. The same day a setup reminder got 20062 *without* the button, so 1.12.3's button theory doesn't cover it; the fallback stays, the docstring says so. `postnow_outcome` reports `refused`.
- **Facts ledger.** `forever_bot/facts_ledger.json`: one entry per tip, fact, deep-dive line, pro tip and class-card line (468), with source, `added`, `verified` and optional `expires`. `tools/facts.py` keeps it in step (`sync`, `due`, `dupes`, `verified`, `record`, `expiring`, `check`); `test_ledger_matches_pools` fails if a line is added or removed without it.
- **Fresh first, no repeats.** `pick()` gives each line added in the last 14 days one day up front (lines from the same batch go one a day, the day after they're added), only for the main post's picks so the evening check-in doesn't repeat it. Lines past `expires` drop out of rotation by themselves.
- **🔧 Hotfix line.** Hotfix, tuning, patch-note and known-issues headlines sort to the top of the news embed with a 🔧.
- **Facts (checked against Blizzard's Nov 5, Nov 6 and Nov 8 posts).** Dungeon kill XP +50% (Nov 8): leveling deep dive, dungeon pro tip, a new leveling tip. PvP faction lock happened on launch night: ruleset deep dive and tip now say so (was "may"). Voidwalker +~40 base health on the Warlock card. New tips: Tanning Rack at 125 (was 140), Tauren Plainsrunning no longer stacks in BG prep and drops when carrying a flag, level-40 gold for mount + dual spec. New did-you-knows: Taldramir (plus a ⛏️ datamined line on its questline), dual spec at 40, the dungeon XP change, Tuesday class tuning (expires Nov 16). Pre-launch raid lines now include Onyxia's Lair.

## 1.12.3 (2026-11-06)
From the Nov 3–6 live logs (82 servers). 3 new tests; `test_status_watcher` no longer depends on the date.
- **Blocked retries aren't "late".** "Forever and ever.", EREBOR and Salt Raptors have channels the bot can't post in. The scheduler retries each minute, and at 5 minutes it logged `slot_late` "bot restarted or was down at post time" every day, though the bot was up. `slot_late` now skips slots already marked `blocked`; `post_blocked` and `slot_missed reason=blocked` still report them.
- **Welcome / setup reminder fallback.** Nov 6 Eternal Wardens: Discord refused the message with the 📍 Post here button (403, code 20062 "requires an application to be authorized by the user"), so neither the welcome nor the reminder landed. New `send_with_setup_button()` resends the same embed without the button on 20062 (`setup_button_refused`, INFO); the embed already says to run `/setup`. Other errors still fail as before. `welcome_sent` and `setup_reminder_sent` log `button=`.
- **Health count.** `refresh_done` no longer counts sources that are switched off or not configured (YouTube, off since 1.1.1), so a healthy run reads `ok=4 total=4` instead of `ok=4 total=5`. New `off=` field lists them. The `/status`-style health line in posts already left them out.
- **Test fix.** `test_status_watcher`'s fake Bluesky post was dated Nov 4 while `status.check()` uses the real clock; from Nov 5 it was outside the 2-hour first-run window and the test failed. The post is now dated from the current time.

## 1.12.2 (2026-11-03)
Hardening from a week of live error/warning logs (Oct 28 – Nov 3). 18 new tests; the two tests that were already failing on main are fixed.
- **Roll call (Nov 2, Runedone).** A Warrior click arrived after Discord's 3-second window (10062 "Unknown interaction"); the board edit failed, then the "Saved as" fallback failed the same way and dumped a traceback. Now the pick is saved first, Discord is answered (board edit, or `defer` off-board) before the class tips card is built, and an expired interaction gets no second reply (`rollcall_late`, WARNING, `saved=True`). Storage errors reply "Couldn't save that" instead of throwing; a broken tips card can't undo a saved pick.
- **Server removed mid-pass (Nov 3, WoWffles).** A schedule pass over ~50 servers takes ~25s. WoWffles removed the bot mid-pass; its config and "posted" marks were deleted, but the pass still held the old config and logged a false `slot_missed reason=offline`. New `live_cfg()` re-reads each server right before ticking it (also picks up `/frequency` changes made mid-pass), and skips servers the bot can't see (`tick_skipped`, once). Used by the daily scheduler, launch-night posts, event posts and status alerts. `on_ready` logs `stale_configs` for servers that removed the bot while it was offline (data kept).
- **Schedule changes.** `/frequency` and re-running `/setup` now call `skip_passed_slots(..., before=old_cfg)`: only slots whose time or time zone changed and are already in the past are skipped, so the reply ("passed slots wait for tomorrow") is true, with no late backfill and no false `slot_missed`. Unchanged slots that are due right now still post.
- **Missed slots are reported once.** The dedupe was in memory, so The NeverEnding Story's Nov 1 noon slot was logged three times across deploys. Now stored as a `missed` mark.
- **Blocked channels log less.** "Forever and ever." has been blocked since Nov 1 and logged an ERROR for every slot and event, every day. New `blocked_level()`: ERROR the first time per channel per week (the week admins get the notice), INFO after (`repeat=true`). Applies to `post_blocked`, `event_blocked`, `milestone_blocked`.
- **Exceptions.** All buttons and dropdowns (views and dynamic items) share one `on_error`: one `component_error` line, a private "try again", and nothing at all for expired interactions (`component_late`). `on_app_error` returns quietly for expired interactions (`command_late`). `on_command_error` ignores `CommandNotFound` (Nov 1 "Ignoring exception in command None" was someone @mentioning the bot). New `on_error` for gateway events. A log filter turns discord.py's own 10062/40060 tracebacks (Oct 30 "Ignoring exception in autocomplete for 'setup'") into one WARNING line; real bugs keep their traceback. `/whatdoesthatmean` autocomplete can't throw.
- **Loops.** Launch-night and event posts isolate each server (`milestone_crashed`, `event_crashed`) so one bad server can't stop the rest. The status check survives a source timing out (Bluesky, Nov 2) with a 60s session timeout and `status_check_failed`. The heartbeat, which restarts the other loops, can no longer crash itself (`heartbeat_crashed`).
- **Tests already failing on main.** `test_release_notes_and_update_line` checks the newest release that has a line, not 1.11.0's `/datamined` wording. `test_content_corrections` allows "Lava Burst was cut…" while still blocking Lava Burst listed as an ability, keybind or rotation step. The 1.11.0 release note no longer says Ice Lance does 200% more.

## 1.12.1 (2026-11-03)
Facts check against Blizzard's WoW Forever development notes (updated Nov 2, launch tuning).
- **Shaman:** Lava Burst removed, Call of Thunder (+5% Lightning Bolt / Chain Lightning crit) in its slot; Elemental Mastery renamed Lightning Mastery; Totemic Projection renamed Totemic Call (pulls totems to you, 30s cooldown); Riptide 12s cooldown, HoT only; Stormstrike 6s cooldown. Class card, talents, `/keybinds` layout (4 = Lightning Shield, C = Totemic Call), Elemental and Enhancement rotations, one fact.
- **Mage:** Ice Lance back to 300% vs Frozen, 8s cooldown shared with Fire Blast (class card, rotation). Ice Lance / Frost Blast fact is now Blizzard-confirmed, no longer datamined.
- **Hunter:** all traps share one 30s cooldown (was "Frost and Fire separate").
- **Paladin:** Salvation and Mass Salvation removed. Righteous Fury at 10 is now Blizzard-confirmed, no longer datamined.
- **Priest:** Holy Binding replaces Binding Heal (talents); Shadow Word: Death self-damage 30% (was 10%).
- **Warlock:** pet health 2 per Stamina (was 7.5): class card and tournament deep dive. Drain Soul's damage-tick shard chance cut a lot: leveling tips now say to finish the kill with it.
- **Druid:** Lacerate is a Feral talent (bear rotation).
- `test_content_corrections` no longer forbids "300% more" (Blizzard reverted to it) and guards the new facts instead.

## 1.12.0 (2026-11-02)
Launch prep, and Forever Sherpa no longer ends on Dec 9.
- **Launch-night posts without pings.** New `LAUNCH_POST_MINUTES = (60, 0)`: a plain post an hour before launch and one at go time, in every countdown channel. `NOTIFY` still controls pings (and brings back T-10 when on). Go-time post points new players to `/tips topic:basics` and `/draggedalong`; Alliance servers get "For the Alliance." `milestone_sent` logs `guild_name` and `ping`.
- **No end date.** `phase()` returns `("live", day_number)` after raids instead of `("done", None)`: titles read "Day N of WoW: Forever", topics rotate through `LIVE_TOPICS` (post-launch topics + raids). A "Next up" line comes from the new `NEXT_UP` list, each entry with a show-until date so posts never point at something stale. Dec 10 callout tells servers the posts keep going.
- **Raid day.** New `raids` deep dive ("Raid night") is Dec 9's topic. Topics without a tip bank take their pro tip from the deep dive, and the highlight never repeats the pro tip.
- **Onyxia everywhere.** Raid headers, check-ins and `/countdown` use `RAIDS_SHORT` (Barrow Deeps, Hyjal Summit and Onyxia's Lair). On Nov 2 the countdown header still listed only two raids.
- **Blocked channels.** On Nov 2 two servers' 7 PM posts were blocked by channel permissions and the log blamed the bot being offline. Now: a once-a-week notice in the server's system channel (or first postable channel) with the fix (`blocked_notice_sent`); `slot_missed` has `reason=blocked|offline`; the staging warning goes out once per slot, not every minute of the 3-hour retry window.
- **Setup reminder.** On Nov 2, 8 servers added the bot; Orbitrap (35 members) and GIGACHADDERS never set it up. Servers still not set up 4 hours after joining get one follow-up in the welcome channel (launch countdown + 📍 Post here, no pings). Once per server, only within 7 days of joining, checked by the 30-minute heartbeat. Log events `setup_reminder_sent`, `setup_reminder_no_channel`, `setup_reminder_failed`.
- **Status alerts:** still watch-only. New `status_near_miss` logs WoW posts from Blizzard Support that the matcher skipped, so the wording can be checked on launch night.
- Help and README wording no longer say the bot stops after Dec 9.

## 1.11.1 (2026-10-31)
From live logs. `parse_hhmm` reads `13pm`–`23pm` as 24-hour times (Equinox typed "16pm, 22pm", got rejected and left). `/postnow` re-sends slot 0 when it was only marked done by `skip_passed_slots` (new `skipped` marker) or was sent to a channel the server has moved away from (new `dailychan` records via `Store.posted_channels`); Primeval moved channels after setup and got "already up" three times. Posts sent before 1.11.1 have no channel record and are treated as posted here. `/frequency times:3` maps to the 3-a-day preset.

## 1.11.0 (2026-10-31)
Content pass. Every tip topic has 15+ tips (was 5–11); did-you-know grows from 47 to 120. New `content.dm()` marks datamined or beta-client items: shown with a ⛏️ label, filtered per server via the new `datamined` guild column and `/datamined` command (default on). `render.V()` applies the filter everywhere tips, facts and deep dives are picked; `render.datamined()` scopes it per render. `/tips` Standard now shows 8 tips (Brief 3, Detailed all). Plus One gets `PLUS_FACTS` and a 🎲 hub button. Corrections: Merchant Coast is in the Barrens; Ice Lance +200% vs frozen; Lava Burst 21 / Elemental Mastery 31 / Earthbound 16; Arcane Wrath replaces Missile Barrage at 16; Onyxia's Lair (40) added to Dec 9.

## 1.10.8 (2026-10-31)
Glossary: `bis` (aliases `best in slot`, `bis list`), shown as "BiS". A placeholder that says Forever's lists are coming once there's real data. Someone looked it up on Oct 30 and got "not in my book".

## 1.10.7 (2026-10-30)
Time zone autocomplete can't crash: `resolve_tz` treats a tzdata folder name (`America`) as not-a-zone instead of raising `IsADirectoryError`, and `_tz_ac` falls back to the popular list on any error (logged as `tz_autocomplete_failed`). `American/...` is read as `America/...`.

## 1.10.6 (2026-10-30)
Leaner owner DMs: member count and the bot's server count only. No server name, ID, channel, post time or time zone. Removals still say how long the bot stayed and whether the server was set up. `owner_setup_text` is folded into `owner_alert_text("setup", ...)`.

## 1.10.5 (2026-10-30)
Owner DM when a server finishes its first setup (`/setup` or the 📍 Post here button): server name and size, channel, post times and time zone. Brings the bot in line with the privacy page's "Server alerts" row. Changing settings later doesn't DM.

## 1.10.4 (2026-10-30)
What's new calls out the bot's new profile photo and banner. No 🆕 line in posts; no behavior changes.

## 1.10.3 (2026-10-30)
Log what `/postnow` did. On Oct 30 two admins ran `/postnow` right after setup and the logs showed no `post_sent` and no reason.
- New log event `postnow` with `outcome=` `posted`, `already_up` (today's full post counts as done and the server is on 1 post a day), `already_posted`, `finished`, `blocked`, `failed`, `error` or `other`, plus `slot` and the start of the reply.

## 1.10.2 (2026-10-30)
Fix owner DMs. In 1.10.0 they failed with `'NoneType' object is not callable` (two joins on Oct 30): the method was named `owner_id`, which discord.py's `Bot` already sets to `None`. Renamed to `alert_owner_id`; a test now runs the DM path on a real `ForeverBot`.

## 1.10.1 (2026-10-30)
Keep behind-the-scenes releases out of What's new.
- Releases marked `"internal": True` in `RELEASE_NOTES` are left out of `/whatsnew` and the What's new page. 1.10.0 (owner alerts) and 1.10.1 are internal.

## 1.10.0 (2026-10-30)
Know right away when servers come and go. Four servers added the bot on Oct 30, and two left within minutes.
- **Owner DMs on join and leave.** The bot DMs its owner when it's added to a server (name, members, new total) and when it's removed (how long it stayed, whether it was ever set up).
- The owner is whoever owns the app in the Discord Developer Portal. `OWNER_ID` overrides it; `OWNER_ALERTS=off` turns the DMs off.
- New log events: `owner_dm_sent`, `owner_dm_failed`.

## 1.9.1 (2026-10-30)
Facts check. No behavior changes.
- **Roleplay-PvP ruleset.** Blizzard added it for launch (Aggrend, Oct 22; ruleset article updated Oct 22). Ruleset lists in the day-9 rundown, the ruleset deep dive and the neutral FAQ now name it. Its faction rules aren't announced, so nothing says it locks a faction.
- **Skyborne Wind Blessed 3% → 2% haste** (Blizzard development notes, Oct 26). Day-5 vets line and Skyborne deep dive.

## 1.9.0 (2026-10-30)
Tell servers what changed, without extra messages.
- **🆕 line in the next post after a release.** Releases with a `line` in `RELEASE_NOTES` add one short line above the post's footer, once per server. Existing servers get the 1.8.1 line (clips and time zones) in their next post. Servers set up from now on start up to date and don't get old news.
- **New `/updates [on]`** (admins): turn those lines off or on. On by default.
- **New `/whatsnew`**: the last three releases in plain words, linking to the full page.
- **What's new page** at foreversherpa.github.io/whatsnew.html, built from the same notes with `python tools/build_whatsnew.py <path>`.
- `RELEASE_NOTES` in `content.py` holds the player-facing notes; a test fails if the newest entry doesn't match `__version__`.
- New log events: `update_line_sent`, `updates_set`.

## 1.8.1 (2026-10-29)
Fewer dead ends. On Oct 29 an admin needed three tries at `/setup` because the time zone had to be exactly `America/Chicago`.
- **Time zones the way people type them.** `/setup timezone:` takes `central`, `CST`, `Central Standard Time`, `america/chicago`, `New York`, `UK`, `CET`, `Helsinki`, `UTC-6` and more. The box suggests matches as you type, and the confirmation says what it read ("Read `central` as America/Chicago").
- **Times the way people type them.** `post_time` and `/frequency times:` also take `noon`, `midnight`, `7p`, `7 p.m.`, `19.30`, `1930` and `19h30`.
- **Clear errors.** A time zone or time that still can't be read is quoted back with suggestions ("Did you mean `America/Chicago`?") and "Nothing was changed."
- **No more bare "Run `/setup` first."** Every admin command used before setup (`/pinpost`, `/frequency`, `/postnow`, `/verbosity`, `/statusalerts`, `/clips`) now explains why and offers the **📍 Post here** button.
- **Tips pass.** Every tip now reads "**do this** → why". Merged duplicates (rested XP, Well Fed, camp buffs, recipe tracking, reagent bags, guard directions), put the strongest tips first (Brief shows 3), labeled the Horde-only racial tips, and made the PvP tips faction-neutral. `/tips` titles get their own icons. No new facts.
- New log events: `input_rejected` (field and what was typed), `needs_setup`.

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
