# Rolling facts check

The playbook the scheduled facts check follows. It runs every morning, before the noon posts, plus a deeper pass on Wednesdays.
Goal: posts track the live game within a day, every line has a source, and servers don't keep seeing the same facts.

## Hard rules
- **Never push to `main`, merge, or deploy.** Work on a new branch `facts/YYYY-MM-DD` (add `-deep` on Wednesdays) off the latest `main`.
  Alex merges only after he says "ship it".
- **No pings, no posts, no Discord messages.** Render is read-only (logs only), never trigger a deploy or change env vars.
- **Sources, in order:** Blizzard (news.blizzard.com, the "WoW: Forever Hotfixes" forum thread, Kaivax/Aggrend blue posts,
  development notes, known issues) → Wowhead, Warcraft Tavern, Icy Veins → everything else.
  A non-Blizzard claim needs **two independent sources**. Anything read from the client or game files gets `dm(...)` (⛏️ label).
- **Don't overstate.** "No numbers yet" is not "unchanged"; "planned for Tuesday" is not "live"; "none at launch" is not "never".
- **Time-limited lines get `--expires`** (anything with "planned", "this week", "until", a date in the future).
- Tips are written as **"do this → here's the benefit"**, and skip what a veteran Horde PvP player already knows.
  Facts and deep-dive lines are plain sentences. Match the tone of the lines around them.

## Daily run (about 15–25 minutes)
1. `git fetch origin main && git checkout -b facts/<today> origin/main`, `pip install -r requirements.txt`.
2. **What changed in the game since the last run?** Read Blizzard's Forever hotfix thread and news, Wowhead's Forever
   blue tracker, then Warcraft Tavern. List each change with its date and link.
3. **Does the bot say anything those changes make wrong?** `grep -rn` `forever_bot/` (content.py, classes.py, guides.py)
   for the spell, zone, item or number. Fix it in place. If a line is only true until a date, give it `--expires`.
4. **Re-check old lines:** `python tools/facts.py due 15` lists the 15 lines checked least recently. Check each against a
   source. Correct it, retire it, or mark it `python tools/facts.py verified "<unique part>" --source <url>`.
5. **Add 3–5 new lines** across the live topics (leveling, professions, travel, gold, pvp, legacy, camping, raids) and
   did-you-know, favouring what's new this week. For each candidate run `python tools/facts.py dupes "<text>"` first and
   drop it if it mostly repeats an existing line. Add it to the pool in `content.py` (in the dated block at the end of the
   facts passes, newest last) or `classes.py`.
6. `python tools/facts.py sync`, then for every new line
   `python tools/facts.py record "<exact text>" --source "<url(s)>" --added <today> [--expires <date>]`.
   Retire anything `python tools/facts.py expiring 0` shows as past due (delete it from the pool and `sync`).
7. `python -m pytest tests -q` must pass. `python -m forever_bot.preview --date <tomorrow>` and read it: no repeats inside
   a post, nothing stale, labels right.
8. Bump the patch version in `forever_bot/__init__.py`, add a CHANGELOG entry (what changed and the source for each), and a
   `RELEASE_NOTES` entry (`line: None`). Commit and push the branch.
9. **Log glance (read-only):** Render service `forever-countdown`, last 24h of `error` / `warning` lines. Note anything new.
10. Report: what changed and why (with links), what was re-verified, anything retired, anything weird in the logs,
    and the branch name. If nothing changed in the game and nothing needed fixing, say so in one line and don't push an empty branch.

## Wednesday deep pass (adds to the daily run)
- Read Tuesday's class tuning and hotfixes in full, then re-check **every class card, `/keybinds` layout and rotation**
  for the classes it touched (classes.py, guides.py). Update numbers, talents and ability names.
- Re-check the raid lines (`RAIDS_SHORT`, `DEEP_DIVES["raids"]`, `KEY_DATES`, `NEXT_UP`) against Blizzard's latest roadmap
  and raid posts. Add exact unlock times once Blizzard announces them.
- `python tools/facts.py due 40` instead of 15.
