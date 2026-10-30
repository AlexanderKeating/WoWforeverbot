"""
Everything the bot says about WoW: Forever lives here. Edit freely.

Compiled Oct 24, 2026 from Blizzard posts and coverage (Warcraft Tavern, Icy Veins,
Wowhead, Kami Labs, timesaver.gg, Raider.IO bracket data).

Forever is NOT retail and NOT Classic:
  - no realms: one mega-realm per ruleset (Normal / PvP / RP / RP-PvP; Hardcore later) per region
  - PvP ruleset locks you to one faction per account
  - no cross-ruleset grouping, no character transfers at launch
  - PvP = Honor (currency) + Rank Points (14-rank personal track, weekly cap), no rating
"""
from datetime import datetime, timezone

# ------------------------------------------------------------------ milestones
# Nov 4, 2026 3:00 PM PST == 23:00 UTC (DST ends Nov 1, so PST not PDT)
LAUNCH = datetime(2026, 11, 4, 23, 0, tzinfo=timezone.utc)
# Raid unlock time not announced; reset is Tuesday but Dec 9 is a Wednesday.
# Treated as a date-only milestone (count days, no exact time).
RAIDS_DATE = "2026-12-09"

DEFAULT_TZ = "America/Chicago"
DEFAULT_POST_TIME = "12:00"
BRAND_COLOR = 0x3FA7D6
NEWS_COLOR = 0xD85A30
GREEN = 0x1D9E75

# (iso date, text). Shown in /dates and used for "Next up".
KEY_DATES = [
    ("2026-10-27", "Name reservation opens, 1 PM Pacific / 3 PM Central (Skyborne pack owners; 3 names)"),
    ("2026-11-03", "Name reservation ends"),
    ("2026-11-04", "Launch"),
    ("2026-12-09", "Raids unlock: Barrow Deeps (10) and Hyjal Summit (20)"),
]
PAST_DATES = [
    ("2026-09-12", "Announced at BlizzCon"),
    ("2026-09-17", "Beta opens"),
    ("2026-10-17", "Forever Open qualifiers"),
    ("2026-10-18", "Forever Open finals"),
    ("2026-10-21", "Open stress test"),
    ("2026-10-23", "Beta closes"),
]
LATER = [("Winter 2026", "Hardcore ruleset"), ("Spring / Summer 2027", "Major content updates")]

# One-off pings to every server at an exact time (UTC). (iso datetime, key, text)
EVENT_PINGS = [  # (UTC time, key, text). Times checked against Blizzard's announcement on Oct 27.
    ("2026-10-27T19:30:00+00:00", "names-30m",
     "📛 **Name reservation opens in 30 minutes** (<t:1793131200:t> your time · 1 PM Pacific / 3 PM Central).\n"
     "Who: Skyborne Heroic or Epic pack owners, or the Warcraft Forever Collection, on the account that bought it.\n"
     "You get **3 names total across all rulesets**. Names are first + last, and only the full pair has to be unique, "
     "so have a few combos ready. Open Battle.net now so you're not stuck patching at 3."),
    ("2026-10-27T20:00:00+00:00", "names-open",
     "📛 **Name reservation is open now.** First come, first served, so go get your name.\n"
     "-# PvP ruleset → Horde. Creating the character now also protects you if Blizzard pauses new characters "
     "for a crowded faction on launch night. Runs through Nov 3."),
    ("2026-11-03T16:00:00+00:00", "names-last",
     "⏰ **Last day of name reservation.** If you haven't locked in your name yet, today's the day."),
    # 1.11: one plain message when servers open (= LAUNCH, 3 PM Pacific / 5 PM Central). No ping.
    ("2026-11-04T23:00:00+00:00", "launch-open",
     "🚀 **WoW: Forever is live.** Servers are open now (<t:1793833200:t> your time).\n"
     "Expect queues and crowded starting zones tonight. Group up with friends early so you land on the same layer, "
     "and group with people hunting the same mobs instead of racing them.\n"
     "-# Daily posts keep going: from tomorrow it's a topic a day and the countdown to raids."),
]

# Shown at the top of the daily post on that date.
TODAY_CALLOUTS = {
    "2026-10-26": "📛 **Name reservation opens tomorrow at 1 PM Pacific / 3 PM Central.** 3 names total across all rulesets. Pick your first + last name ideas tonight (`/faq` has the rules).",
    "2026-10-27": "📛 **Name reservation opens today at 1 PM Pacific / 3 PM Central.** Skyborne pack owners can reserve **3 names total** across all rulesets, through Nov 3. Create your characters now rather than on launch night: if a faction gets crowded on PvP, Blizzard can pause *new* characters.",
    "2026-11-03": "⏰ **Last day of name reservation.**",
    "2026-11-04": "🚀 **It's launch day.**",
}

# ------------------------------------------------------------------ matching
# Text matching for news/clips. Normalized (lowercase, no punctuation/accents).
FOREVER_ALIASES = [
    "wow forever", "world of warcraft forever", "warcraft forever", "wowforever",
    "forever beta", "forever open", "forever launch", "forever stress test",
    "classic plus", "classic+", "skyborne", "darkspear islands", "zephras",
    "barrow deeps", "shen dralas", "shendralas", "riverglades",
]
# "forever" alone counts only if one of these also appears
FOREVER_WEAK = ["forever"]
WOW_CONTEXT = ["wow", "warcraft", "azeroth", "horde", "alliance", "blizzard", "raid", "dungeon", "classic"]

# Until Twitch adds a Forever category, also show WoW-category clips from STREAMERS (labeled as WoW).
CLIPS_LOOSE_UNTIL_CATEGORY = True
CLIPS_LOOSE_MAX = 2
CLIP_MIN_VIEWS = 20  # 1.6.1: skip clips almost nobody watched

# Twitch category names to try, in order. First hit wins; WoW main category is the fallback.
TWITCH_GAME_NAMES = [
    "World of Warcraft: Forever", "World of Warcraft Forever", "WoW: Forever", "WoW Forever",
]
TWITCH_FALLBACK_GAME = "World of Warcraft"

# Pinned streamers (Twitch logins). Their clips get a boost; the category feed finds everyone else.
# "tipsout" removed: login not found on Twitch (Oct 25). Check the event=twitch_login_not_found log line.
STREAMERS = ["summit1g", "xaryu", "esfandtv", "sodapoppin", "zackrawrr", "pikabooirl"]

# Optional YouTube channels: {display name: channel_id starting "UC"}. Leave empty to skip.
YOUTUBE_CHANNELS: dict[str, str] = {}

# YouTube videos in posts. Turned off in 1.1.1 (picks weren't great). Set True to bring them back;
# the fetch code and YOUTUBE_API_KEY handling are kept.
SHOW_YOUTUBE = False

# Notifications. Off since 1.1.2: no @role pings, and no standalone reminder / launch-countdown posts
# (daily posts already carry that info). Set True to bring back pings, the name-reservation alerts,
# launch-night countdown posts, and the 🔔 opt-in button on the pinned card.
NOTIFY = False

# 1.3.3: the name-reservation alerts (EVENT_PINGS below) post again as plain channel messages.
# No @role pings unless NOTIFY is also True. Launch-night countdown posts stay off.
EVENT_POSTS = True

# 1.6: WoW: Forever service status from Blizzard Support's Bluesky (free public API, no key).
# Starts watch-only: logs event=status_would_post. Flip STATUS_POST_TO_CHANNELS once the logs look right.
STATUS_SOURCES = [{"name": "Blizzard Support", "handle": "support.blizzard.com"}]
STATUS_POST_TO_CHANNELS = False
STATUS_CHECK_MINUTES = 5
STATUS_MAX_AGE_H = 6

# Policy pages live in the ForeverSherpa/foreversherpa.github.io repo (GitHub Pages).
SITE_URL = "https://foreversherpa.github.io"
TERMS_URL = SITE_URL + "/terms.html"
PRIVACY_URL = SITE_URL + "/privacy.html"
BOT_INVITE_URL = ("https://discord.com/oauth2/authorize?client_id=1563945999670706297"
                  "&scope=bot+applications.commands&permissions=19456")

# News sources. Each tries feed URLs in order, then RSS autodiscovery on the homepage.
# Removed after first live run (Oct 25): Blizzard (no public RSS; Wowhead mirrors blue posts),
# Icy Veins (403s bots; not worth working around).
NEWS_SOURCES = [
    {"name": "Wowhead", "feeds": ["https://www.wowhead.com/news/rss/all", "https://www.wowhead.com/news/rss/classic"],
     "home": "https://www.wowhead.com/news", "trusted": False},
    {"name": "Warcraft Tavern", "feeds": ["https://www.warcrafttavern.com/feed/", "https://www.warcrafttavern.com/forever/feed/"],
     "home": "https://www.warcrafttavern.com/forever/news/", "trusted": False},
    {"name": "MassivelyOP", "feeds": ["https://massivelyop.com/feed/"],
     "home": "https://massivelyop.com/", "trusted": False},
]
# trusted=True: everything from that source counts as Forever news only if it matches aliases too.
# (Kept as a flag in case Blizzard gets a Forever-only feed later.)

# Clip titles containing these get skipped (new players in the channel).
TITLE_BLOCKLIST = ["fuck", "shit", "bitch", "cunt", "nigg", "fag", "retard", "rape", "kys", "porn", "nsfw"]

CLASSES = ["Warrior", "Paladin", "Hunter", "Rogue", "Priest", "Shaman", "Mage", "Warlock", "Druid"]

