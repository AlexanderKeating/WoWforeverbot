"""
Everything the bot says about WoW: Forever lives here. Edit freely.

Compiled Oct 24, 2026 from Blizzard posts and coverage (Warcraft Tavern, Icy Veins,
Wowhead, Kami Labs, timesaver.gg, Raider.IO bracket data).

Forever is NOT retail and NOT Classic:
  - no realms: one mega-realm per ruleset (Normal / PvP / RP; Hardcore later) per region
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
EVENT_PINGS = [
    ("2026-10-27T19:30:00+00:00", "names-30m", "📛 **Name reservation opens in 30 minutes** (1 PM Pacific / 3 PM Central). "
     "3 names total across all rulesets. Have your first + last name ideas ready, and on PvP make your **Horde** character first."),
    ("2026-10-27T20:00:00+00:00", "names-open", "📛 **Name reservation is open now.** First come, first served. Go get your name."),
    ("2026-11-03T16:00:00+00:00", "names-last", "⏰ **Last day of name reservation.** If you haven't locked in your name yet, today's the day."),
]

# Shown at the top of the daily post on that date.
TODAY_CALLOUTS = {
    "2026-10-26": "📛 **Name reservation opens tomorrow at 1 PM Pacific / 3 PM Central.** 3 names total across all rulesets. Pick your first + last name ideas tonight (`/faq` has the rules).",
    "2026-10-27": "📛 **Name reservation opens today at 1 PM Pacific / 3 PM Central.** Skyborne pack owners can reserve **3 names total** across all rulesets, through Nov 3. On the PvP ruleset, make your Horde character first: your account gets locked to one faction there.",
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
         "new": "You don't pick a server. You pick a ruleset: Normal, PvP or Roleplay. Everyone on the same ruleset in your region plays in one big shared world. We're on **PvP, Horde**.",
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

NEWBIE_TIPS = [
    "On the PvP ruleset, players from the other faction can attack you out in the world. Quest in pairs in contested zones.",
    "Your hearthstone takes you back to the inn you set it at. Set it somewhere useful before a long trip.",
    "Train new spells at your class trainer every couple of levels. It's easy to forget.",
    "Pick up two gathering professions early (like Herbalism and Mining). They pay for your first mount.",
    "Out of mana or health? Eat and drink between fights instead of pushing on.",
    "Dungeons need a tank, a healer and three damage dealers. If you're new, ask a guildie to run one with you.",
    "Elite mobs (gold dragon on the portrait) are meant for groups. Don't solo them early.",
    "Talents unlock at level 10. Each class has three trees; you don't have to copy a guide, but it helps.",
    "Lost in a city? Ask any guard. They'll mark the bank, trainers and more on your map.",
    "No mount until level 40. Save about 100 gold for riding plus your first mount.",
    "Stop clicking your abilities. Put them on keys around WASD. /keybinds shows you how.",
    "Battlegrounds give Honor whether you win or lose, but winning gives more.",
    "Transmog is opt-in. If someone's gear looks weird, they might just have it on.",
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
        "**Normal / PvP / Roleplay** at launch; **Hardcore** later. Each is one big world per region, split into layers when busy.",
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
TIPS = {
    "basics": NEWBIE_TIPS,
    "leveling": [
        "Rested XP doubles kill XP. It builds while you're logged out in an inn, city or on a Cozy Sleeping Bag.",
        "Mobs with a skull are 5+ levels above you. Mobs and quests 5+ below give nothing.",
        "Only the first player or group to tag a mob gets credit. A gray nameplate means it's taken.",
        "Cooking food with Well Fed gives +5% kill XP for about 15 minutes.",
        "Quest turn-in XP isn't reduced by grouping, so quest with friends freely.",
    ],
    "pvp": [
        "On the PvP ruleset, Alliance can attack you anywhere outside cities. Travel in groups in contested zones.",
        "Rank Points have a weekly cap. A few BGs every week beats one huge weekend.",
        "Darkspear Islands: four bases and a center flag. Score the flag at a base your team holds.",
        "Queue Darkspear Islands from the Darkspear Raiders base at Merchant Coast, Dustwallow Marsh.",
        "Undead's Will of the Forsaken breaks Fear, Charm and Sleep. Save it for the big one.",
    ],
    "camping": [
        "Do \"The Great Outdoors\" around level 5 and learn Cooking to place campfires.",
        "Each player can add one item per campfire, so camp with friends for more buffs.",
        "Camp buffs don't stack with matching class buffs.",
        "The Leatherworking Camp Tent gives a rested XP buff that survives death.",
    ],
    "professions": [
        "You get two primary professions plus Cooking, First Aid and Fishing.",
        "Professions open in their own window (K). Track recipes like a shopping list.",
        "Reagent bags get their own bag slot, separate from your five normal bags.",
        "Tauren can pick herbs without Herbalism, and get double herbs with it.",
    ],
    "travel": [
        "Click every flight master you pass; long routes need the stops in between.",
        "Ask a guard for directions to the bank, trainers and more.",
        "Shamans and Druids get travel forms before the level-40 mount.",
        "Crossing continents means zeppelins or boats unless a Mage or Warlock helps.",
    ],
}

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
