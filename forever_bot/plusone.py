"""
Plus One mode (1.3): for people whose partner, friend or roommate talked them into WoW: Forever.

Tone: warm, never condescending, a light wink. Assume a smart adult who has simply never played.
Accuracy: Forever-specific claims only where content.py already has them. Everything else here is
basic how-the-game-works (controls, deaths, groups, slang), which Forever inherits from the original.

  /draggedalong        hub: survival kit + buttons
  /whatdoesthatmean    glossary lookup
  "Plain words" level  /mysettings option; private replies drop the veteran parts and explain jargon
"""
import re

PLUS_COLOR = 0xE89AC7

# ------------------------------------------------------------------ glossary
# term -> (plain meaning, optional "you'll hear it like" example)
GLOSSARY = {
    "aggro": ("When a monster decides you're its target. \"I pulled aggro\" means it's chasing me now.", "Sorry, I pulled aggro."),
    "tank": ("The sturdy player who keeps monsters hitting them instead of everyone else. Usually a Warrior, Druid in bear form or Paladin.", "Wait for the tank to go first."),
    "healer": ("The player keeping everyone's health up. Priests, Shamans, Druids and Paladins can heal.", "Healer's out of mana, hold up."),
    "dps": ("Short for damage per second, and also what we call the players whose job is to deal damage.", "We need one more DPS."),
    "add": ("An extra monster that joined a fight nobody invited it to.", "Add on the left!"),
    "pull": ("Starting a fight on purpose, usually by attacking from a distance so monsters come to you.", "I'll pull the next group."),
    "trash": ("The regular monsters between bosses in a dungeon.", "Just trash until the next boss."),
    "boss": ("The big named monster at the end of an area. Best loot, hardest fight.", None),
    "mob": ("Any monster or computer-controlled enemy. From an old word for \"mobile object\".", "Kill ten of those mobs."),
    "elite": ("A monster with a gold dragon around its portrait. Built for groups, so don't fight one alone early on.", None),
    "wipe": ("Everyone in the group died. It happens to every group, including good ones.", "That's a wipe, run back."),
    "rez": ("Short for resurrect: bringing a dead player back. Healers can do it out of combat.", "Can I get a rez?"),
    "corpse run": ("When you die, you appear as a ghost at a graveyard and run back to your body to come back to life.", None),
    "spirit healer": ("The angel at the graveyard. She'll revive you on the spot, but your gear gets damaged and you're weakened for a while. Running back to your body is usually better.", None),
    "buff": ("A helpful effect on you, like extra stamina from a friend's spell. Also: when the developers make something stronger.", "Can I get a buff?"),
    "debuff": ("A harmful effect on you, like poison or a slow.", None),
    "dot": ("Damage over time: a spell that keeps hurting its target for several seconds.", None),
    "hot": ("Heal over time: a spell that keeps healing for several seconds.", None),
    "proc": ("When something has a chance to trigger and it does. \"My sword procced\" means its bonus effect just went off.", None),
    "crit": ("Critical hit: a lucky hit for extra damage or healing.", None),
    "cooldown": ("The waiting time before you can use an ability again. Also written CD.", "Shield's on cooldown."),
    "cd": ("Cooldown: the waiting time before an ability can be used again.", "Shield's on CD."),
    "cc": ("Crowd control: anything that stops an enemy from acting for a bit, like a stun, sheep or fear.", "CC the one on the left."),
    "aoe": ("Area of effect: an attack or heal that hits everyone in an area instead of one target.", "Stand out of the AoE."),
    "kite": ("Staying out of reach while you keep attacking, so an enemy chases you and never catches you.", None),
    "los": ("Line of sight. If a wall or pillar is between you, spells can't reach. Breaking LoS is a classic escape trick.", None),
    "oom": ("Out of mana. Casters need to stop and drink.", "OOM, give me 20 seconds."),
    "mana": ("The blue bar casters spend on spells. Refill it by drinking between fights.", None),
    "rage": ("The Warrior's red bar. It builds when you hit things and when things hit you.", None),
    "energy": ("The Rogue's yellow bar. It refills quickly on its own.", None),
    "xp": ("Experience points. Fill the bar to level up.", None),
    "rested": ("Bonus experience you earn while logged out, especially if you log out at an inn or in a city. Your XP bar turns blue.", None),
    "hearth": ("Your hearthstone: a stone that teleports you to the inn you set it at. Has a long cooldown.", "I'll hearth and meet you in town."),
    "inn": ("Where you set your hearthstone and the best place to log out for bonus XP.", None),
    "quest": ("A task from a character with a yellow ! over their head. A yellow ? means it's ready to turn in.", None),
    "grind": ("Doing the same thing over and over for XP, gold or items.", None),
    "loot": ("Items and gold you collect from defeated monsters. Right-click (or interact with) a body that sparkles.", None),
    "need": ("In a group, roll Need on an item if your character will actually use it.", None),
    "greed": ("Roll Greed if you just want to sell it. Need beats Greed.", None),
    "ninja": ("Someone who takes loot they shouldn't, like rolling Need on something they can't use.", None),
    "soulbound": ("An item that's now permanently yours and can't be traded. Picking up or equipping some items binds them.", None),
    "boe": ("Bind on equip: tradeable until someone puts it on. These sell well.", None),
    "vendor": ("A shopkeeper character. Gray items are junk: sell them to any vendor.", None),
    "ah": ("Auction House: the player marketplace in big cities.", None),
    "mats": ("Materials for crafting, like ore, herbs or cloth.", None),
    "dungeon": ("A private area for a group of five, with its own monsters, bosses and loot.", None),
    "instance": ("Another word for a dungeon or raid: a private copy just for your group.", None),
    "raid": ("A big group content area, with 20 or 40 players depending on the raid.", None),
    "bg": ("Battleground: an organized PvP match between teams. You earn Honor for playing.", None),
    "honor": ("Points you earn from PvP. Winning gives more, but you earn some either way.", None),
    "pvp": ("Player versus player: fighting other players instead of monsters.", None),
    "pve": ("Player versus environment: fighting monsters and the game world.", None),
    "gank": ("Getting attacked by another player (or several) who clearly had the advantage. Annoying, very normal on PvP servers, and never your fault.", "Got ganked on the road again."),
    "layer": ("A copy of the same zone. When it's crowded, the game splits players into layers. Join a group to end up in your partner's layer.", None),
    "lfg": ("Looking for group.", "LFG for the next dungeon?"),
    "inc": ("Incoming: enemies are on their way.", "Inc from the south!"),
    "afk": ("Away from keyboard.", None),
    "brb": ("Be right back.", None),
    "gg": ("Good game.", None),
    "alt": ("A second (or fifth) character on the same account. Your first or favorite is your main.", None),
    "main": ("The character you play the most.", None),
    "spec": ("Your specialization: which of your class's three talent trees you've put most points into.", None),
    "talents": ("Points you start earning at level 10 to customize your class.", None),
    "nerf": ("When the developers make something weaker.", None),
    "meta": ("Whatever most people think is the strongest way to play right now.", None),
    "zug zug": ("Orc for \"yes, sure, okay\". You will hear it a lot on the Horde, and you are allowed to say it back.", "Ready? Zug zug."),
    "lok'tar ogar": ("Orcish: \"victory or death\". A Horde battle cry.", None),
    "for the horde": ("The Horde motto. Shouted before charging into something questionable.", None),
}