# ------------------------------------------------------------------ daily rundowns
# Key = calendar days until launch (in the server's time zone) on the day of the post.
# "new" = plain English for first-timers. "vets" = the detail. "special" plugs in a block.
RUNDOWNS = {
    11: {"title": "What is WoW: Forever?",
         "new": "A fresh version of World of Warcraft that starts from the 2004-era world and adds new zones, dungeons and story. Your normal WoW sub covers it. Everyone starts at level 1 on Nov 4.",
         "vets": "Blizzard's official Classic+. Set after the fall of Lordaeron, before Molten Core. Level cap is 60 permanently; progress comes from new content at 60, not new levels. Lives alongside retail and Classic."},
    10: {"title": "The $100K beta duel tournament", "special": "tourney",
         "new": "Streamers ran a 1v1 dueling tournament on the beta, Horde side, PvP rules, level 30. 1,380 players checked in. A Warlock won $50,000.",
         "vets": "Warlockguy (20th seed, last lock in via tiebreakers) dropped G1, then beat Neepzen 3–1. Shamans took 3rd and 4th. #1 seed Korleone went out 9th–12th."},
    9: {"title": "Rulesets: there are no realms",
         "new": "You don't pick a server. You pick a ruleset: Normal, PvP, Roleplay or Roleplay-PvP. Everyone on the same ruleset in your region plays in one big shared world. We're on **PvP, Horde**.",
         "vets": "One mega-realm per ruleset per region, with layering. PvP ruleset = one faction per account. No cross-ruleset grouping, no transfers at launch. Hardcore comes later; dead Hardcore characters can move to another ruleset, PvP included."},
    8: {"title": "Names work differently", "callout_date": "2026-10-27",
         "new": "Every character gets a first and a last name. Someone else can have your first name, but not your full name.",
         "vets": "Uniqueness is regional since realms are gone. Reservation (Oct 27–Nov 3) needs the Heroic pack or higher and is tied to the account that bought it. Blizzard may temporarily limit character creation on the PvP ruleset for an overloaded faction, so reserve early."},
    7: {"title": "Four new regions",
         "new": "Forever adds four zones that never existed in the original game, from a new starter island to an endgame mountain.",
         "vets": "**Mount Hyjal** (endgame, Hyjal Summit plus a Barrow Deeps entrance) · **Shen'dralas** (the ruins between Mulgore and Desolace) · **Riverglades** (EK east coast, ~35–45, 150+ quests) · **Zephras Isle** (Skyborne start, 1–12)."},
    6: {"title": "Nine new dungeons",
         "new": "Dungeons are 5-player group zones with bosses and loot. Forever launches with nine brand-new ones from level 13 to 60.",
         "vets": "Hall of Thanes 13–18 · Ruins of Lordaeron 15–20 · Whelgar's Excavation 24–29 · City of Dalaran 28–33 · Drowned City 35–40 · Krol'dok Stronghold 40–55 (outdoor) · Alcaz Prison 48–53 · Blackmaw Hold 55–60 · Shaper's Terrace 58–60."},
    5: {"title": "The Skyborne",
         "new": "A new playable race: wind-touched elves who start on their own island. On Horde, they can be Shamans.",
         "vets": "Highborne exiles tied to Skywall. Faction picked at creation: Horde via the Earthen Ring (Shaman), Alliance via the Kirin Tor (Mage). Also Warrior, Hunter, Rogue, Druid, with their own druid forms. Needs the Skyborne Heroic Pack or higher."},
    4: {"title": "PvP: honor, ranks, Darkspear Islands",
         "new": "Battlegrounds are team PvP matches you queue for. Win, earn Honor, buy PvP gear. Ranks unlock rewards like a trinket, cloaks, mounts and epic weapons.",
         "vets": "Honor is a currency (blue and epic PvP sets), normalized across BGs. Rank Points fill a 14-rank personal track with a weekly cap, not the old ladder. Seasonal weekly tasks give bonus points and Legacy Points. New 15v15 Darkspear Islands: EotS-style flag plus AB-style caps. No arena or rating."},
    3: {"title": "New systems",
         "new": "Small quality-of-life changes: camp out with friends for a bonus, earn perks for your alts, and choose old-school or updated character models.",
         "vets": "**Camping** (craft at others' camps, shared rest buff) · **Legacy** (each 1–60 finish unlocks alt perks; shared across rulesets except Hardcore) · opt-in **transmog** · HD/classic model toggle · controller support · no flying, no level scaling."},
    2: {"title": "Raids and the roadmap",
         "new": "Raids are big group boss fights. The first two open Dec 9, about five weeks after launch.",
         "vets": "Barrow Deeps (10) and Hyjal Summit (20) on Dec 9; Hyjal drops Forever's first legendary. ||Barrow Deeps reportedly once held a certain infamous demon hunter.|| Hardcore in winter, major updates spring and summer 2027, including a 'revamped iconic raid'."},
    1: {"title": "Launch-day checklist",
         "new": "Tomorrow. Make sure your sub or game time is active, pre-install from the Battle.net dropdown, and pick **PvP ruleset → Horde**.",
         "vets": "Beta and stress-test characters are wiped. Expect queues and layering at launch. PvP faction lock is per account, so don't test an Alliance alt on PvP first."},
    0: {"title": "Launch day",
         "new": "Servers open at the time below. See you in Azeroth.",
         "vets": "Expect queues. Group with friends early so you land on the same layer."},
}

NEWBIE_TIPS = [  # 1.2.2: "**do this** → benefit", no tips a Horde PvP player already knows
    "**Set your hearthstone at the inn closest to where you'll quest next, not where you are** → your hearth back ends your night next to tomorrow's quests.",
    "**Visit your class trainer on every even level** → new ranks and spells come every couple of levels, and missing them is the most common reason a new character feels weak.",
    "**Pick up two gathering professions from level 1 (Herbalism and Mining is a classic pair)** → you sell what you pick up along the way, and that's what pays for your mount at 40.",
    "**Start setting gold aside early for level 40** → riding plus your first mount costs about 100 gold, and that's the biggest purchase you'll make while leveling.",
    "**Skip mobs with a gold dragon on their portrait unless you're grouped** → they're elites built for groups, and they're the most common early death.",
    "**Spend your first talent points at 10, then check a guide before you hit 20** → Forever reworked the talent trees, so a build from the original game won't carry over.",
    "**Ask a city guard for directions** → they put a mark on your map for the bank, trainers, flight master and more.",
    "**Move your abilities onto keys around WASD early** → you'll be able to move and fight at the same time. `/keybinds` shows a starting layout for your class.",
    "**Queue a battleground even when your team looks outmatched** → you earn Honor win or lose, and a win only adds more on top.",
    "**Don't judge gear by how it looks** → transmog is opt-in, so a player in starter-looking clothes might be wearing their best gear under it.",
    "**Run your first dungeons with a guildmate who knows the route** → you'll learn the pulls and the loot rules without losing a group to a wipe.",
]

# tag: "new" | "vet" | "horde" (horde = only shown when server faction is horde)
DID_YOU_KNOW = [
    ("new", "Your regular WoW subscription already includes Forever. No separate purchase."),
    ("new", "Forever is set before Molten Core opened, which is why the original raids are still locked."),
    ("new", "There are no flying mounts and no level scaling. Zones stay as dangerous as they were built."),
    ("new", "Original 2004 WoW launched with zero battlegrounds. Forever launches with a brand-new 15v15 one."),
    ("new", "Controllers are officially supported in Forever."),
    ("vet", "Launch ships with nine new dungeons and over 1,000 new quests across 1–60."),
    ("vet", "Darkspear Islands mixes Eye of the Storm's neutral flag with Arathi Basin–style capture points."),
    ("horde", "In Darkspear Islands, the Horde fights alongside the Darkspear trolls; the Alliance shows up as the Theramore Expeditionary Force."),
    ("vet", "Skyborne keep vanilla's asymmetry: Shaman only on Horde, Mage only on Alliance."),
    ("vet", "Hyjal Summit is a 20-player raid where Archimonde fell, and it drops Forever's first legendary weapon."),
    ("vet", "Talent trees drop a lot of the boring +1% talents in favor of choices you actually feel."),
    ("vet", "Paladins get a new seal built for tanking, plus some group-healing talents."),
    ("vet", "Dwarves deal +5% damage to beasts, and Undead get a chance to drain health. Racials got a pass."),
    ("vet", "Tidal Charm and Whitemane's Chapeau come back reworked among hundreds of items with new effects."),
    ("vet", "Riverglades is a 35–45 zone about everyday frontier life rather than world-ending stakes."),
    ("vet", "Honor gains are normalized across battlegrounds, so there's no reason to farm only Alterac Valley."),
    ("vet", "Rank Points have a weekly cap. No more account-sharing to keep a rank."),
    ("vet", "Legacy Points are shared account-wide across rulesets, except Hardcore."),
    ("vet", "Blizzard dev Aggrend said the beta found more problems in six hours than six months of internal testing."),
    ("vet", "The beta queue on day one passed 17,000 players."),
    ("horde", "17 of the 36 Forever Open finalists were Undead. Will of the Forsaken vs. Fear was huge."),
    ("vet", "Soul Link moved from a 31-point to a 21-point talent, so it's live at level 30. Every Warlock finalist ran 21 in Demonology."),
    ("vet", "All four Mage finalists in the Forever Open lost in the same round and split the Mage prize, about $1,389 each."),
    ("vet", "Blizzard built a dueling arena in Hyjal Crater for Forever Open finals day, even though it was a community event."),
    ("vet", "The Forever Open grand final ended around 4:30 AM Paris time, hours past schedule."),
    ("vet", "The collector's edition statue, a dwarf and a bear, is a nod to Hardcore and to November 2004."),
    ("vet", "The roadmap has a mystery 'revamped iconic raid' in summer 2027."),
]

