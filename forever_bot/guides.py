"""
Keybinds, macros, leveling rotations, controller setup, and the /whichclass quiz.

Written for WoW: Forever. Ability names follow Forever's class changes (see classes.py sources).
Macro syntax confirmed for Forever (Kami Labs macro guide, Oct 2026): #showtooltip, /cast,
/startattack, /cancelform, !Form, [form:N]/[noform:N], [@mouseover,help,nodead], [help,nodead], [@player].
Macros marked verified=False use standard Classic macro syntax that hasn't been confirmed for Forever.
Controller facts: Warcraft Tavern controller guide (Gamepad UI (Alpha)).
"""

# ======================================================================= keybinds: everyone
KEYBIND_BASICS = {
    "new": [
        "**Stop clicking.** Clicking abilities with the mouse is the #1 thing that slows new players down. Every ability you use in a fight should be on a key.",
        "**Move with WASD, steer with the right mouse button.** Hold right-click to turn your character with the mouse; it's faster than A/D, which just turn you slowly.",
        "**Don't backpedal.** Walking backward with S is slow. To get away, turn and run.",
    ],
    "layout": [
        "**Keys around WASD are prime real estate:** 1–5, Q, E, R, F, G, Z, X, C, plus Shift and Ctrl versions of the same keys.",
        "**Most-used abilities** go closest to W: 1, 2, 3, Q, E.",
        "**Emergency buttons** (interrupt, escape, defensive) go on keys you can hit without looking, like F or Shift+Q.",
        "**Side mouse buttons** are perfect for your most important 2 abilities.",
        "**Rebind strafe:** a lot of players move strafe-left/right onto A/D and use the mouse to turn.",
    ],
    "targeting": [
        "**Tab** cycles enemies in front of you.",
        "**Bind 'Target Nearest Friend'** and **'Assist Target'** if you heal or follow a raid leader.",
        "**Set up mouseover macros** (`/macros`) so you can heal or cast on whoever your mouse is over without switching targets.",
    ],
    "howto": "Press **Esc → Options → Keybindings** to change binds. In the Spellbook, drag spells to your bars; the bar slot's key is the ability's key.",
}

CONTROLLER = [
    "**Turn it on:** Esc → Options → Gameplay → **Gamepad (Alpha)** → tick *Enable Gamepad UI (Alpha)*. (Also at character select: Menu → Options → System → Gamepad.)",
    "**Layout:** 4 sets of 8 buttons, D-pad on the left and face buttons on the right. Hold **LT**, **RT**, or both to swap sets, for 28 custom buttons.",
    "**Fixed buttons:** A jumps, B cancels, X interacts (and starts attacking in combat), Y opens context menus.",
    "**Targeting:** by default you hit what you're facing. Hold **RB** to aim enemy targeting with the right stick; hold **LB** to move through party frames with the D-pad.",
    "**Binding spells:** open the radial menu with Menu, go to the Spellbook, press **X** on a spell, then press the button you want.",
    "**Tips:** turn on *Input Legend* while learning; *HUD Modifier: Press to Toggle* means you don't have to hold LB/RB. Keyboard and mouse still work with the gamepad UI on.",
    "**Heads-up:** it's labeled Alpha. Some menus still need a mouse.",
]