ALIASES = {
    "cds": "cooldown", "cooldowns": "cooldown", "rezz": "rez", "res": "rez", "ress": "rez", "resurrect": "rez",
    "dots": "dot", "hots": "hot", "procs": "proc", "procced": "proc", "adds": "add", "pulling": "pull",
    "ganked": "gank", "ganking": "gank", "wiped": "wipe", "mobs": "mob", "buffs": "buff", "debuffs": "debuff",
    "hearthstone": "hearth", "bgs": "bg", "battleground": "bg", "auction house": "ah", "out of mana": "oom",
    "zugzug": "zug zug", "loktar": "lok'tar ogar", "lok tar": "lok'tar ogar", "lfm": "lfg", "boes": "boe",
    "kiting": "kite", "elites": "elite", "crits": "crit", "line of sight": "los", "tanks": "tank", "healers": "healer",
    "rested xp": "rested", "instances": "instance", "dungeons": "dungeon", "raids": "raid", "talent": "talents",
}

# The ones you'll hear in the first week, in roughly the order you'll hear them
STARTER_TERMS = ["quest", "mob", "aggro", "pull", "add", "tank", "healer", "dps", "oom", "rez",
                 "corpse run", "hearth", "rested", "gank", "layer", "zug zug"]


def _key(s: str) -> str:
    s = re.sub(r"[^a-z' ]+", " ", (s or "").lower()).strip()
    s = re.sub(r"\s+", " ", s)
    return ALIASES.get(s, s)