# ------------------------------------------------------------------ layer 3: pro tips
# One concrete, actionable tactic per day, tied to that day's topic. Sources: Blizzard posts,
# Warcraft Tavern XP/riding/profession guides, Method camping + mount guides (Oct 2026).
PRO_TIPS = {
    11: "Set your hearthstone at a big quest hub like the Crossroads, not your starter inn, and click every flight master you pass. Long flights only work if you've unlocked the stops in between.",
    10: "Undead vs a Warlock: save Will of the Forsaken for the Fear, not the first stun you see. It breaks Fear, Charm and Sleep, which is exactly what locks lean on.",
    9: "Agree on PvP + Horde with your friends **before** anyone makes a character. One Alliance test character on the PvP ruleset locks your whole account out of Horde there.",
    8: "Pick two or three first + last name combos before Oct 27. The full name has to be unique across the region, so popular first names need a good surname.",
    7: "When the Barrens dries up in your mid-30s, head to Riverglades: 150+ new quests built for roughly 35–45.",
    6: "Run dungeons with people near your level. Higher-level members cut everyone's kill XP, but quest turn-in XP is never reduced by grouping.",
    5: "Horde Skyborne buy riding and Galestrider mounts from Genn Fairweather on Zephras Isle. Other races' mount vendors won't sell to you until Exalted.",
    4: "Darkspear Islands: take bases first, then run the center flag to a base you own. A flag with no friendly base to score at is wasted. First team to 2,000 points wins.",
    3: "Logging out in the field? Put down a Cozy Sleeping Bag. Lying on it counts as a rested area, so you keep earning rested XP while offline.",
    2: "Camp buffs don't stack with class buffs (camp Kings is 8% vs the real 10%). In raids, treat camps as a backup for missing classes, not a bonus.",
    1: "Don't power-level with a much higher friend for kills: it tanks your XP. Quest together instead; turn-in XP isn't affected by grouping.",
    0: "Starting zones will be packed. Only the first player or group to tag a mob gets credit, so group up with people hunting the same mob instead of racing them.",
}

# ------------------------------------------------------------------ layer 4: deep dives
# Behind the 🔎 button on each post (private reply, so the channel stays clean).
# Keyed by days-to-launch, or by topic name for post-launch rotation.
DEEP_DIVES = {
    11: ("Getting around Azeroth", [
        "**No mount until 40.** Budget about 100g for Apprentice Riding plus your first mount. Skip trainer ranks you won't use to save up.",
        "**Travel order:** hearthstone > Mage portal / Warlock summon > flight path > zeppelin. No modern-style portal rooms.",
        "**Other continents:** zeppelins and boats only, unless a Mage or Warlock helps.",
        "**Lost?** Ask any guard: it marks the bank, trainers and more on your map.",
        "**Shamans and Druids** are the only classes with a travel form before 40.",
    ]),
    10: ("Reading the tournament data", [
        "**Who:** 36 finalists, top 4 of each class after six Swiss rounds with 1,380 players.",
        "**Warlocks:** 26–7 in duels vs other classes. Soul Link at 21 points plus pet scaling made them hard to kill at 30.",
        "**Shamans** were the other standout: 19–11 and both 3rd and 4th place.",
        "**Mages** went 4–12 on finals day, after a week of forum calls to nerf them. Hype isn't results.",
        "**Why it may not hold at 60:** more trinkets and Fear answers, damage outscaling healing, and BGs where nobody is forced to stand and duel.",
        "**Pick your class for fun first.** No arena is announced; Forever PvP is battlegrounds and world PvP.",
    ]),
    9: ("Rulesets in practice", [
        "**Normal / PvP / Roleplay / Roleplay-PvP** at launch; **Hardcore** later. Each is one big world per region, split into layers when busy.",
        "**PvP = one faction per account.** Normal and RP don't lock you.",
        "**No cross-ruleset grouping** and **no transfers at launch**: your ruleset is where your friends must be.",
        "**Shared across rulesets:** collections and Legacy points (not Hardcore).",
        "**Hardcore deaths** can move to another ruleset, PvP included.",
        "**Faction balance:** Blizzard may temporarily limit new characters for an overloaded faction on PvP, like Season of Discovery did.",
    ]),
    8: ("Name reservation checklist", [
        "**Window:** Oct 27 → Nov 3. Needs the Skyborne Heroic Pack or higher.",
        "**Tied to the account** that bought the pack.",
        "**Two-part names:** first names can repeat; full names can't.",
        "**Make your PvP Horde character first.** That locks the right faction for your account on PvP.",
        "**Not guaranteed:** if a combo is taken, try a different surname rather than a misspelled first name.",
    ]),
    7: ("Zone guide", [
        "**Zephras Isle (1–12):** Skyborne start. Highborne exiles allied with wind spirits.",
        "**Riverglades (~35–45):** EK east coast between Redridge, Burning Steppes, Badlands and Swamp of Sorrows. 150+ quests, home of Krol'dok Stronghold.",
        "**Shen'dralas:** the ruins between Mulgore and Desolace, with Shen'dralar, Gordunni and Magram, tied to Maraudon and Razorfen Downs.",
        "**Mount Hyjal (endgame):** Darkwhisper Gorge, Hyjal Summit, and one of three Barrow Deeps entrances.",
    ]),
    6: ("Dungeon tips", [
        "**Group:** tank, healer, three damage. Talk before you pull.",
        "**Level spread matters:** high-level members lower everyone's kill XP.",
        "**Cross-faction sneaking:** Horde must sneak into Hall of Thanes (Ironforge); Alliance sneaks into Ruins of Lordaeron.",
        "**Krol'dok Stronghold (40–55)** is outdoors, and cultists chant there at night.",
        "**Alcaz Prison (48–53)** is enterable for the first time ever.",
        "**Endgame pair:** Blackmaw Hold (55–60, Azshara) and Shaper's Terrace (58–60, Un'Goro).",
    ]),
    5: ("Skyborne for Horde", [
        "**Horde Skyborne** work with the Earthen Ring and unlock **Shaman**.",
        "**Also:** Warrior, Hunter, Rogue and Druid, with unique druid forms.",
        "**Start:** Zephras Isle, levels 1–12.",
        "**Mounts:** Galestriders from Genn Fairweather at Fairweather Stables.",
        "**Needs** the Skyborne Heroic Pack or higher.",
    ]),
    4: ("PvP deep dive", [
        "**Darkspear Islands:** 15v15, levels 30–60, off Dustwallow Marsh. Four capture points plus a center flag; first to 2,000.",
        "**Queue** from a battlemaster in a capital, in the Barrens, or the Darkspear Raiders base at Merchant Coast.",
        "**Darkspear rep** unlocks vendor trinkets, rings, cloaks, weapons and armor; Exalted unlocks a tabard questline. Turn in Marks of Honor.",
        "**Honor** buys a blue PvP set and an epic PvP set. Gains are normalized across BGs.",
        "**Rank Points** climb a 14-rank track with a weekly cap. Ranks reset each season.",
        "**Rank rewards:** 2 trinket · 3 cloaks · 4 necklace · 5 combat potions · 7 battle standard · 9 epic boots token · 11 mounts · 14 epic weapons.",
    ]),
    3: ("Camping and leveling speed", [
        "**Unlock:** \"The Great Outdoors\" quest around level 5, plus Cooking for a Basic Campfire.",
        "**Campfire tiers:** Cooking 1 (3 items), 90 (5), 200 (10). Each player adds one item.",
        "**Best leveling items:** Leatherworking Camp Tent (1h rested XP buff, survives death) and Cozy Sleeping Bag (up to +3% XP, counts as rested).",
        "**Rested XP** doubles kill XP; it builds 5% of a level per 8h, up to 150%.",
        "**Well Fed** cooking food: +5% kill XP for about 15 minutes.",
        "**Other camp buffs:** Mining melee AP, Skinning crit, Herbalism intellect, Engineering repair vendor, Fishing 8% stats.",
    ]),
    2: ("Gearing toward Dec 9", [
        "**Raids:** Barrow Deeps (10) and Hyjal Summit (20). Hyjal drops Forever's first legendary weapon.",
        "**Stock up on consumables:** an Alchemist + Herbalist in the guild keeps everyone in potions.",
        "**Save gold:** Journeyman Riding is 1,000g at 60, epic mounts 200g each.",
        "**Discounts:** Honored with your home faction is 10% off riding and mounts; the Bartering Legacy talent adds up to 10% off mounts.",
        "**Warlocks** get a free level-40 mount quest from Strahad Farsan in Ratchet.",
    ]),
    1: ("Launch-night game plan", [
        "**Before:** sub or game time active, client pre-installed, addons updated.",
        "**Create:** PvP ruleset → Horde → your reserved name.",
        "**Group early** so you land on the same layer.",
        "**Learn Cooking** early for campfires; pick a gathering profession for gold.",
        "**Expect** queues, crowded starting zones and mob tagging. Group up rather than compete.",
    ]),
    0: ("First hour checklist", [
        "**Grab every flight path** and set your hearthstone at a hub.",
        "**Learn Cooking** and do \"The Great Outdoors\" around level 5 to unlock camping.",
        "**Two gathering professions** (like Herbalism and Mining) fund your level-40 mount.",
        "**Train spells** every couple of levels.",
        "**On PvP,** watch for Alliance in contested zones and travel with friends.",
    ]),
    # ---- post-launch rotation topics
    "leveling": ("Leveling faster", [
        "**Rested XP** doubles kill XP. Log out in inns, cities or on a Cozy Sleeping Bag.",
        "**Gray quests and mobs** (5+ levels below) give no XP; quests over 5 levels below lose 10–20% per level.",
        "**Grouping:** big parties split kill XP; quest turn-ins are never reduced.",
        "**Well Fed** food adds +5% kill XP; the Camp Tent adds a rested buff that survives death.",
        "**Explore:** new areas give a little XP.",
    ]),
    "gold": ("Gold basics", [
        "**Target:** about 100g by 40 for your first mount, 1,000g by 60 for Journeyman Riding.",
        "**Gathering pays:** Herbalism, Mining and Skinning sell steadily early on.",
        "**Alchemy + Herbalism** is the classic gold-making pair.",
        "**Discounts:** Honored with your home faction saves 10% on riding and mounts.",
    ]),
    "professions": ("Professions in Forever", [
        "**Two primaries** plus all three secondaries (Cooking, First Aid, Fishing). Secondaries can't be unlearned.",
        "**Caps:** Apprentice 75 · Journeyman 150 (lvl 10) · Expert 225 (lvl 20) · Artisan 300 (lvl 35).",
        "**No passive bonuses.** Value comes from crafts and camp items, which unlock at skill 20, 140 and 300.",
        "**New UI:** a profession window (K), recipe search and tracking, and a separate reagent bag slot.",
        "**Pairs:** Alch + Herb, BS + Mining, Eng + Mining (PvP), Ench + Tailoring, LW + Skinning.",
        "**Tauren Cultivation** lets you pick herbs without Herbalism, or doubles yield with it.",
    ]),
    "pvp": ("PvP progression", [
        "**Honor** buys blue and epic PvP sets; it's normalized across BGs, and holiday-week BGs give extra.",
        "**Rank Points** have a weekly cap, so steady play beats marathons. Ranks reset each season.",
        "**Weekly tasks** give bonus Honor, Rank Points, and sometimes a Legacy Point.",
        "**Darkspear Islands:** bases first, then flag to a base you own. First to 2,000.",
    ]),
    "travel": ("Travel and mounts", [
        "**Mount at 40:** 100g for Apprentice Riding with your first mount; extra colors 20g.",
        "**Epic at 60:** 1,000g Journeyman Riding, 200g per epic mount, +100% speed.",
        "**Horde vendors:** wolves in Orgrimmar, raptors in Sen'jin, kodos in Bloodhoof, skeletal horses in Brill.",
        "**Free mounts:** Warlocks via Strahad Farsan in Ratchet; Horde Paladins have their own quest.",
    ]),
}
POST_LAUNCH_TOPICS = ["leveling", "professions", "travel", "gold", "pvp"]