# ======================================================================= per class
# bind_first: (ability, why). layout: (key, ability). Keep layouts short and leveling-friendly.
CLASS_GUIDES = {
    "Warrior": {
        "bind_first": [
            ("Charge / Intercept", "your gap closer. Charge from Battle Stance, Intercept from Berserker"),
            ("Pummel / Shield Bash", "your interrupt"),
            ("Hamstring", "keeps runners from escaping"),
            ("Victory Rush", "free 10% heal after a kill (new baseline at 20)"),
            ("Intimidating Shout", "fear a group off you or a healer"),
            ("Berserker Rage", "breaks fear"),
            ("Shield Wall / Retaliation", "emergency buttons; they no longer share a cooldown"),
        ],
        "layout": [("1", "Heroic Strike"), ("2", "Rend"), ("3", "Victory Rush"), ("4", "Thunder Clap"),
                   ("5", "Sunder Armor"), ("Q", "Charge"), ("E", "Hamstring"), ("R", "Overpower"),
                   ("F", "Pummel / Shield Bash"), ("G", "Intimidating Shout"), ("Z", "Berserker Rage"),
                   ("Shift+1/2/3", "Battle / Defensive / Berserker Stance")],
    },
    "Paladin": {
        "bind_first": [
            ("Hammer of Justice", "your stun, and your interrupt"),
            ("Divine Shield", "emergency immunity"),
            ("Blessing of Freedom", "breaks roots and slows"),
            ("Cleanse", "removes poison, disease and magic"),
            ("Judgement", "no longer eats your Seal, so press it on cooldown"),
            ("Holy Strike", "new baseline attack at level 6"),
            ("Lay on Hands", "full heal, now a 20-minute cooldown"),
        ],
        "layout": [("1", "Holy Strike"), ("2", "Judgement"), ("3", "Consecration"), ("4", "Seal (Righteousness / Fury)"),
                   ("5", "Flash of Light"), ("Q", "Hammer of Justice"), ("E", "Blessing of Freedom"), ("R", "Holy Light"),
                   ("F", "Cleanse"), ("G", "Divine Shield"), ("Shift+G", "Lay on Hands")],
    },
    "Hunter": {
        "bind_first": [
            ("Feign Death", "drops you out of combat and threat"),
            ("Freezing Trap", "now usable in combat (30-second cooldown)"),
            ("Scatter Shot", "a short disorient; Undead can't Will of the Forsaken while scattered"),
            ("Disengage", "jump back from melee"),
            ("Concussive Shot", "slow"),
            ("Mend Pet", "keep your pet alive"),
            ("Pet Attack / Pet Follow", "control your pet without clicking its bar"),
        ],
        "layout": [("1", "Arcane Shot"), ("2", "Serpent Sting"), ("3", "Aimed Shot"), ("4", "Multi-Shot"),
                   ("5", "Hunter's Mark"), ("Q", "Concussive Shot"), ("E", "Disengage"), ("R", "Raptor Strike / Wing Clip"),
                   ("F", "Freezing Trap"), ("Shift+F", "Frost Trap"), ("G", "Feign Death"), ("Z", "Scatter Shot"),
                   ("C", "Pet Attack")],
    },
    "Rogue": {
        "bind_first": [
            ("Kick", "your interrupt"),
            ("Gouge / Blind", "short and long control to escape or reset"),
            ("Vanish", "escape and re-stealth"),
            ("Sprint", "speed to escape or catch"),
            ("Evasion", "huge dodge when a melee is on you"),
            ("Sap", "no longer breaks Stealth, so you can sap and keep sneaking"),
            ("Kidney Shot / Cheap Shot", "stuns"),
        ],
        "layout": [("1", "Sinister Strike / Backstab"), ("2", "Eviscerate"), ("3", "Slice and Dice"), ("4", "Rupture"),
                   ("5", "Ambush / Cheap Shot"), ("Q", "Kick"), ("E", "Gouge"), ("R", "Kidney Shot"), ("F", "Blind"),
                   ("G", "Vanish"), ("Z", "Sprint"), ("X", "Evasion"), ("C", "Sap"), ("Shift+1", "Stealth")],
    },
    "Priest": {
        "bind_first": [
            ("Power Word: Shield", "the first button when you get hit"),
            ("Psychic Scream", "fear everything near you"),
            ("Fade", "drop threat (doubled in Forever)"),
            ("Fear Ward", "every Priest gets it at 20; huge against Warlocks"),
            ("Dispel Magic", "remove debuffs from allies, buffs from enemies"),
            ("Shadow Word: Death", "instant finisher at 32 (hurts you if it doesn't kill)"),
            ("Flash Heal", "your fast heal"),
        ],
        "layout": [("1", "Shadow Word: Pain"), ("2", "Mind Blast"), ("3", "Mind Flay"), ("4", "Devouring Plague"),
                   ("5", "Shoot (wand)"), ("Q", "Power Word: Shield"), ("E", "Renew"), ("R", "Flash Heal"),
                   ("F", "Psychic Scream"), ("G", "Fade"), ("Z", "Dispel Magic"), ("X", "Fear Ward"),
                   ("Shift+R", "Greater Heal")],
    },
    "Shaman": {
        "bind_first": [
            ("Earth Shock", "your interrupt"),
            ("Frost Shock", "slow"),
            ("Purge", "strips enemy buffs"),
            ("Call of the Elements", "drops your whole totem preset at once (level 20)"),
            ("Totemic Recall", "picks totems back up, refunds some mana"),
            ("Ghost Wolf", "travel and escape"),
            ("Lesser Healing Wave / Healing Wave", "self-heal"),
        ],
        "layout": [("1", "Stormstrike / Lightning Bolt"), ("2", "Flame Shock"), ("3", "Earth Shock"), ("4", "Lava Burst"),
                   ("5", "Chain Lightning"), ("Q", "Frost Shock"), ("E", "Lesser Healing Wave"), ("R", "Healing Wave"),
                   ("F", "Purge"), ("G", "Ghost Wolf"), ("Z", "Call of the Elements"), ("X", "Totemic Recall"),
                   ("C", "Totemic Projection")],
    },
    "Mage": {
        "bind_first": [
            ("Counterspell", "your interrupt"),
            ("Frost Nova", "root everything near you"),
            ("Blink", "escape"),
            ("Polymorph", "turn an extra enemy into a sheep"),
            ("Ice Block", "emergency immunity (Frost talent)"),
            ("Cone of Cold", "slow a group"),
            ("Remove Lesser Curse", "cleanse curses"),
        ],
        "layout": [("1", "Frostbolt / Fireball / Arcane Blast"), ("2", "Fire Blast"), ("3", "Ice Lance"),
                   ("4", "Arcane Missiles"), ("5", "Frostfire Bolt"), ("Q", "Frost Nova"), ("E", "Blink"),
                   ("R", "Cone of Cold"), ("F", "Counterspell"), ("G", "Polymorph"), ("Z", "Ice Block"),
                   ("X", "Mana Shield"), ("C", "Evocation")],
    },
    "Warlock": {
        "bind_first": [
            ("Fear", "your main control. Undead can break it; Priests can Fear Ward"),
            ("Death Coil", "instant horror plus a heal"),
            ("Howl of Terror", "fear everything near you"),
            ("Spell Lock / Seduction", "pet interrupt (Felhunter) or control (Succubus)"),
            ("Health Funnel", "keep your pet tank alive"),
            ("Healthstone", "emergency heal"),
            ("Pet Attack", "send your demon in"),
        ],
        "layout": [("1", "Shadow Bolt"), ("2", "Corruption"), ("3", "Bane of Agony"), ("4", "Immolate"),
                   ("5", "Drain Life"), ("Q", "Fear"), ("E", "Death Coil"), ("R", "Life Tap"), ("F", "Pet: Spell Lock"),
                   ("G", "Howl of Terror"), ("Z", "Healthstone"), ("X", "Drain Soul"), ("C", "Pet Attack")],
    },
    "Druid": {
        "bind_first": [
            ("Bear / Cat / Travel Form", "Shift+1/2/3 or similar; you'll swap constantly"),
            ("Bash", "your stun and interrupt in Bear Form"),
            ("Entangling Roots", "now works indoors"),
            ("Barkskin", "now usable while shapeshifted"),
            ("Nature's Grasp", "baseline at 10, usable in forms"),
            ("Innervate", "mana for you or a healer"),
            ("Revive", "out-of-combat res at 12"),
        ],
        "layout": [("1", "Claw / Shred / Wrath"), ("2", "Rake / Moonfire"), ("3", "Ferocious Bite / Rip"),
                   ("4", "Rejuvenation"), ("5", "Regrowth"), ("Q", "Entangling Roots"), ("E", "Bash"),
                   ("R", "Barkskin"), ("F", "Nature's Grasp"), ("Shift+1", "Bear Form"), ("Shift+2", "Cat Form"),
                   ("Shift+3", "Travel Form"), ("Z", "Innervate")],
    },
}