def lookup(term: str) -> tuple[str | None, list[str]]:
    """(matched key or None, close suggestions)."""
    k = _key(term)
    if k in GLOSSARY:
        return k, []
    near = [g for g in GLOSSARY if k and (k in g or g in k or g.startswith(k[:3]))][:5]
    return None, near


def glossary_choices(current: str, limit: int = 25) -> list[str]:
    c = _key(current)
    names = sorted(GLOSSARY)
    if not c:
        return STARTER_TERMS[:limit]
    starts = [n for n in names if n.startswith(c)]
    contains = [n for n in names if c in n and n not in starts]
    return (starts + contains)[:limit]


def _display(term: str) -> str:
    return term.upper() if len(term) <= 3 and term not in ("add", "mob", "inn", "rez", "hot", "dot") else term.title()


def glossary_embed(term: str | None) -> dict:
    if not term:
        lines = [f"**{_display(t)}** · {GLOSSARY[t][0]}" for t in STARTER_TERMS[:12]]
        return {"title": "📖 What does that mean?", "color": PLUS_COLOR,
                "description": "The words you'll hear in your first week:\n\n" + "\n".join(lines)
                               + "\n\n-# Look up any word with `/whatdoesthatmean term`. There are "
                               + f"{len(GLOSSARY)} in here, from aggro to zug zug."}
    key, near = lookup(term)
    if not key:
        more = (" Maybe: " + ", ".join(f"`{n}`" for n in near) + "?") if near else ""
        return {"title": "📖 Hmm, not in my book", "color": PLUS_COLOR,
                "description": f"I don't have **{term[:40]}** yet.{more}\n-# If your partner said it with total confidence, "
                               "it's probably slang. Asking them is allowed, and it's a little bit romantic."}
    meaning, example = GLOSSARY[key]
    desc = meaning + (f"\n\n> *\"{example}\"*" if example else "")
    return {"title": f"📖 {_display(key)}", "color": PLUS_COLOR, "description": desc,
            "footer": {"text": "Plus One mode · /draggedalong for the survival kit"}}


# ------------------------------------------------------------------ plain-words replies
# Short glosses added the first time a term shows up in a reply. Case-sensitive for acronyms.
_SWAPS = [
    (r"\bDPS\b", "damage dealers"), (r"\bAoE\b", "hits everything nearby"),
    (r"\bCC\b", "stuns and other ways to stop an enemy"), (r"\bkite\b", "stay out of reach while attacking"),
    (r"\baggro\b", "the monster's attention"), (r"\bprocs?\b", "a bonus that randomly triggers"),
    (r"\bthreat\b", "how much a monster wants to hit you"), (r"\bcooldown\b", "wait time before reuse"),
    (r"\belites?\b", "gold-dragon monsters made for groups"), (r"\bpulls?\b", "starting a fight"),
    (r"\bLegacy\b", "account-wide unlocks"), (r"\bHonor\b", "PvP points"),
    (r"\bspec\b", "talent focus"), (r"\bOOM\b", "out of mana"), (r"\bcrit\b", "a lucky big hit"),
    (r"\bbattlegrounds?\b", "team PvP match"), (r"\blayer(ing)?\b", "a copy of the zone"),
    (r"\bDoTs?\b", "damage over time"), (r"\bBGs?\b", "team PvP matches"), (r"\bgank(ed|s)?\b", "jumped by another player"), (r"\bHoT\b", "heal over time"), (r"\bRested\b", "bonus XP"),
]
_SWAPS = [(re.compile(p), g) for p, g in _SWAPS]  # (pattern, gloss): "word" -> "word (gloss)"
_PROTECT = re.compile(r"(https?://\S+|\[[^\]]*\]\([^)]*\)|`[^`]*`|<[^>]+>)")
_VET_MARKERS = ("🧙", "⭐ Talents", "Veteran", "For veterans")


def plain_text(text: str, used: set) -> str:
    if not text:
        return text
    parts = _PROTECT.split(text)
    for i in range(0, len(parts), 2):  # even indexes are unprotected text
        seg = parts[i]
        for rx, gloss in _SWAPS:
            if gloss in used:
                continue
            m = rx.search(seg)
            if m and "(" not in seg[m.end():m.end() + 2]:
                seg = seg[:m.end()] + f" ({gloss})" + seg[m.end():]
                used.add(gloss)
        parts[i] = seg
    return "".join(parts)