# Short tips for /tips <topic>, and the rotating daily "New player tip" (basics).
TIPS = {"basics": NEWBIE_TIPS}  # topics are filled in below (1.8.1 tips pass)

# ------------------------------------------------------------------ tournament
TOURNEY = {
    "summary": (
        "Community event by **Tips Out**, streamed by **Esfand** and **Xaryu**; **TimTheTatman** doubled "
        "the pot to $100K. Level-30 Horde characters on the beta PvP ruleset. Oct 17: six Swiss rounds, "
        "1,380 checked in. Oct 18: top 4 per class (36) in double elimination."
    ),
    "top8": [
        ("1", "Warlockguy", "Warlock"), ("2", "Neepzen", "Warlock"), ("3", "Cdewx", "Shaman"),
        ("4", "Oddwaffletv", "Shaman"), ("5–6", "Minpojke", "Druid"), ("5–6", "Azzu", "Paladin"),
        ("7–8", "Jázggz", "Warlock"), ("7–8", "Lamelol", "Paladin"),
    ],
    # finals duels vs other classes, mirrors excluded: (class, won, played, series W–L)
    "winrates": [
        ("Warlock", 26, 33, "13–3"), ("Shaman", 19, 30, "14–6"), ("Paladin", 16, 29, "9–7"),
        ("Druid", 12, 26, "7–8"), ("Priest", 9, 21, "6–8"), ("Hunter", 7, 18, "4–7"),
        ("Rogue", 5, 16, "3–7"), ("Warrior", 4, 15, "3–7"), ("Mage", 4, 16, "2–8"),
    ],
    "why": "Soul Link is a 21-point talent in Forever, so it's live at 30; every lock finalist ran 21 in Demo. All four were Undead (Will of the Forsaken vs Fear).",
    "story": "Oddwaffletv won two tiebreakers to qualify, opened as the 31st seed, dropped to the lower bracket, then knocked out five players. Nine matches in one day for 4th.",
    "prizes": "$50,000 champion; $5,555 to the top finisher of each class. The four Mages tied and split theirs.",
    "caveat": "Level-30 1v1 duels on the beta. Not level-60 battlegrounds.",
}

# ------------------------------------------------------------------ FAQ
FAQ = [
    ("Do I need to buy anything?", "No. An active WoW subscription or game time includes Forever. The Skyborne packs are optional (the Skyborne race needs Heroic or higher)."),
    ("Which server do I pick?", "There are no servers. Pick the **PvP** ruleset and **Horde**. Everyone on PvP in your region shares one world."),
    ("Can I make an Alliance alt?", "Not on the PvP ruleset; it locks your account to one faction there. You can on Normal or Roleplay, but you can't group across rulesets."),
    ("What's a PvP ruleset?", "Players from the other faction can attack you out in the world. It's part of the fun; travel in groups."),
    ("Is this retail or Classic?", "Neither. It's a third version of WoW: the classic-era world with new zones, dungeons, systems and a permanent level 60 cap."),
    ("When does it launch?", "Wed, Nov 4: 3 PM PST · 5 PM CST · 6 PM EST · 23:00 UTC."),
    ("When do raids open?", "Dec 9: Barrow Deeps (10-player) and Hyjal Summit (20-player)."),
    ("Is there arena?", "No arena or rated PvP announced. PvP is battlegrounds and world PvP with Honor and Rank Points."),
]


# ======================================================================= 1.1.2: fuller vets lines + deep dives
# Same facts as above, written to explain why each change matters instead of listing it.
_VETS_LONG = {
    9: ("There are no realm lists in Forever. Each ruleset (Normal, PvP, Roleplay, Roleplay-PvP) is one big shared world per region, "
        "and Blizzard splits it into layers when it gets crowded so busy zones stay playable. On the PvP ruleset your whole "
        "account is locked to one faction, and Blizzard can pause new characters for an overloaded faction, so "
        "creation limits only ever block *new* characters. There's no "
        "grouping across rulesets and no character transfers at launch, so wherever your first character lands is where your "
        "friends need to be. Hardcore arrives later as its own ruleset, and a Hardcore character that dies can move to another "
        "ruleset, PvP included."),
    8: ("With realms gone, names are unique across your whole region instead of per server. That's why Forever uses a first + "
        "last name pair: lots of people can be \"Thrall,\" but only one can be \"Thrall Stormcaller.\" Reservation opens Oct 27 "
        "at 1 PM Pacific and runs through Nov 3. It needs a Skyborne pack, is tied to the account that bought it, and gives you "
        "**3 names across all rulesets**, so spend them on the characters you'll actually play. On PvP, Blizzard may briefly "
        "pause character creation for whichever faction gets too big (Season of Discovery did this), which is one more reason "
        "to lock in your Horde name early."),
    7: ("Forever doesn't just replay the 2004 map. **Zephras Isle** (1–12) is the Skyborne start. **Riverglades** (~35–45) fills "
        "the Eastern Kingdoms coast between Redridge, Burning Steppes, the Badlands and Swamp of Sorrows with 150+ quests and an "
        "outdoor dungeon, giving mid-30s players somewhere fresh when the old zones run dry. **Shen'dralas** finally opens the "
        "ruins between Mulgore and Desolace, tied into Maraudon and Razorfen Downs. **Mount Hyjal** is the endgame zone: "
        "Darkwhisper Gorge, the Hyjal Summit raid, and one of three entrances to Barrow Deeps."),
    6: ("Nine new dungeons fill gaps the original leveling path never covered. The first two are faction-flavored: Horde sneak "
        "into **Hall of Thanes** (13–18) under Ironforge, while Alliance sneak into the **Ruins of Lordaeron** (15–20). The "
        "middle stretch gets Whelgar's Excavation, City of Dalaran and Drowned City, and **Krol'dok Stronghold** (40–55) is an "
        "outdoor dungeon with an unusually wide level range. Endgame adds Alcaz Prison, Blackmaw Hold and Shaper's Terrace. "
        "Higher-level party members reduce everyone's kill XP, so these are best run with people near your level."),
    5: ("The Skyborne are Highborne exiles tied to Skywall who chose a side rather than being born into one. Horde Skyborne work "
        "with the Earthen Ring, which is how they unlock **Shaman**; Alliance Skyborne side with the Kirin Tor and unlock "
        "**Mage**. Either way they can also be Warriors, Hunters, Rogues or Druids, with druid forms of their own. Their "
        "racials lean mobile: **Wind Blessed** gives 2% haste and **Walk on Air** is on a 90-second cooldown. They start on "
        "Zephras Isle (1–12) and require the Skyborne Heroic Pack or higher."),
    4: ("PvP progress uses two separate currencies. **Honor** is what you spend on gear (a blue PvP set and an epic one), and "
        "Blizzard normalized Honor across battlegrounds so you're not stuck farming Alterac Valley. **Rank Points** climb a "
        "14-rank personal track with a **weekly cap**, so a few battlegrounds every week beats one exhausting weekend, and nobody "
        "needs to share an account to hold a rank. Ranks reset each season, and weekly tasks add bonus points plus Legacy "
        "Points. The new 15v15 **Darkspear Islands** (30–60) has four capture points and a center flag you score at a base you "
        "own; first to 2,000 wins. No arena or rated PvP is announced."),
    3: ("**Camping** turns professions into group buffs. Each profession has camp items that unlock at skill 20, 140 and 300, "
        "and the Leatherworking Camp Tent's rested-XP buff even survives death. Camp buffs don't stack with matching class "
        "buffs, so they shine when your group is missing a class. **Legacy** is account-wide progress: every character that "
        "finishes 1–60 unlocks perks for your alts, shared across rulesets except Hardcore. Transmog is opt-in, HD vs. classic "
        "models is a toggle, controllers are supported, and there's still no flying or level scaling, so zones stay as "
        "dangerous as they were built."),
    2: ("The first raids open **Dec 9**, about five weeks after launch, which is roughly how long a steady player needs to hit "
        "60 and gear up. **Barrow Deeps** is a 10-player raid in a night elf prison; **Hyjal Summit** is a 20-player raid where "
        "Archimonde fell, and it drops Forever's first legendary weapon. ||Rumor has it Barrow Deeps once held a certain infamous "
        "demon hunter.|| Molten Core and the other original raids stay locked because the story is set before they opened. "
        "Hardcore arrives in winter, and major updates are planned for spring and summer 2027, including a \"revamped iconic "
        "raid.\""),
    1: ("Beta and stress-test characters are wiped, so everyone starts fresh. Expect queues and layering on launch night: group "
        "up with friends early so the game puts you on the same layer. Once you're in, set your hearthstone at a quest hub, grab every flight path "
        "you pass, and learn Cooking early so you can use campfires."),
    0: ("Servers open at the same moment worldwide. Starting zones will be packed, and only the first player or group to tag a "
        "mob gets credit, so group up with people hunting the same thing instead of racing them. Do \"The Great Outdoors\" "
        "around level 5 to unlock camping, and pick up two gathering professions early: they'll pay for your level-40 mount "
        "(about 100 gold)."),
}
for _k, _v in _VETS_LONG.items():
    RUNDOWNS[_k]["vets"] = _v