# ======================================================================= macros
# (title, macro text, what it does, verified)
_MOUSEOVER_NOTE = "Hover your mouse over a target and press the key. No target switching."

MACROS = {
    "Warrior": [
        ("Attack + Heroic Strike", "#showtooltip\n/startattack\n/cast Heroic Strike", "Makes sure auto-attack is on, then queues Heroic Strike.", True),
        ("Charge or Intercept", "#showtooltip\n/cast [stance:1] Charge; [stance:3] Intercept",
         "One key: Charge in Battle Stance, Intercept in Berserker Stance.", False),
    ],
    "Paladin": [
        ("Mouseover Flash of Light", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Flash of Light",
         _MOUSEOVER_NOTE + " Falls back to your target, then yourself.", True),
        ("Mouseover Cleanse", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Cleanse", _MOUSEOVER_NOTE, True),
        ("Attack + Holy Strike", "#showtooltip\n/startattack\n/cast Holy Strike", "Starts auto-attack with Holy Strike.", True),
    ],
    "Hunter": [
        ("Mark + send pet", "#showtooltip\n/cast Hunter's Mark\n/petattack", "Marks the target and sends your pet in.", False),
        ("Mouseover Mend Pet", "#showtooltip\n/cast [@pet] Mend Pet", "Heals your pet without targeting it.", False),
    ],
    "Rogue": [
        ("Attack + Sinister Strike", "#showtooltip\n/startattack\n/cast Sinister Strike", "Starts auto-attack with your builder.", True),
        ("Mouseover Kick", "#showtooltip\n/cast [@mouseover,harm,nodead][] Kick", "Kick whoever your mouse is over, or your target.", False),
    ],
    "Priest": [
        ("Mouseover Flash Heal", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Flash Heal",
         _MOUSEOVER_NOTE + " Falls back to your target, then yourself.", True),
        ("Mouseover Power Word: Shield", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Power Word: Shield", _MOUSEOVER_NOTE, True),
        ("Mouseover Dispel", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Dispel Magic", _MOUSEOVER_NOTE, True),
    ],
    "Shaman": [
        ("Mouseover Healing Wave", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Healing Wave", _MOUSEOVER_NOTE, True),
        ("Mouseover Earth Shock", "#showtooltip\n/cast [@mouseover,harm,nodead][] Earth Shock", "Interrupt whoever your mouse is over.", False),
        ("Attack + Stormstrike", "#showtooltip\n/startattack\n/cast Stormstrike", "Starts auto-attack with Stormstrike.", True),
    ],
    "Mage": [
        ("Mouseover Polymorph", "#showtooltip\n/cast [@mouseover,harm,nodead][] Polymorph", "Sheep a second enemy without losing your target.", False),
        ("Counterspell (cancel cast)", "#showtooltip\n/stopcasting\n/cast Counterspell", "Stops whatever you're casting so the interrupt goes out right away.", False),
    ],
    "Warlock": [
        ("Mouseover Corruption", "#showtooltip\n/cast [@mouseover,harm,nodead][] Corruption", "DoT up extra enemies without switching targets.", False),
        ("Mouseover Fear", "#showtooltip\n/cast [@mouseover,harm,nodead][] Fear", "Fear a second enemy while you keep your target.", False),
        ("Pet attack", "/petattack", "Sends your demon at your target.", False),
    ],
    "Druid": [
        ("Cat Form / Dash", "#showtooltip\n/cast [noform:3] !Cat Form\n/cast [form:3] Dash",
         "Shift into Cat, or Dash if you're already a cat. Never accidentally shifts you out.", True),
        ("Mouseover Rejuvenation", "#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] Rejuvenation", _MOUSEOVER_NOTE, True),
        ("Leave form", "/cancelform", "Drops whatever form you're in.", True),
    ],
}
MACRO_HOWTO = ("Type **/macro** in game → **New** → pick an icon (the ❓ icon with `#showtooltip` shows the spell's own icon) "
               "→ paste → drag the macro to your bar. Macros max out at 255 characters.")

# ======================================================================= leveling rotations
# (spec, [steps]). Beginner-level priorities using Forever's versions of each class.
ROTATIONS = {
    "Warrior": [
        ("Arms (leveling)", ["Charge in", "Rend", "Overpower whenever it lights up", "Your big Arms strike on cooldown",
                             "Heroic Strike to dump extra Rage", "Victory Rush after the kill to heal"]),
        ("Fury", ["Bloodthirst on cooldown (now gives 10% speed, no heal)", "Whirlwind (hits with both weapons with Raging Blows)",
                  "Heroic Strike or Cleave to dump Rage", "Victory Rush after kills"]),
        ("Protection (tank)", ["Defensive Stance, Shield Block when you're taking hits", "Revenge whenever it's up",
                               "Sunder Armor on your main target", "Thunder Clap for groups (usable in Defensive now)"]),
    ],
    "Paladin": [
        ("Retribution (leveling)", ["Seal of Righteousness up", "Judgement on cooldown (it keeps your Seal now)",
                                    "Holy Strike on cooldown", "Consecration on groups", "Flash of Light between fights if low"]),
        ("Protection (tank)", ["Righteous Fury and Seal of Fury up", "Judgement to pull and taunt from range",
                               "Holy Strike on cooldown", "Consecration for groups", "Templar's Bulwark when it gets scary (21)"]),
        ("Holy (healer)", ["Flash of Light for most healing", "Holy Light for big hits", "Holy Shock on cooldown once talented (21)",
                           "Light's Vigil to heal the whole party at 31", "Cleanse debuffs"]),
    ],
    "Hunter": [
        ("Marksmanship / Beast Mastery", ["Hunter's Mark, send your pet", "Serpent Sting", "Arcane Shot on cooldown",
                                          "Aimed Shot (20+) or Multi-Shot; they share a cooldown", "Auto Shot in between",
                                          "If something reaches you: Frost Trap, step back"]),
        ("Survival (melee)", ["Hunter's Mark", "Raptor Strike on cooldown", "Mongoose Bite whenever it procs",
                              "Strider Kick at 21 for burst and speed", "Wing Clip anything that runs"]),
    ],
    "Rogue": [
        ("Combat (leveling)", ["Open with Cheap Shot or Ambush", "Sinister Strike to build combo points",
                               "Slice and Dice at 1–2 points", "Eviscerate at 5 points", "Evasion if a melee is winning"]),
        ("Assassination (daggers)", ["Open from stealth", "Mutilate to build (21, needs two daggers)",
                                     "Keep poisons up", "Venom as your finisher at 31", "Eviscerate on low targets"]),
        ("Subtlety", ["Open from stealth", "Hemorrhage or Backstab to build", "Rupture to stack Thousand Cuts (31)",
                      "Eviscerate to finish"]),
    ],
    "Priest": [
        ("Shadow (leveling)", ["Power Word: Shield first", "Shadow Word: Pain", "Mind Blast", "Mind Flay",
                               "Devouring Plague on tougher mobs", "Wand to finish and save mana"]),
        ("Holy / Discipline (healer)", ["Renew on whoever's taking damage", "Power Word: Shield the tank",
                                         "Flash Heal for fast healing", "Greater Heal for big hits",
                                         "Penance (Disc 21) or Prayer of Mending (Holy 31)"]),
    ],
    "Shaman": [
        ("Enhancement (leveling)", ["Windfury or Rockbiter imbue (lasts an hour)", "Call of the Elements to drop totems",
                                    "Stormstrike on cooldown (every 8 seconds)", "Earth Shock or Flame Shock",
                                    "Instant Lightning Bolt when Maelstrom Weapon is full"]),
        ("Elemental", ["Flame Shock", "Lava Burst on cooldown at 21 (stronger on Flame Shocked targets)",
                       "Lightning Bolt (2.5-second cast now)", "Chain Lightning for groups"]),
        ("Restoration (healer)", ["Water Shield up", "Riptide on cooldown at 31", "Chain Heal (stronger on Riptide targets)",
                                  "Healing Wave for big hits", "Mana Tide Totem when low"]),
    ],
    "Mage": [
        ("Frost (leveling)", ["Frostbolt", "Frostbolt", "Frost Nova when it gets close", "Ice Lance on frozen targets (200% more)",
                              "Step back, Frostbolt again", "Cone of Cold to slow a group"]),
        ("Fire", ["Fireball", "Fire Blast and Scorch crits stack Heating Up", "Pyroblast when Heating Up is high",
                  "Frostfire Bolt at 40 counts as Fire too"]),
        ("Arcane", ["Arcane Blast up to 4 stacks", "Arcane Missiles when Missile Barrage procs",
                    "Let stacks fall off if mana gets low", "Evocation to recover mana"]),
    ],
    "Warlock": [
        ("Affliction (leveling)", ["Pet attacks first", "Corruption", "Bane of Agony", "Drain Life to heal while you fight",
                                   "Life Tap for mana, Drain Soul on low targets for shards", "Wrack at 31"]),
        ("Demonology", ["Voidwalker tanks (pets scale with you now)", "Corruption and Bane", "Shadow Bolt",
                        "Health Funnel the pet when needed", "Soul Link at 21"]),
        ("Destruction", ["Immolate", "Conflagrate on cooldown (16)", "Incinerate at 31 (stronger with Immolate)",
                         "Shadow Bolt otherwise", "Bane of Havoc on a second target (21)"]),
    ],
    "Druid": [
        ("Feral cat (leveling)", ["Prowl and open", "Claw or Shred to build combo points", "Rip or Ferocious Bite at 5 points",
                                  "Shifting Power (16) for a burst of energy", "Potions work in form now"]),
        ("Feral bear (tank)", ["Primal Bite on cooldown (16)", "Lacerate to stack (42)", "Swipe for groups",
                               "Demoralizing Roar", "Growl if something gets loose"]),
        ("Balance", ["Moonfire", "Insect Swarm (16)", "Wrath (cheap now) to build Eclipse", "Starfire with Eclipse up"]),
        ("Restoration (healer)", ["Rejuvenation", "Regrowth (much cheaper now)", "Swiftmend (16, keeps the HoT now)",
                                  "Wild Growth at 31 on a hurt party"]),
    ],
}

# ======================================================================= /whichclass quiz
# Each answer adds points to classes. Five questions, 3–4 answers each.
QUIZ = [
    ("What do you want to do in a group?", [
        ("🛡️ Tank: hold enemies' attention", {"Warrior": 3, "Paladin": 2, "Druid": 2, "Shaman": 1, "Warlock": 1}),
        ("💚 Heal: keep everyone alive", {"Priest": 3, "Shaman": 2, "Druid": 2, "Paladin": 2}),
        ("🗡️ Melee damage, up close", {"Rogue": 3, "Warrior": 2, "Shaman": 1, "Druid": 1, "Paladin": 1, "Hunter": 1}),
        ("🔥 Ranged damage, from afar", {"Mage": 3, "Warlock": 3, "Hunter": 3, "Priest": 1, "Shaman": 1, "Druid": 1}),
    ]),
    ("How will you mostly play?", [
        ("🧭 Solo, at my own pace", {"Hunter": 3, "Warlock": 3, "Druid": 1, "Paladin": 1}),
        ("🤝 A mix of solo and friends", {"Shaman": 2, "Druid": 2, "Paladin": 1, "Priest": 1, "Mage": 1, "Rogue": 1}),
        ("👥 Mostly in groups and raids", {"Priest": 2, "Warrior": 2, "Mage": 1, "Paladin": 1, "Shaman": 1}),
    ]),
    ("How many buttons do you want?", [
        ("🙂 Keep it simple", {"Hunter": 2, "Paladin": 2, "Warlock": 1, "Warrior": 1}),
        ("🎛️ Some depth", {"Mage": 1, "Priest": 1, "Rogue": 1, "Shaman": 1, "Warlock": 1}),
        ("🧠 Lots of tools and swapping", {"Druid": 3, "Shaman": 2, "Rogue": 2, "Warrior": 1}),
    ]),
    ("Your PvP style?", [
        ("👤 Stealth and burst", {"Rogue": 3, "Druid": 1}),
        ("❄️ Control from range", {"Mage": 2, "Warlock": 2, "Hunter": 2, "Priest": 1}),
        ("🧱 Tough and hard to kill", {"Warrior": 2, "Paladin": 2, "Warlock": 1, "Druid": 1, "Shaman": 1}),
        ("🎺 Support my team", {"Priest": 2, "Shaman": 2, "Paladin": 1, "Druid": 1}),
    ]),
    ("Pick a vibe", [
        ("🐺 Beasts and nature", {"Hunter": 3, "Druid": 3, "Shaman": 1}),
        ("⚡ Arcane and the elements", {"Mage": 3, "Shaman": 3}),
        ("✨ Holy light or shadow", {"Priest": 3, "Paladin": 3}),
        ("⚔️ Steel and steel only", {"Warrior": 3, "Rogue": 3}),
        ("😈 Demons and curses", {"Warlock": 4}),
    ]),
]


def score_quiz(answers: list[int]) -> list[tuple[str, int]]:
    """answers[i] = chosen option index for QUIZ[i]. Returns classes sorted by score (ties: alphabetical)."""
    totals = {}
    for qi, ai in enumerate(answers):
        for cls, pts in QUIZ[qi][1][ai][1].items():
            totals[cls] = totals.get(cls, 0) + pts
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