def plainify(embed: dict) -> dict:
    """Plain-words version of any private reply: drop veteran sections, explain jargon once."""
    if not embed:
        return embed
    e = dict(embed)
    used: set = set()
    if e.get("description"):
        paras = [p for p in e["description"].split("\n\n") if not p.lstrip().startswith(_VET_MARKERS)]
        e["description"] = plain_text("\n\n".join(paras), used)[:4000]
    fields = []
    for f in e.get("fields", []) or []:
        if any(m in (f.get("name") or "") for m in _VET_MARKERS):
            continue
        fields.append({**f, "value": plain_text(f.get("value", ""), used)[:1024]})
    if "fields" in e:
        e["fields"] = fields
    e["footer"] = {"text": "Detail: Plain words · /whatdoesthatmean explains any term · change with /mysettings"}
    return e


# ------------------------------------------------------------------ survival kit
def survival_kit_embed() -> dict:
    return {
        "title": "🧭 The Plus One survival kit",
        "color": PLUS_COLOR,
        "description": (
            "So someone you love said \"it'll be fun, I'll show you everything.\" Good news: it actually is. "
            "Here's everything you need for night one, and nothing you don't."),
        "fields": [
            {"name": "🎮 Moving around", "value": (
                "**W A S D** to walk. **Hold right-click** and move the mouse to steer. "
                "**Space** jumps (you'll do this constantly for no reason, everyone does).\n"
                "Prefer a controller? Forever supports them officially."), "inline": False},
            {"name": "❗ Quests", "value": (
                "A yellow **!** over someone's head means they have a job for you. Talk to them, do the thing, "
                "then come back when they have a yellow **?**. That's most of leveling, and it's genuinely relaxing."),
                "inline": False},
            {"name": "🗺️ The five keys worth knowing", "value": (
                "**M** map · **B** bags · **C** your character · **P** your spells · **L** your quest list"),
                "inline": False},
            {"name": "💀 You will die. That's fine.", "value": (
                "You'll turn into a ghost at a graveyard. Run back to your body and click to come back to life. "
                "Skip the angel's offer unless you're truly lost: it costs you. Your partner has died thousands of times, "
                "they're just better at hiding it."), "inline": False},
            {"name": "🫂 Stay together", "value": (
                "Have your partner **invite you to a group** first thing. You'll share quest progress, see each other on "
                "the map, and land in the same copy of the zone when it's crowded."), "inline": False},
            {"name": "⚔️ About the other team", "value": (
                "On the PvP ruleset, players from the other faction can attack you out in the world. If you get jumped, it's not your fault, "
                "it's just Tuesday. Run back, carry on, tell your partner, watch them get very serious about revenge."),
                "inline": False},
            {"name": "🍞 Between fights", "value": (
                "Low on health or mana? **Sit and eat or drink** before the next fight. "
                "Pushing on at half health is how the corpse runs start."), "inline": False},
        ],
        "footer": {"text": "Plus One mode · Buttons below for more. Your subscription already covers Forever, no extra purchase."},
    }


def hub_intro() -> str:
    return ("💞 **Welcome to Plus One mode.** For anyone whose partner, best friend or roommate said \"you'll love it\". "
            "Everything here is private, jargon-free, and judgment-free.")


# ------------------------------------------------------------------ "I'm dying" panic buttons
# Long-standing baseline abilities for each class. Some unlock a few levels in.
PANIC_GENERAL = {
    "heal": "Eat food out of combat, or drink a **health potion** in combat. Train **First Aid** at any city and bandages become your best friend.",
    "escape": "Run back the way you came: monsters give up the chase after a while. Running toward guards or your partner helps too.",
    "help": "Type **help** in group chat, or just say their name out loud. Then let them take over and don't feel bad about it.",
}