DEEP_DIVES.update({
    9: ("Rulesets in practice", [
        "**Four rulesets at launch: Normal, PvP, Roleplay and Roleplay-PvP.** Hardcore comes later. Each one is a single huge world for your region, split into layers when it's busy, so you'll keep seeing the same community instead of being scattered across realms.",
        "**PvP locks your account to one faction.** The first character you make on PvP decides it. Normal and Roleplay don't lock you, so that's where Alliance alts go.",
        "**No cross-ruleset grouping, no transfers at launch.** You can't run a dungeon with a friend on another ruleset, and character transfers aren't available at launch, so agree on PvP Horde before anyone logs in.",
        "**Some progress follows you everywhere.** Collections and Legacy points are shared across rulesets (except Hardcore), so time on an alt elsewhere isn't wasted.",
        "**Hardcore has an escape hatch.** If a Hardcore character dies, it can transfer to another ruleset, including PvP.",
        "**Faction balance is managed.** Like Season of Discovery, Blizzard can temporarily pause new characters for an overloaded faction on PvP, so creating your character early matters.",
    ]),
    8: ("Name reservation checklist", [
        "**When:** Oct 27 at 1 PM Pacific (3 PM Central) through Nov 3. The bot pings 30 minutes before it opens and again when it's live.",
        "**Who:** owners of a Skyborne pack. It's tied to the Battle.net account that bought it, so reserve on the account you'll play.",
        "**How many:** 3 names total, across all rulesets. Two PvP characters leaves room for just one Normal or Roleplay name.",
        "**How names work:** first + last name, unique across the region. If your first name is taken, change the surname, not the spelling; \"Grommash Ashfall\" ages better than \"Grommashh.\"",
        "**Order matters on PvP:** make your Horde character first so the faction lock goes the right way.",
        "**No guarantees:** it's first come, first served. Have two or three combos ready before 3 PM Central.",
    ]),
    7: ("Zone guide", [
        "**Zephras Isle (1–12):** the Skyborne starting island. Highborne exiles made a pact with the wind spirits here, and it's where Skyborne learn their class before joining the wider world.",
        "**Riverglades (~35–45):** the Eastern Kingdoms east coast, between Redridge, Burning Steppes, the Badlands and Swamp of Sorrows. It has 150+ quests about everyday frontier life, and it's home to Krol'dok Stronghold.",
        "**Shen'dralas:** the ruins players have stared at between Mulgore and Desolace for twenty years, now open, with the Shen'dralar, Gordunni and Magram, and ties to Maraudon and Razorfen Downs.",
        "**Mount Hyjal (endgame):** Darkwhisper Gorge, the Hyjal Summit raid, and one of three entrances to Barrow Deeps. Expect to spend a lot of time here at 60.",
        "**Why it matters:** with more zones in the 30–50 range, the classic mid-level slump (and the crowding that comes with it) should be much lighter.",
    ]),
    6: ("Dungeon tips", [
        "**Build a balanced group:** one tank, one healer, three damage dealers. Talk before you pull. A 10-second plan saves a 10-minute run back from the graveyard.",
        "**Mind the level spread:** higher-level members reduce everyone's kill XP, so for leveling, run with people within a few levels of you.",
        "**Faction sneak-ins:** Horde have to sneak into Hall of Thanes under Ironforge; Alliance sneak into the Ruins of Lordaeron. Expect enemy-faction territory on the way in.",
        "**Krol'dok Stronghold (40–55)** is outdoors and changes at night, when cultists start chanting. It's a great place to camp with a group for a while.",
        "**Alcaz Prison (48–53)** is enterable for the first time ever: Defias against naga, in the prison where King Varian was said to have been held.",
        "**Endgame pair:** Blackmaw Hold (55–60, Azshara) and Shaper's Terrace (58–60, Un'Goro) are where you'll gear up for Dec 9.",
    ]),
    5: ("Skyborne for Horde", [
        "**Lore:** Highborne exiles tied to Skywall who allied with the wind spirits and later chose a faction. On Horde they work with the Earthen Ring.",
        "**Classes:** Shaman (Horde-only for Skyborne), plus Warrior, Hunter, Rogue and Druid. Druids get Skyborne-specific forms.",
        "**Racials:** Wind Blessed (2% haste), Walk on Air (90-second cooldown), plus Skysight and Read Leyline, both castable while moving.",
        "**Start:** Zephras Isle, levels 1–12, with its own story before you reach Kalimdor or the Eastern Kingdoms.",
        "**Mounts:** Galestriders from Genn Fairweather at Fairweather Stables on Zephras Isle.",
        "**Requirement:** the Skyborne Heroic Pack or higher.",
    ]),
    4: ("PvP deep dive", [
        "**Darkspear Islands:** 15v15 for levels 30–60, off the coast of Dustwallow Marsh. Four capture points earn steady points, and a center flag scores bonus points when you carry it to a base you hold. First to 2,000 wins.",
        "**Where to queue:** a battlemaster in any capital or the Barrens, or the Darkspear Raiders base at Merchant Coast, which has a portal straight in.",
        "**Darkspear reputation:** earns vendor trinkets, rings, cloaks, weapons and armor. Turn in Marks of Honor for rep, and Exalted unlocks a tabard questline.",
        "**Honor vs. Rank Points:** Honor is spending money (a blue PvP set and an epic set). Rank Points climb your rank. Honor is normalized across battlegrounds, so play the one you enjoy.",
        "**Weekly cap:** Rank Points cap each week and ranks reset each season. A few games every week beats marathons. Weekly tasks give bonus Honor, Rank Points, and sometimes a Legacy Point.",
        "**Rank rewards:** 2 trinket · 3 cloaks · 4 necklace · 5 combat potions · 7 battle standard · 9 epic boots token · 11 mounts · 14 epic weapons.",
    ]),
    3: ("Camping and leveling speed", [
        "**Unlock it early:** do \"The Great Outdoors\" around level 5 and learn Cooking. A Basic Campfire needs Simple Wood and Flint and Tinder.",
        "**Campfires grow with Cooking:** skill 1 holds 3 camp items, 90 holds 5, and 200 holds 10. Each player can add one item, so camp with friends.",
        "**Best items for leveling:** the Leatherworking Camp Tent (1-hour rested-XP buff that survives death) and the Cozy Sleeping Bag (up to +3% XP, and lying on it counts as a rested area while you're logged out).",
        "**How rested XP works:** it doubles kill XP (not quest XP) and builds 5% of a level every 8 hours you're resting, up to 150% of a level.",
        "**Food matters:** Well Fed adds +5% kill XP for about 15 minutes.",
        "**Other camp buffs:** Mining (melee attack power), Skinning (crit), Herbalism (intellect), Engineering (a repair vendor), Fishing (8% stats). None stack with matching class buffs.",
    ]),
    2: ("Gearing toward Dec 9", [
        "**The raids:** Barrow Deeps (10-player) and Hyjal Summit (20-player). Hyjal Summit drops Forever's first legendary weapon.",
        "**Consumables win raids:** an Alchemist and an Herbalist in your group keep everyone in potions, and camps fill in buffs for missing classes.",
        "**Gold plan:** Journeyman Riding is 1,000 gold at 60, and epic mounts are 200 gold each. Start saving while leveling.",
        "**Discounts stack:** Honored with your home faction is 10% off riding and mounts, and the Bartering Legacy talent adds up to 10% off mounts.",
        "**Free mounts:** Warlocks get a level-40 mount quest from Strahad Farsan in Ratchet, and Horde Paladins have their own mount quest.",
        "**Dungeons to farm:** Blackmaw Hold and Shaper's Terrace are the 55–60 dungeons to target first.",
    ]),
    1: ("Launch-night game plan", [
        "**Before 5 PM Central:** sub or game time active, game pre-installed from the Battle.net dropdown, and your reserved name ready.",
        "**Character creation:** PvP ruleset, then Horde, then your character. Make this one before any alt so the faction lock is right.",
        "**Group up immediately:** the game puts groups on the same layer, so invite your friends before you leave the starting area.",
        "**Mob tagging:** only the first player or group to hit a mob gets credit. Grouping is faster than competing.",
        "**Early wins:** set your hearthstone at a hub, take every flight path, learn Cooking for campfires, and pick a gathering profession for gold.",
    ]),
    0: ("First hour checklist", [
        "**Flight paths and hearthstone:** click every flight master you pass; long routes only work if you've unlocked the stops in between.",
        "**Camping:** do \"The Great Outdoors\" around level 5 and learn Cooking.",
        "**Gold:** two gathering professions (like Herbalism and Mining) pay for your level-40 mount.",
        "**Spells:** visit your class trainer every couple of levels. New spells are easy to forget.",
        "**PvP awareness:** on the PvP ruleset, Alliance can attack you anywhere outside cities. Travel with friends in contested zones.",
    ]),
})


# ======================================================================= 1.1.2: "do this → benefit" format
# Pro tips and deep dives lead with an action, then the payoff.
PRO_TIPS.update({
    9: "**Treat your first level 60 as an investment, even on an alt ruleset** → every 1–60 finish unlocks Legacy perks for all your alts, and Legacy is shared across Normal, PvP and Roleplay, so a Normal-ruleset character still powers up your PvP account.",
    8: "**Pick one surname and use it for your whole roster** → names only have to be unique as a first + last pair, so a shared \"family name\" is easier to claim than a rare first name, and guildies can spot your alts at a glance.",
    7: "**Plan to head to Riverglades in your mid-30s** → 150+ fresh quests built for 35–45, right when the classic zones start running dry.",
    6: "**Run dungeons with people within a few levels of you** → nobody's kill XP gets cut by a high-level party member, and quest turn-ins stay full value either way.",
    5: "**Pick Skyborne if you want a Horde Shaman with built-in mobility** → Wind Blessed haste and Walk on Air on a 90-second cooldown, on a class the Horde already loves.",
    4: "**Capture bases first in Darkspear Islands, then run the flag to a base you hold** → steady points from the bases, plus a flag that actually scores instead of getting stuck.",
    3: "**Put down a Cozy Sleeping Bag before you log out in the field** → it counts as a rested area, so you keep earning rested XP overnight.",
    2: "**Start saving gold now, even while leveling** → 1,000g Journeyman Riding at 60 won't stall your gearing for Dec 9 raids.",
    1: "**Quest with friends instead of having a higher-level friend kill things for you** → quest XP isn't reduced by grouping, but kill XP is.",
    0: "**Group up with people hunting the same mobs** → shared tags mean everyone gets credit instead of racing for kills in packed starting zones.",
})

DEEP_DIVES.update({
    9: ("Rulesets in practice", [
        "**Create your character during reservation, not on launch night** → Blizzard can pause new characters for an overloaded faction on PvP (like Season of Discovery did), and that only affects characters that don't exist yet.",
        "**Level an alt on Normal or Roleplay guilt-free** → collections and Legacy points are shared across rulesets (except Hardcore), so that time still powers up your PvP account.",
        "**If a friend \"vanishes\" in a busy city, invite them** → the world is split into layers when crowded, and grouping pulls you onto the same one.",
        "**Treat Hardcore as a free second shot when it arrives** → a Hardcore character that dies can transfer to another ruleset, PvP included, so a death isn't the end of that character.",
        "**Don't count on a transfer to fix a mistake** → there's no cross-ruleset grouping and no character transfers at launch, so double-check the ruleset at character creation.",
    ]),
    8: ("Name reservation checklist", [
        "**Be online at 3 PM Central on Oct 27** → the best names go first, and it's first come, first served. The bot posts a heads-up 30 minutes before.",
        "**Reserve on the account you'll actually play** → the reservation is tied to the Battle.net account that bought the Skyborne pack.",
        "**Spend your 3 names on launch characters** → the 3 are shared across all rulesets, so two PvP names leaves just one for Normal or Roleplay.",
        "**If a first name is taken, change the surname, not the spelling** → names are first + last and unique per region, and \"Grommash Ashfall\" ages better than \"Grommashh.\"",
        "**Use one surname across your roster** → only the full name has to be unique, so a shared \"family name\" is easy to claim and makes your alts recognizable.",
    ]),
    7: ("Zone guide", [
        "**Level a Skyborne on Zephras Isle (1–12)** → a whole starting story of Highborne exiles and wind spirits before you reach the main continents.",
        "**Head to Riverglades around 35** → 150+ new quests on the Eastern Kingdoms coast and the outdoor dungeon Krol'dok Stronghold, so you skip the classic mid-level slump.",
        "**Explore Shen'dralas** → the ruins between Mulgore and Desolace are finally open, with links into Maraudon and Razorfen Downs.",
        "**Set up camp in Mount Hyjal at 60** → it holds Darkwhisper Gorge, the Hyjal Summit raid, and an entrance to Barrow Deeps, so it'll be your endgame home.",
    ]),
    6: ("Dungeon tips", [
        "**Bring one tank, one healer and three damage dealers, and talk before you pull** → a 10-second plan beats a 10-minute run back from the graveyard.",
        "**Group with people within a few levels of you** → higher-level members reduce everyone's kill XP.",
        "**Travel to Hall of Thanes as a group** → Horde have to sneak in under Ironforge, through Alliance territory.",
        "**Camp a night at Krol'dok Stronghold (40–55)** → it's outdoors, it changes at night when the cultists start chanting, and the wide level range keeps it useful for a long time.",
        "**Go see Alcaz Prison (48–53)** → it's enterable for the first time ever, Defias against naga, in the prison where King Varian was said to be held.",
        "**Farm Blackmaw Hold and Shaper's Terrace at 55–60** → they're your best gear sources before Dec 9 raids.",
    ]),
    5: ("Skyborne for Horde", [
        "**Roll Skyborne on Horde if you want Shaman** → Horde Skyborne work with the Earthen Ring, which unlocks Shaman for them.",
        "**Pick Skyborne for a mobile character** → Wind Blessed gives 2% haste, Walk on Air is on a 90-second cooldown, and Skysight and Read Leyline can be cast while moving.",
        "**Try a Skyborne Druid** → you get druid forms built just for the race.",
        "**Buy your mount from Genn Fairweather on Zephras Isle** → Galestriders are sold there, at Fairweather Stables.",
        "**Get the Skyborne Heroic Pack or higher** → it's required to play the race.",
    ]),
    4: ("PvP deep dive", [
        "**Queue from the Darkspear Raiders base at Merchant Coast** → there's a portal straight into Darkspear Islands. Battlemasters in the capitals and the Barrens work too.",
        "**Hold bases, then carry the center flag to one you own** → the four bases earn steady points, the flag scores bonus points, and first to 2,000 wins.",
        "**Turn in Marks of Honor for Darkspear reputation** → it unlocks vendor trinkets, rings, cloaks, weapons and armor, and Exalted opens a tabard questline.",
        "**Play whichever battleground you enjoy** → Honor is normalized across battlegrounds, so there's no penalty for skipping Alterac Valley.",
        "**Play a few games every week instead of marathons** → Rank Points have a weekly cap, so consistency beats grinding. Weekly tasks add bonus Honor, Rank Points and Legacy Points.",
        "**Aim for rank 2 first** → that's the PvP trinket. Later ranks unlock cloaks (3), a necklace (4), mounts (11) and epic weapons (14).",
    ]),
    3: ("Camping and leveling speed", [
        "**Do \"The Great Outdoors\" around level 5 and learn Cooking** → you unlock campfires, the base for every camp buff.",
        "**Level Cooking to 90, then 200** → your campfire holds 5, then 10 camp items instead of 3.",
        "**Camp with friends** → each player adds one item, so a group fire stacks more buffs.",
        "**Grab a Leatherworking Camp Tent** → a 1-hour rested-XP buff that survives death.",
        "**Log out on a Cozy Sleeping Bag** → it counts as a rested area, so you earn rested XP while offline, which doubles your kill XP when you're back.",
        "**Eat Well Fed food before a grind** → +5% kill XP for about 15 minutes.",
    ]),
    2: ("Gearing toward Dec 9", [
        "**Save 1,000 gold by 60** → that's Journeyman Riding, and epic mounts are 200 gold each.",
        "**Get Honored with your home faction** → 10% off riding and mounts. Add the Bartering Legacy talent for up to another 10% off mounts.",
        "**Have an Alchemist and an Herbalist in your group** → steady potions are what win early raids.",
        "**Use camp buffs to cover missing classes** → they don't stack with matching class buffs, but they fill gaps.",
        "**Play Warlock or Horde Paladin for a free mount** → Warlocks get a level-40 quest from Strahad Farsan in Ratchet, and Horde Paladins have their own.",
        "**Chase the Hyjal Summit legendary** → the 20-player raid drops Forever's first legendary weapon.",
    ]),
    1: ("Launch-night game plan", [
        "**Pre-install tonight from the Battle.net game version menu** → you're not stuck downloading at 5 PM.",
        "**Learn First Aid in your first few levels** → bandages from the cloth you're already looting cut your downtime between pulls, on any class.",
        "**Invite your friends before you leave the starting area** → groups land on the same layer, so you can actually see each other.",
        "**Group with strangers hunting the same mobs** → only the first group to tag gets credit, so groups level faster than solo racers.",
        "**Set your hearthstone at a hub, take every flight path, and learn Cooking** → faster travel and campfires from day one.",
    ]),
    0: ("First hour checklist", [
        "**Click every flight master you pass** → long flights only work once you've unlocked the stops in between.",
        "**Do \"The Great Outdoors\" around level 5** → camping and campfire buffs.",
        "**Pick two gathering professions, like Herbalism and Mining** → they pay for your level-40 mount, about 100 gold.",
        "**Visit your class trainer every couple of levels** → new spells are easy to miss.",
        "**Take the starter profession quest** → it hands you Mining, Skinning or Herbalism plus 2 free skill points, a head start on your mount gold.",
    ]),
})