PANIC = {  # class -> (heal, escape, help) class-specific lines
    "Warrior": ("**Victory Rush** right after a kill heals you for 10% of your health (from level 20).",
                "**Hamstring** slows the enemy, then walk away. Warriors aren't great at running, so pick fights you can win.",
                "If your partner is a healer, stand still near them and keep hitting. You're the sturdy one, they'll keep you up."),
    "Paladin": ("Cast **Holy Light** on yourself. Yes, really: you're a healer too.",
                "**Hammer of Justice** stuns the enemy for a few seconds. Use them to walk away or heal.",
                "Your **Divine Protection** bubble keeps you safe while your partner cleans up."),
    "Hunter": ("Let your pet hold the monster while you bandage or eat. That's the whole point of the pet.",
               "Back off and keep shooting: you do your best work from far away. **Frost Trap** works mid-fight in Forever.",
               "Tell your pet to attack whatever's hitting your partner. Instant hero."),
    "Rogue": ("Bandages. Rogues can't heal themselves, so carry plenty.",
              "**Sprint** runs very fast. **Vanish** (a bit later) makes you disappear completely.",
              "**Evasion** makes you dodge most hits for a few seconds while your partner helps."),
    "Priest": ("**Power Word: Shield** on yourself first, then a heal. In that order.",
               "**Psychic Scream** makes nearby enemies run away in fear for a few seconds.",
               "You're probably the healer. Heal your partner first, you second, and enjoy being essential."),
    "Shaman": ("Cast **Healing Wave** on yourself. Shamans heal well.",
               "**Frost Shock** or **Earthbind Totem** slows enemies so you can walk away.",
               "Drop totems near your partner too. They help everyone nearby."),
    "Mage": ("Eat the food you can conjure yourself (mages make their own snacks).",
             "**Frost Nova** freezes everything near you. Then walk away and keep casting. **Blink** teleports you a short way.",
             "Let your partner hold their attention while you blast from behind them."),
    "Warlock": ("**Drain Life** steals health from the enemy. **Healthstones** you make are instant heals.",
                "**Fear** makes an enemy run away in terror for a bit.",
                "Your demon pet (the Voidwalker especially) can take the hits for you. Send it in."),
    "Druid": ("**Rejuvenation** and **Healing Touch** on yourself. You can heal.",
              "**Entangling Roots** holds an enemy in place. Walk away and heal while it's stuck.",
              "**Bear Form** gives you lots of armor and health. Turn into a bear and let your partner finish the job."),
}

PANIC_KINDS = {"heal": ("🩹", "Heal me"), "escape": ("🏃", "Get me out"), "help": ("📣", "Get help")}


def panic_embed(cls: str | None, kind: str) -> dict:
    emoji, label = PANIC_KINDS[kind]
    idx = list(PANIC_KINDS).index(kind)
    lines = []
    if cls in PANIC:
        lines.append(f"**As a {cls}:** {PANIC[cls][idx]}")
    lines.append(f"**Anyone:** {PANIC_GENERAL[kind]}")
    return {"title": f"{emoji} {label}", "color": PLUS_COLOR, "description": "\n\n".join(lines),
            "footer": {"text": "Plus One mode · Some abilities unlock a few levels in. Your trainer teaches them."}}


# ------------------------------------------------------------------ duo class quiz
HORDE_CLASSES = ["Warrior", "Paladin", "Hunter", "Rogue", "Priest", "Shaman", "Mage", "Warlock", "Druid"]
STYLES = {
    "melee": ("⚔️", "Up close, hitting things"),
    "ranged": ("🔥", "From a distance, with spells or arrows"),
    "heal": ("💚", "Keeping my partner alive"),
    "pet": ("🐺", "Having a pet do the scary part"),
}
COMFORT = {
    "safe": ("🛡️", "I'd rather not die much"),
    "fine": ("🎲", "Dying is fine, I want fun"),
}
PARTNER_ROLE = {
    "Warrior": "tank", "Paladin": "tank", "Druid": "tank", "Shaman": "melee", "Rogue": "melee",
    "Hunter": "ranged", "Mage": "ranged", "Warlock": "ranged", "Priest": "heal",
}
STYLE_PICKS = {  # style -> classes in order of beginner-friendliness, (safe, fine)
    "melee": (["Paladin", "Warrior", "Druid"], ["Rogue", "Warrior", "Shaman"]),
    "ranged": (["Warlock", "Hunter", "Mage"], ["Mage", "Warlock", "Hunter"]),
    "heal": (["Paladin", "Shaman", "Druid"], ["Priest", "Shaman", "Druid"]),
    "pet": (["Hunter", "Warlock"], ["Hunter", "Warlock"]),
}
WHY = {
    "Warrior": "Wears the heaviest armor and grows into a great protector. Simple buttons, satisfying hits.",
    "Paladin": "Heavy armor and can heal itself. Very hard to kill, which makes it the gentlest start in the game. Horde Paladins are Undead.",
    "Hunter": "Your pet fights up front while you shoot from far back. Often called the easiest class to learn.",
    "Rogue": "Sneaky, stealthy and fast. You pick when fights start, which is a nice kind of control.",
    "Priest": "The classic healer. Groups love you, and you get to save your partner's life on a regular basis.",
    "Shaman": "Heals, fights and drops helpful totems. Flexible, and a Horde-only favorite.",
    "Mage": "Big spells from far away, and you make your own food and water. Squishy but powerful.",
    "Warlock": "Comes with a demon pet that takes hits for you, plus spells that drain enemies. Warlocks won the beta tournament, for what it's worth.",
    "Druid": "Shapeshifts: bear to be sturdy, cat to fight, plus healing spells. Something for every mood.",
}


def duo_pick(partner: str | None, style: str, comfort: str) -> tuple[str, str, str | None]:
    """(class, reason, runner_up)."""
    safe_list, fine_list = STYLE_PICKS.get(style, STYLE_PICKS["ranged"])
    order = list(safe_list if comfort == "safe" else fine_list)
    prole = PARTNER_ROLE.get(partner or "")
    # prefer something that complements the partner, and not the same class
    def fit(c):
        s = 0
        if c == partner:
            s -= 2
        if prole == "tank" and c in ("Priest", "Shaman", "Druid", "Paladin", "Mage", "Warlock", "Hunter"):
            s += 1
        if prole == "heal" and c in ("Warrior", "Paladin", "Druid", "Rogue", "Hunter", "Warlock"):
            s += 1
        if prole in ("melee", "ranged") and c in ("Priest", "Shaman", "Paladin", "Druid"):
            s += 1
        return s
    ranked = sorted(order, key=lambda c: (-fit(c), order.index(c)))
    pick = ranked[0]
    pair = ""
    if partner:
        if prole == "tank":
            pair = f"Your partner's {partner} keeps monsters busy, so you can focus on your part without getting chased."
        elif prole == "heal":
            pair = f"Your partner's Priest keeps you alive, so you can be brave."
        elif pick in ("Priest", "Shaman", "Paladin", "Druid"):
            pair = f"You can heal, so your partner's {partner} gets to go wild knowing you've got them."
        else:
            pair = f"You and a {partner} cover different jobs, so you'll be stronger together than apart."
        if pick == partner:
            pair = f"Same class as your partner: they can teach you every button. Twinning is allowed."
    return pick, (WHY[pick] + (" " + pair if pair else "")).strip(), (ranked[1] if len(ranked) > 1 else None)


def duo_embed(partner: str | None, style: str, comfort: str) -> dict:
    pick, why, alt = duo_pick(partner, style, comfort)
    desc = [f"## {pick}", why]
    if alt:
        desc.append(f"\n-# Close second: **{alt}**. {WHY[alt].split('.')[0]}.")
    desc.append("\nTry `/classtips` with your pick, then tell the server with `/pickaclass`.")
    return {"title": "💞 Your class, picked for two", "color": PLUS_COLOR, "description": "\n".join(desc),
            "footer": {"text": "Plus One mode · No wrong answers. You can always make another character."}}


# ------------------------------------------------------------------ card for the one who brought them
def partner_card_embed() -> dict:
    return {
        "title": "💌 For the one who brought me",
        "color": PLUS_COLOR,
        "description": "A few notes from Plus One HQ to the person who promised \"I'll show you everything.\"",
        "fields": [
            {"name": "🎒 Give them bags", "value": "The first big quality-of-life upgrade is bag space. A few bags from you is a better gift than gold.", "inline": False},
            {"name": "🐢 Let them set the pace", "value": "Read the quests with them, at least at first. You've done Durotar a hundred times; they haven't.", "inline": False},
            {"name": "🎁 Let them loot", "value": "Let them open the chests and pick up the shiny things. It's half the fun.", "inline": False},
            {"name": "🧠 One new thing a night", "value": "Night one is moving, quests and eating. Talents and keybinds can wait a few days.", "inline": False},
            {"name": "🛡️ Be their bodyguard", "value": "On a PvP server, they will get jumped. Stay close in contested zones and handle it calmly. Revenge is optional, but encouraged.", "inline": False},
            {"name": "🏠 End the night at an inn", "value": "Log out in an inn or a city so you both come back with bonus XP. Free progress, very romantic.", "inline": False},
        ],
        "footer": {"text": "Plus One mode · Posted from /draggedalong"},
    }