# ------------------------------------------------------------------ 1.5: more depth
# Sources (Oct 27): Blizzard "How PvP Progression in WoW: Forever Works" (Oct 7) and the Legacy System
# article; Warcraft Tavern guides to Professions, Legacy and Camping. Faction-neutral throughout.
# Perk numbers come from beta and can change, so tips name perks without quoting their values.
# 1.8.1 tips pass: every tip reads "**do this** → why", duplicates merged (rested XP, Well Fed, camp buffs,
# recipe tracking, reagent bags), best tips first (Brief shows the first 3, More detail the first 4),
# and faction-specific tips say which faction they're for. No new facts; same sources as above.
TIPS["leveling"] = [
    "**Log out in an inn, a city or on a Cozy Sleeping Bag** → you build rested XP, which doubles your kill XP until it runs out.",
    "**Eat cooked food before a long quest session** → Well Fed gives +5% kill XP for about 15 minutes, on top of camp and sleeping-bag buffs.",
    "**Quest with friends freely** → grouping doesn't reduce the XP you get for turning in quests.",
    "**Skip skull mobs, and move on once things turn gray** → skulls are 5+ levels above you, and mobs or quests 5+ below you give nothing.",
    "**Check the nameplate before you pull** → a gray one means someone else tagged it first, and only they get credit.",
    "**Plan your first Legacy Point for level 25** → that's when most players unlock the Legacy System (Y) and its account-wide perks.",
    "**Need a break from your main? Level another class to 25** → Legacy gives a point for reaching 25, 45 and 60 on every class, and it all feeds your account.",
]
TIPS["pvp"] = [
    "**Play a few battlegrounds every week instead of one huge weekend** → Rank Points have a weekly cap.",
    "**Aim for Rank 2 early** → that's where the PvP trinket unlocks.",
    "**Check the PvP tab on your character pane (C)** → it shows your rank, your Rank Points and which rewards you can buy right now.",
    "**Do your Field of Honor journey tasks every week** → they pay Honor and Rank Points, and three per season also give a Legacy Point.",
    "**Buy the blue Honor set first, then look for Emboldened Seals** → the epic set is your blue piece plus a seal, and seals have rank requirements.",
    "**Queue on a battleground's holiday week** → holiday-week battlegrounds give bonus Honor and Rank Points.",
    "**Play the battleground you actually enjoy** → Honor rates were evened out, so Alterac Valley isn't the only efficient pick anymore.",
    "**Travel in groups through contested zones on the PvP ruleset** → the other faction can attack you anywhere outside cities.",
    "**In Darkspear Islands, carry the center flag to a base your team holds** → that's how you score. The map has four bases and the flag in the middle.",
    "**Head to the Darkspear Raiders base at Merchant Coast in Dustwallow Marsh** → that's where you queue for Darkspear Islands.",
    "**Playing Undead (Horde)? Save Will of the Forsaken for the big one** → it breaks Fear, Charm and Sleep.",
]
TIPS["camping"] = [
    "**Do \"The Great Outdoors\" around level 5 and learn Cooking** → that's what lets you place campfires.",
    "**Pack Flint and Tinder and some Simple Wood** → a Basic Campfire needs only Cooking 1, holds 3 camp items and burns for about 10 minutes.",
    "**Sit (/sit) at the camp for a full minute** → camp buffs only kick in after you've rested there for a minute.",
    "**Camp with friends: add your item, then let them add theirs** → each character places one camp item (then waits an hour), but everyone at the camp shares every buff.",
    "**Pick camp items your group's classes don't already cover** → camp buffs are a bit weaker than class buffs and don't stack with them.",
    "**Bring a Leatherworker's Camp Tent** → its rested XP buff survives death.",
    "**Ask your Engineer for a Repair Bot** → the second-tier Engineering camp item works as a repair vendor in the middle of nowhere.",
]
TIPS["professions"] = [
    "**Do the starting-zone profession quest** → it hands you a book for Mining, Skinning or Herbalism plus 2 free skill points.",
    "**Pick two primary professions, then add Cooking, First Aid and Fishing** → those three don't use up a primary slot.",
    "**Watch the colored arrows on nodes and recipes** → orange, yellow, green and gray show your skill-up chance before you spend materials.",
    "**Track a recipe while you farm (K opens professions)** → it turns into a shopping list in your objectives.",
    "**Grab an early reagent bag** → it gets its own slot, separate from your five normal bags. Small gathering bags drop early, and Tailors can make a 6-slot Linen Reagent Bag.",
    "**Find the special Artisan trainer at level 35** → regular trainers stop at Expert, and Artisan takes you from 225 to 300.",
    "**Think twice before dropping a profession** → unlearning wipes all progress, and you start over from 1.",
    "**Playing Tauren (Horde)? Take Herbalism anyway** → Tauren can pick herbs without it, and get double herbs with it.",
]
TIPS["travel"] = [
    "**Click every flight master you pass** → long routes need the stops in between.",
    "**Playing a Shaman or Druid? Use your travel form** → you get it well before the level-40 mount.",
    "**Make friends with a Mage or Warlock** → otherwise crossing continents means zeppelins or boats.",
    "**Pick up Frequent Flier in your Legacy tree if you fly a lot** → it makes flight paths cheaper and faster.",
    "**Take The Quick and the Dead if you die a lot** → your ghost runs faster, and your helpful spells cost nothing for a minute after you come back.",
]
TIPS["gold"] = [
    "**Pick two gathering professions while leveling** → you sell what you pick up along the way, and that pays for your mount at 40.",
    "**Sell your gray items to any vendor** → it's free gold, and it clears bag space.",
    "**Take Reagent Economy in the Legacy Resourcefulness tree** → your class abilities stop needing vendor reagents, which adds up fast on reagent-heavy classes.",
    "**Look at Bartering in the Legacy Professions tree** → it lowers vendor prices on everything you buy.",
    "**Use an Engineer's Reagent Bot at camp** → you can buy reagents and sell loot without riding back to town.",
]
TIPS["legacy"] = [
    "**Open the Legacy System with Y** → it unlocks with your first Legacy Point, usually at level 25. Hitting 150 in a crafting profession or exploring the whole map works too.",
    "**Spend points with your main in mind** → each character can spend up to 16 points at launch across three trees: Professions, Adventure and Resourcefulness.",
    "**Clear one dungeon from each difficulty group** → finishing a Novice, an Experienced and a Master dungeon is worth a Legacy Point each.",
    "**Level a crafting profession to 150, 225 and 300** → each milestone is a Legacy Point, and there are 18 to collect across six crafting professions.",
    "**Grab Talented in the Adventure tree on new alts** → your talent points start arriving before level 10.",
    "**Pick Well Rested if you play in short sessions** → you build rested XP faster and can bank more of it.",
    "**Planning to try Hardcore when it arrives? Earn some points there** → Hardcore points count on every ruleset, but points from Normal, PvP or Roleplay don't carry into Hardcore.",
]

DEEP_DIVES["legacy"] = ("The Legacy System", [
    "**What it is:** Forever's replacement for achievements. 65 challenges, each worth one Legacy Point, earned across your whole Battle.net account.",
    "**Unlock:** your first point, usually at level 25. 150 in a crafting profession or exploring the entire world map also counts. Open it with **Y**.",
    "**Spending:** each character can spend up to 16 points at launch across three trees: Professions, Adventure and Resourcefulness.",
    "**Where points come from:** Classes 27 (levels 25, 45 and 60 on all nine) · Tradeskills 18 · PvP 12 · Dungeons 3 · Raids 3 · Adventure 2.",
    "**Rewards:** points also unlock account-wide cosmetics. At launch: a Replica Ironforge Air Rifle toy, a Spectral Bear Cub pet, a Spectral Bear Tabard and the Reins of the Spectral Bear mount.",
    "**Hardcore:** points earned there count everywhere, but not the other way around. PvP challenges are swapped for Hardcore-only ones.",
])
DEEP_DIVES["camping"] = ("Camping 101", [
    "**Light a fire:** Cooking plus Flint and Tinder and wood. Basic Campfire (Cooking 1, 3 items) · Journeyman (Cooking 140, 5 items) · Expert (Cooking 220, 10 items). Each burns for about 10 minutes.",
    "**Add items:** every profession crafts three camp items. Each character can place one per camp (then waits an hour), and anyone can add to the same fire.",
    "**Get the buff:** sit within range for at least a minute. Buffs from different items combine into one Camp Benefits buff.",
    "**What they do:** stat buffs a bit weaker than class buffs (they don't stack with them), plus utility: the Leatherworking Camp Tent gives rested XP, Engineering bots sell reagents and repair, and Herbalism and Mining can grow nodes.",
    "**Cozy Sleeping Bag:** earned through a quest chain across both continents. It stacks with camp buffs, and you can eat cooked food on it for even more XP.",
])
POST_LAUNCH_TOPICS += ["legacy", "camping"]

DID_YOU_KNOW += [
    ("new", "Forever replaces achievements with the Legacy System: 65 challenges, each worth one account-wide point."),
    ("vet", "PvP Rank 11 unlocks mounts, and Rank 14 unlocks epic weapons."),
    ("vet", "Forever adds over 600 new recipes, mostly using materials from the original game."),
    ("new", "Every profession in Forever has its own crafting menu, even the gathering ones."),
    ("vet", "You can link a profession in chat to show off every recipe you know and what it needs."),
    ("new", "Exploring the entire world map earns a Legacy Point."),
    ("vet", "Shamans get three PvP gear sets in Forever: healer, melee and caster."),
    ("new", "Several players can add items to the same campfire, and everyone resting there gets every buff."),
    ("vet", "Each profession's top camp item is a full workstation, like the Fishing Hut or the Master Forge."),
]


# ------------------------------------------------------------------ 1.5: /dungeons
# Source: Blizzard's dungeon preview (news.blizzard.com/en-us/article/24301455), Oct 2026.
# (name, levels, where, note)
DUNGEONS = [
    ("Hall of Thanes", "13–18", "Beneath Ironforge, Dun Morogh",
     "Alliance walk in from their capital. Horde groups have to travel through Alliance territory."),
    ("Ruins of Lordaeron", "15–20", "The ruined city above the Undercity, Tirisfal Glades",
     "Horde walk in from the Undercity. Alliance groups have to travel through Horde territory."),
    ("Excavation Site", "24–29", "Whelgar's Excavation, Wetlands (near Thelgen Rock and Dun Algaz)",
     "Titan constructs guard a time-frozen dig site."),
    ("City of Dalaran", "28–33", "Alterac Mountains, in through the sewers",
     "Start with the quest from Emissary Jacques in Southshore (Alliance) or Magus Wordeen Voidglare in Tarren Mill (Horde)."),
    ("The Drowned City", "35–40", "Off the Stranglethorn Vale coast, west of Grom'gol",
     "Dive underwater to find the entrance. Bring water breathing if you have it."),
    ("Krol'dok Stronghold", "40–45", "Riverglades",
     "An ogre fortress kidnapping travelers. Pairs well with questing in Riverglades."),
    ("Alcaz Prison", "48–53", "Alcaz Island, off Dustwallow Marsh",
     "The Defias and naga fight over the prison, and some famous prisoners are inside."),
    ("Blackmaw Hold", "55–60", "Behind a sealed gate in Azshara", "A furbolg city falling to corruption."),
    ("Shaper's Terrace", "58–60", "Northern hills of Un'Goro Crater",
     "Gather Un'Goro power crystals before you go; the consoles inside use them."),
]
RAIDS_INFO = "**Raids open Dec 9:** Barrow Deeps (10 players) and Hyjal Summit (20 players)."


# ------------------------------------------------------------------ 1.5: /addons
# Sources (checked Oct 27): Kami-Labs' Forever addon directory (data as of Oct 20, beta build 1.60.1),
# Gfinity's CurseForge picks, AllThingsHow's manual install guide. Forever runs on the modern client,
# so Classic versions of addons don't load, and the combat log is closed to addons.
ADDON_PICKS = [
    ("Questie", "Quest givers, objectives and turn-ins on your map. Use the Forever version: it knows the new zones."),
    ("Leatrix Plus", "Dozens of small comforts: auto-repair, auto-sell grays, more camera zoom and more. Get the Forever edition."),
    ("OpenMap or Leatrix Maps", "A better world map. Pick one, not both: map addons conflict."),
    ("Baganator or Bagnon", "All your bags in one window, with search."),
    ("Auctionator", "Makes the Auction House usable. Pick this over TradeSkillMaster for now."),
    ("Deadly Boss Mods", "Boss warnings and timers, with modules for Forever's new dungeons."),
    ("Details!", "Damage and healing meter. It shows Blizzard's own numbers, since addons can't read the combat log."),
    ("BugSack", "Catches addon errors quietly instead of popping them up mid-fight."),
]
ADDON_BUILTIN = ("**Already in the game, no addon needed:** Edit Mode (move and resize your UI), the Cooldown Manager "
                 "(turn it on under Options → Gameplay Enhancements), a built-in damage meter and click casting.")
ADDON_AVOID = [
    "**WeakAuras** doesn't support Forever's client. The built-in Cooldown Manager covers most of what it did.",
    "**Classic versions of addons won't load.** Forever runs on the modern client, so grab the Forever or retail version.",
    "**Combat-log addons** (most old damage meters, OmniCC-style cooldown trackers, arena frames) can't read combat data in Forever.",
    "Run only **one** world map addon and **one** minimap addon at a time.",
]
ADDON_INSTALL = [
    "**Find your game folder:** open Battle.net, pick WoW: Forever, click the gear next to Play, then **Show in Explorer** (Finder on Mac).",
    "**Open Interface → AddOns** inside the Forever game folder. Create both folders if they're missing.",
    "**Download the addon** from CurseForge or Wago (choose *Download file* if you're not using an app), and unzip it.",
    "**Copy the addon folder** (not the zip) into AddOns, so you end up with `...\\Interface\\AddOns\\Questie`.",
    "**In game:** press Esc → AddOns, tick the addon, then click Reload UI. If it still doesn't show, restart the game.",
    "**Using the CurseForge app?** Pick World of Warcraft, then the Forever install if it's listed. If not, use the steps above.",
]


# 1.6.1: livelier did-you-knows: lore, history and dungeon trivia. Dungeon facts are from Blizzard's
# dungeon preview; lore is long-standing Warcraft canon. Also retire a few that just restate tips.
_DULL = {
    "Several players can add items to the same campfire, and everyone resting there gets every buff.",
    "Every profession in Forever has its own crafting menu, even the gathering ones.",
    "Controllers are officially supported in Forever.",
    "Honor gains are normalized across battlegrounds, so there's no reason to farm only Alterac Valley.",
}
DID_YOU_KNOW[:] = [x for x in DID_YOU_KNOW if x[1] not in _DULL]
DID_YOU_KNOW += [
    ("new", "In the original game, King Varian Wrynn was missing for years. In Forever, you'll find him as a prisoner in the new Alcaz Prison dungeon."),
    ("new", "Dalaran sat sealed under a violet dome for the entire original game. Forever finally lets you inside, through the sewers."),
    ("vet", "The Ruins of Lordaeron, the empty courtyard above the Undercity, are a full dungeon in Forever as the Forsaken try to reclaim them."),
    ("vet", "Hall of Thanes is the tomb of Ironforge's dwarven kings, and Dark Iron intruders have broken in."),
    ("new", "The Drowned City has no door: you dive underwater off the Stranglethorn coast, west of Grom'gol, to find it."),
    ("vet", "Shaper's Terrace is a titan facility in Un'Goro, and its consoles run on power crystals you gather in the crater."),
    ("vet", "Blackmaw Hold is a furbolg city hidden behind a sealed gate in Azshara, and the path inside may lead even deeper."),
    ("new", "Mount Hyjal was blocked off in the original game. Players spent years sneaking in through map exploits just to look around. In Forever, it's the endgame zone."),
    ("vet", "Krol'dok Stronghold's ogres kidnap travelers on the road, and the chanting only starts after dark."),
    ("new", "Original WoW launched on Nov 23, 2004. Forever launches on Nov 4, 2026, almost 22 years later."),
    ("vet", "Forever's 9 new dungeons span levels 13 to 60, so there's a new one to try at almost every stage of leveling."),
    ("vet", "Dalaran's starting quest depends on your faction: Southshore for Alliance, Tarren Mill for Horde. Those two towns were the site of a famous world PvP rivalry in the original game."),
    ("new", "You can earn Legacy Points without ever fighting: maxing crafting professions and exploring the whole world map both count."),
    ("vet", "One of the account-wide Legacy rewards is a mount: the Reins of the Spectral Bear."),
    ("vet", "Shen'dralas, the Highborne you met inside Dire Maul, finally get their own zone in Forever."),
]


# ------------------------------------------------------------------ 1.9: what's new
# Player-facing release notes: /whatsnew, the 🆕 line in the next post after a release, and the
# What's new page (foreversherpa.github.io/whatsnew.html). Newest first. "line" is the one-liner a
# server sees in its next post; None means the release isn't worth interrupting anyone for.
# "internal": True keeps a behind-the-scenes release out of /whatsnew and the What's new page.
WHATSNEW_URL = SITE_URL + "/whatsnew.html"
RELEASE_NOTES = [
    {"version": "1.11.0", "date": "2026-11-04", "title": "Launch night",
     "line": None,
     "notes": ["A short \"servers are open\" message posts once in each server when WoW: Forever goes live. No pings."]},
    {"version": "1.10.5", "date": "2026-10-30", "title": "Owner setup alerts",
     "line": None, "internal": True,
     "notes": ["Behind the scenes: the owner also gets a DM when a server finishes setup."]},
    {"version": "1.10.4", "date": "2026-10-30", "title": "A new look",
     "line": None,
     "notes": ["Forever Sherpa has a new profile photo and banner."]},
    {"version": "1.10.3", "date": "2026-10-30", "title": "/postnow logging",
     "line": None, "internal": True,
     "notes": ["Behind the scenes: `/postnow` logs what it did."]},
    {"version": "1.10.2", "date": "2026-10-30", "title": "Owner alerts fix",
     "line": None, "internal": True,
     "notes": ["Behind the scenes: owner join and leave DMs now send."]},
    {"version": "1.10.1", "date": "2026-10-30", "title": "Internal releases stay out of What's new",
     "line": None, "internal": True,
     "notes": [
         "Behind the scenes: releases marked internal no longer show in `/whatsnew` or on the What's new page.",
     ]},
    {"version": "1.10.0", "date": "2026-10-30", "title": "Owner alerts",
     "line": None, "internal": True,
     "notes": [
         "Behind the scenes: the bot's owner now gets a DM when a server adds or removes the bot.",
     ]},
    {"version": "1.9.1", "date": "2026-10-30", "title": "Facts check",
     "line": None,
     "notes": [
         "Rulesets now include Roleplay-PvP, which Blizzard added for launch.",
         "Skyborne Wind Blessed is 2% haste after Blizzard's Oct 26 racial tuning (was 3%).",
     ]},
    {"version": "1.9.0", "date": "2026-10-30", "title": "What's new, right in your posts",
     "line": None,
     "notes": [
         "After an update, the next post in your server gets one short 🆕 line about what changed. Admins can turn it off with `/updates`.",
         "`/whatsnew` shows recent changes any time, and there's a What's new page on the website.",
     ]},
    {"version": "1.8.1", "date": "2026-10-29", "title": "Setup that understands you",
     "line": "admins can turn clips off with `/clips`, and `/setup` now understands time zones like \"central\" or \"Helsinki\".",
     "notes": [
         "`/setup` understands time zones the way people type them: `central`, `CST`, `New York`, `UK`, `CET`, `Helsinki`, `UTC-6`. It also suggests matches as you type.",
         "Post times can be written as `noon`, `7p`, `7:30 pm` or `19.30`.",
         "If something still can't be read, the bot tells you what it got and what would work, and changes nothing.",
         "Admin commands used before setup now offer the one-click 📍 Post here button.",
         "Every tip was rewritten to say what to do and why, with duplicates merged and the best ones first.",
     ]},
    {"version": "1.8.0", "date": "2026-10-29", "title": "Turn clips off",
     "line": "Admins can turn the Twitch clips off with `/clips`.",
     "notes": [
         "New `/clips` for admins: turn the Twitch clips under each post off, or back on.",
         "The welcome card lists the settings that make the post fit your server.",
     ]},
    {"version": "1.7.1", "date": "2026-10-28", "title": "A gentler first day",
     "line": None,
     "notes": [
         "Setting up after today's post time no longer sends a late catch-up post. You get a short first look instead, and the full post starts on schedule.",
     ]},
    {"version": "1.7.0", "date": "2026-10-28", "title": "One-click setup",
     "line": None,
     "notes": [
         "When the bot joins a server it says hello with a 📍 Post here button. One click sets up the daily post.",
         "`/setup` uses the channel you're in if you don't pick one.",
         "`/help` shows a ⭐ Start here banner until the server is set up.",
     ]},
    {"version": "1.6.0", "date": "2026-10-27", "title": "Outage alerts and better clips",
     "line": None,
     "notes": [
         "Blizzard's Forever outage, maintenance and fix updates can post in your channel. Admins control it with `/statusalerts`.",
         "Clips: never two from the same streamer, no near-duplicates, and no clips under 20 views.",
         "Fifteen new did-you-knows, and no more repeats inside one post.",
     ]},
    {"version": "1.5.0", "date": "2026-10-27", "title": "More depth",
     "line": None,
     "notes": [
         "Forty new tips, plus new gold and Legacy topics in `/tips`.",
         "New `/dungeons` (Forever's nine new dungeons) and `/addons` (starter picks that work on Forever).",
         "Alliance race lists and racial tips on class cards.",
     ]},
]


def public_notes() -> list[dict]:
    """Releases players see in /whatsnew and on the What's new page (newest first)."""
    return [r for r in RELEASE_NOTES if not r.get("internal")]


def latest_line_since(version: str | None) -> tuple[str, str] | None:
    """(latest version, line) for the newest announced release after `version`, or None."""
    for r in RELEASE_NOTES:
        if version is not None and _vkey(r["version"]) <= _vkey(version):
            return None
        if r["line"]:
            return RELEASE_NOTES[0]["version"], r["line"]
    return None


def _vkey(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))
