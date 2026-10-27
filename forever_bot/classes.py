"""
Class tips for all nine classes, written for WoW: Forever (not retail, not Classic).

Sources (Oct 2026): Blizzard's Forever class deep dives as covered by Warcraft Tavern
(Priest/Warrior, Mage/Shaman, Rogue/Warlock, Paladin) and Blizzard's Hunter/Druid deep dive;
Warcraft Tavern racial changes; Method race/class table; Forever Open finals data (Raider.IO).
Beta notes: Blizzard says abilities and talents may still change. Edit freely.

Each class:
  races      Horde races that can play it (Forever)
  role       one plain-English line for new players
  new        the biggest Forever changes (vets)
  leveling   practical leveling tips
  pvp        Horde PvP tips
  talents    gold-medal / signature talents worth knowing (points tier in parentheses)
"""

COLORS = {  # standard WoW class colors
    "Warrior": 0xC69B6D, "Paladin": 0xF48CBA, "Hunter": 0xAAD372, "Rogue": 0xFFF468, "Priest": 0xE8E8E8,
    "Shaman": 0x0070DD, "Mage": 0x3FC7EB, "Warlock": 0x8788EE, "Druid": 0xFF7C0A,
}

CLASSES = {
    "Warrior": {
        "races": "Orc · Troll · Tauren · Undead · Skyborne",
        "role": "The front line. Tank as Protection, or deal big melee damage as Arms or Fury. Rage builds as you hit and get hit.",
        "new": [
            "Rage from hits ignores armor and shields, and crits give 75% more Rage.",
            "**Tactical Mastery** is baseline at 14: keep 10 Rage when you swap stances.",
            "**Victory Rush** at 20: after a kill, an instant hit that heals 10% of your max health.",
            "Thunder Clap works in Defensive Stance; Rend and Thunder Clap now scale with Attack Power.",
            "Bloodthirst no longer heals. It gives 10% movement speed instead.",
        ],
        "leveling": [
            "Victory Rush after every kill means far fewer eating breaks.",
            "Stance swaps are cheap now. Charge in Battle Stance, then swap as needed.",
            "Rend and Thunder Clap scale with Attack Power, so they're worth pressing while leveling.",
        ],
        "pvp": [
            "**Spearing Strike** (Arms) dismounts targets and hits mounted players for double. Built for ambushing riders.",
            "In 1v1 duels at 30, warriors struggled against kiting classes. In battlegrounds, stick with a healer.",
        ],
        "talents": ["Spearing Strike (Arms, 16)", "Raging Blows (Fury, 16)", "Vanguard (Protection, 16)",
                    "Weaponmaster (Arms, replaces weapon specs)", "Boundless Rage (Fury, more max Rage)"],
    },
    "Paladin": {
        "races": "Undead (new: the first Horde paladins)",
        "role": "A plate-armored healer, tank or holy warrior. New for the Horde: Undead can be Paladins.",
        "new": [
            "**Seal of Fury** at 10: the tanking seal. Hits add Holy damage and an absorb shield; its Judgement taunts.",
            "**Judgement no longer consumes your Seal.**",
            "**Holy Strike** at 6 and **Consecration** for everyone at 20.",
            "Salvation is no longer a Blessing, so it can sit alongside one. Lay on Hands is a 20-minute cooldown.",
            "Seal twisting now comes from the Ret talent **Twist of Light**, not baseline.",
        ],
        "leveling": [
            "Holy Strike at 6 gives you a real button to press early.",
            "Judge freely: Judgement no longer eats your Seal.",
            "Seal of Fury's absorb shield helps you survive solo, not just tank.",
        ],
        "pvp": [
            "Paladins went 16–13 in duels vs other classes in the beta tournament finals and had four undefeated qualifiers.",
            "**Holy Shock** is now a 21-point talent with a 10-second cooldown, so shockadin hybrids are real.",
            "Undead keep **Will of the Forsaken** to break Fear, Charm and Sleep.",
        ],
        "talents": ["Holy Shock (Holy, 21)", "Light's Vigil (Holy, 31)", "Templar's Bulwark (Protection, 21)",
                    "Sacred Arbiter (Retribution, 16)", "Twist of Light (Retribution, 31)"],
    },
    "Hunter": {
        "races": "Orc · Troll · Tauren · Skyborne",
        "role": "Ranged damage with a pet at your side. One of the most comfortable classes for leveling solo.",
        "new": [
            "**Aimed Shot** is baseline at 20 for every Hunter.",
            "Traps work **in combat** (30-second cooldown); Frost and Fire traps have separate cooldowns.",
            "Pets scale with your gear, and every pet family has its own unique ability. Foxes are a new family.",
            "**Lone Wolf** (Marksmanship): 20% more damage with no pet out.",
            "Survival is a real melee spec now, with Strider Kick and Lacerating Strikes.",
        ],
        "leveling": [
            "Pick a pet for its family ability: Boar Charge, Spider Web, Turtle Shell Shield, Wolf Furious Howl and more.",
            "Something on you? Traps work in combat now. Drop a Frost Trap and back off.",
            "Pets scale with your gear, so upgrades help both of you.",
        ],
        "pvp": [
            "Undead can't use Will of the Forsaken while Scatter Shotted.",
            "Hunters went 7–11 vs other classes in the beta tournament finals; group PvP plays to your range.",
        ],
        "talents": ["Lone Wolf (Marksmanship, 11)", "Summon Hawk (Beast Mastery, 16)", "Sniper Shot (Marksmanship, 31)",
                    "Strider Kick (Survival, 21)", "Lacerating Strikes (Survival, 31)"],
    },
    "Rogue": {
        "races": "Orc · Troll · Undead · Skyborne",
        "role": "Stealthy melee burst. Pick your fights, open from stealth, and finish fast.",
        "new": [
            "Poisons get more charges and **stack with Sharpening Stones** and other temporary enchants.",
            "Rogues can use **one-handed axes**. Hack and Slash replaces the old weapon specializations.",
            "**Sap no longer breaks Stealth.**",
            "Distract also lowers nearby enemies' stealth detection for 10 seconds.",
            "New signatures: **Mutilate** and **Venom** (Assassination), **Thousand Cuts** (Subtlety).",
        ],
        "leveling": [
            "Use poisons and a Sharpening Stone at the same time now.",
            "Sap, stay stealthed, and slip past packs you don't need to fight.",
            "Hack and Slash gives axes a chance at an extra attack, like swords.",
        ],
        "pvp": [
            "Sap the healer and stay in stealth to choose your target.",
            "Distract lowers stealth detection, but it alerts nearby players that a Rogue is around.",
            "Rogues went 5–11 vs other classes in the beta tournament finals.",
        ],
        "talents": ["Cold Blood (Assassination, 16)", "Mutilate (Assassination, 21)", "Venom (Assassination, 31)",
                    "Flawless Execution (Combat, 16)", "Premeditation (Subtlety, 16)", "Thousand Cuts (Subtlety, 31)"],
    },
    "Priest": {
        "races": "Troll · Undead",
        "role": "Healer or shadow caster. Every group wants one.",
        "new": [
            "**Fear Ward** and **Devouring Plague** for every Priest at 20, whatever your race.",
            "**Divine Spirit** baseline at 30 and **Shadow Word: Death** at 32 (costs you 10% health if it doesn't kill).",
            "Shadowform halves Shadow spell mana costs and doubles their crit bonus.",
            "Undead get **Dark Sacrifice** at 20: turn health into mana over time.",
            "New signatures: Penance (Discipline), Prayer of Mending (Holy), Vampiric Embrace (Shadow, 16).",
        ],
        "leveling": [
            "Shadow is the comfortable leveling route, and Shadowform halves your Shadow mana costs.",
            "Fade's threat reduction is doubled. Use it when a dungeon pull turns on you.",
            "Renew from several Priests can now stack on one target.",
        ],
        "pvp": [
            "Fear Ward is for every Priest now, which helps a lot against Warlocks (who won the beta tournament).",
            "Shadow Word: Death is an instant finisher, but it costs you if it doesn't kill.",
            "Priests went 9–12 vs other classes in the beta tournament finals.",
        ],
        "talents": ["Soul Warding (Discipline, 16)", "Penance (Discipline, 21)", "Binding Heal (Holy, 16)",
                    "Prayer of Mending (Holy, 31)", "Vampiric Embrace (Shadow, 16)"],
    },
    "Shaman": {
        "races": "Orc · Troll · Tauren · Skyborne",
        "role": "The Horde hybrid: heal, throw lightning, or swing a big weapon, with totems that buff your group.",
        "new": [
            "Totems: 1-second global cooldown, and buff totems last 5 minutes.",
            "**Call of the Elements** at 20: preset four totems and drop them all in one 3-second cast.",
            "**Totemic Projection** at 22 moves all your totems up to 30 yards.",
            "Weapon imbues last **60 minutes** and stack with stones and oils. Windfury Totem is a party buff.",
            "New signatures: Lava Burst (Elemental), Maelstrom Weapon (Enhancement), Riptide (Restoration). Elemental Mastery is gone.",
        ],
        "leveling": [
            "Set up a Call of the Elements preset at 20. One cast drops all four totems.",
            "Imbue once an hour instead of every 5 minutes.",
            "Rockbiter plus Spirit Weapons lets Enhancement off-tank small groups.",
        ],
        "pvp": [
            "Shamans went 19–11 vs other classes in the beta tournament finals and took 3rd and 4th.",
            "Totemic Projection lets you reposition every totem mid-fight.",
            "**Earthbound** (Elemental, 21) makes Earthbind Totem root nearby enemies for 5 seconds.",
        ],
        "talents": ["Shamanistic Focus (Enhancement, 11)", "Stormstrike (Enhancement, 16)", "Earthbound (Elemental, 21)",
                    "Lava Burst (Elemental, 31)", "Water Shield (Restoration, 11)", "Riptide (Restoration, 31)"],
    },
    "Mage": {
        "races": "Orc (new) · Troll · Undead",
        "role": "Ranged spell damage and crowd control, plus food, water and portals for the group.",
        "new": [
            "**Frostfire Bolt** at 40 counts as both Fire and Frost.",
            "Arcane: **Arcane Blast** (11) and Missile Barrage (16).",
            "Fire: **Heating Up** is Forever's Hot Streak; crits shorten your next Pyroblast.",
            "Frost: **Ice Lance** (11) does 300% more to Frozen targets; **Fingers of Frost** makes targets count as Frozen.",
            "Cone of Cold lasts less time, to stop huge kite-pulls. Orc Mages are new.",
        ],
        "leveling": [
            "Huge AoE kite-pulls got harder (Cone of Cold is shorter), so plan on smaller pulls.",
            "Learn **Comprehension**, a new minor tradeskill for reading scrolls that monsters drop.",
            "Frost: Frost Nova, then Ice Lance for big damage on the frozen target.",
        ],
        "pvp": [
            "Mages went 4–12 vs other classes in the beta tournament finals, and all four lost in the same round.",
            "Frost combos (a root, then Ice Lance with Fingers of Frost) are built for burst.",
            "Undead Mages keep Will of the Forsaken against Warlock fears.",
        ],
        "talents": ["Arcane Blast (Arcane, 11)", "Missile Barrage (Arcane, 16)", "Ice Lance (Frost, 11)",
                    "Ice Block (Frost, 16)", "Cold Snap (Frost, 21)"],
    },
    "Warlock": {
        "races": "Orc · Troll (new) · Undead",
        "role": "Damage over time, demons and fear. A Warlock won the $100K beta duel tournament.",
        "new": [
            "**Pets scale with your stats.** Your Voidwalker is a real tank now.",
            "Curse of Agony and Curse of Doom are now **Banes**: one Bane per Warlock per target.",
            "Firestone and Spellstone are weapon imbues that stack with Wizard Oil.",
            "**Soul Link** is a 21-point talent; **Demonic Pact** (31) keeps Demonic Sacrifice when you swap pets.",
            "New signatures: Wrack (Affliction, 31), Bane of Havoc (21) and Incinerate (31) in Destruction.",
        ],
        "leveling": [
            "Free mount at 40: the quest is from **Strahad Farsan in Ratchet**.",
            "Drain Soul now guarantees a Soul Shard after enough ticks.",
            "Life Tap scales with Spirit.",
        ],
        "pvp": [
            "Warlocks went 26–7 vs other classes in the beta tournament finals and took 1st and 2nd.",
            "Expect Undead to Will of the Forsaken your Fear, and Priests to Fear Ward.",
            "That was level-30 dueling. At 60, more trinkets and Fear answers will change things.",
        ],
        "talents": ["Demonic Sacrifice (Demonology, 11)", "Soul Link (Demonology, 21)", "Demonic Pact (Demonology, 31)",
                    "Wrack (Affliction, 31)", "Bane of Havoc (Destruction, 21)", "Incinerate (Destruction, 31)"],
    },
    "Druid": {
        "races": "Tauren · Skyborne",
        "role": "The shapeshifter: bear tank, cat damage, moonkin caster or healer, whatever the group needs.",
        "new": [
            "Most **potions and consumables work in forms**, and most doors and objects too.",
            "In forms, your auto-attack uses your **weapon's DPS**, and weapon enchants and procs work.",
            "**Revive** at 12, **Nature's Grasp** at 10, **Omen of Clarity** baseline at 20.",
            "Tiger's Fury is gone (replaced by **Shifting Power**), and **Primal Bite** replaces Mangle.",
            "New signatures: Berserk (Feral, 31), Wild Growth (Restoration, 31), Eclipse (Balance).",
        ],
        "leveling": [
            "Drink potions and open doors without leaving form, which matters a lot for Feral.",
            "Your weapon matters in forms now, so don't skip weapon upgrades.",
            "Racials work while shapeshifted, so Tauren can War Stomp in bear form (90-second cooldown).",
        ],
        "pvp": [
            "Druids went 12–14 vs other classes in the beta tournament finals; Minpojke finished top 6.",
            "Barkskin works while shapeshifted, and Entangling Roots works indoors.",
        ],
        "talents": ["Feral Charge (Feral, 11)", "Primal Bite (Feral, 16)", "Berserk (Feral, 31)",
                    "Swiftmend (Restoration, 16)", "Wild Growth (Restoration, 31)", "Insect Swarm (Balance, 16)"],
    },
}

# One-liners for the rotating "Class spotlight" in check-ins: (class, tip)
SPOTLIGHT = [(c, t) for c, d in CLASSES.items() for t in d["leveling"][:2]]


# 1.2.2: leveling and PvP tips as "**do this** → benefit". Same facts as above, reworded.
# Beta-tournament records stay as plain facts (they're context, not instructions).
_DO = {
    "Warrior": {
        "leveling": [
            "**Victory Rush right after every kill** → a free 10% heal each fight, so you stop to eat far less.",
            "**Charge in Battle Stance, then swap to whatever the fight needs** → Tactical Mastery keeps 10 Rage, so swapping no longer resets you.",
            "**Keep Rend and Thunder Clap in your rotation** → both scale with Attack Power now, so they get better as your gear does.",
        ],
        "pvp": [
            "**Hunt mounted players with Spearing Strike (Arms)** → it dismounts them and hits for double damage on riders.",
            "**Queue battlegrounds with a healer on your hip** → in the level-30 beta duels, warriors struggled against kiting classes on their own.",
        ],
    },
    "Paladin": {
        "leveling": [
            "**Bind Holy Strike as soon as you get it at 6** → you finally have a real button to press, not just auto-attack.",
            "**Judge on cooldown** → Judgement no longer eats your Seal, so there's no reason to save it.",
            "**Run Seal of Fury while soloing, not just tanking** → its absorb shield means fewer stops between pulls.",
        ],
        "pvp": [
            "**Try a shockadin build if you want burst** → Holy Shock is a 21-point talent on a 10-second cooldown now.",
            "**Save Will of the Forsaken (Undead) for a Fear, Charm or Sleep** → breaking a Warlock's Fear is the trade that wins duels.",
            "Paladins went 16–13 vs other classes in the beta tournament finals, with four undefeated qualifiers.",
        ],
    },
    "Hunter": {
        "leveling": [
            "**Tame for the family ability, not the look** → Boar Charge, Spider Web, Turtle Shell Shield and Wolf Furious Howl each solve a different problem.",
            "**Drop a Frost Trap mid-fight and back off** → traps work in combat now, so you can fix a bad pull without running first.",
            "**Upgrade your own gear before your pet's food** → pets scale with your gear, so every upgrade counts twice.",
        ],
        "pvp": [
            "**Scatter Shot an Undead when you need them locked down** → they can't use Will of the Forsaken while Scatter Shotted.",
            "**Play group PvP from max range** → hunters went 7–11 in beta finals duels, but range is your edge in battlegrounds.",
        ],
    },
    "Rogue": {
        "leveling": [
            "**Run poisons and a Sharpening Stone together** → they stack now, so it's free damage.",
            "**Sap and sneak past packs you don't need** → you skip fights that give little XP and keep moving.",
            "**Don't pass on a good axe** → Hack and Slash gives axes a chance at an extra attack, like swords.",
        ],
        "pvp": [
            "**Sap the healer, then stay stealthed** → you pick the fight and the target.",
            "**Use Distract only when you're ready to commit** → it lowers stealth detection but tells nearby players a Rogue is around.",
            "Rogues went 5–11 vs other classes in the beta tournament finals.",
        ],
    },
    "Priest": {
        "leveling": [
            "**Level as Shadow and stay in Shadowform** → Shadow spells cost half the mana, so you drink far less.",
            "**Fade the moment a dungeon pull turns on you** → its threat drop is doubled now.",
            "**Stack Renews with other Priests** → Renew from several Priests can sit on one target now.",
        ],
        "pvp": [
            "**Fear Ward yourself before engaging a Warlock** → every Priest has it now, and Warlocks won the beta tournament.",
            "**Only Shadow Word: Death when it will kill** → it's an instant finisher, but it costs you if they live.",
            "Priests went 9–12 vs other classes in the beta tournament finals.",
        ],
    },
    "Shaman": {
        "leveling": [
            "**Set up a Call of the Elements preset at 20** → one cast drops all four totems.",
            "**Imbue your weapon once when you log in** → imbues last an hour now, not 5 minutes.",
            "**Pair Rockbiter with Spirit Weapons as Enhancement** → you can off-tank small groups.",
        ],
        "pvp": [
            "**Move your totems with Totemic Projection mid-fight** → keep them on the fight instead of re-dropping them.",
            "**Take Earthbound (Elemental, 21)** → Earthbind Totem roots nearby enemies for 5 seconds.",
            "Shamans went 19–11 vs other classes in the beta tournament finals and took 3rd and 4th.",
        ],
    },
    "Mage": {
        "leveling": [
            "**Plan smaller pulls than the old AoE kites** → Cone of Cold is shorter, so huge kite-pulls are riskier.",
            "**Learn Comprehension, the new minor tradeskill** → you can read the scrolls monsters drop.",
            "**Frost Nova, then Ice Lance** → Ice Lance hits frozen targets for big damage.",
        ],
        "pvp": [
            "**Root first, then Ice Lance on Fingers of Frost** → that combo is your burst window.",
            "**Undead Mages: hold Will of the Forsaken for Warlock fears** → that's the fight you'll see most.",
            "Mages went 4–12 vs other classes in the beta tournament finals, and all four lost in the same round.",
        ],
    },
    "Warlock": {
        "leveling": [
            "**Grab your free mount at 40 from Strahad Farsan in Ratchet** → save the gold for training and gear.",
            "**Let Drain Soul finish its ticks** → it guarantees a Soul Shard if it runs long enough.",
            "**Stack some Spirit** → Life Tap scales with it, so you sit to drink less.",
        ],
        "pvp": [
            "**Plan your fight around Fear getting answered** → Undead Will of the Forsaken it and every Priest has Fear Ward, so don't open with it.",
            "Warlocks went 26–7 vs other classes in the beta tournament finals and took 1st and 2nd. That was level-30 dueling; at 60, more trinkets and Fear answers will change things.",
        ],
    },
    "Druid": {
        "leveling": [
            "**Drink potions and open doors without leaving form** → Feral stays in form instead of paying mana to shift back.",
            "**Keep upgrading your weapon as Feral** → weapons matter in forms now.",
            "**Tauren: War Stomp in bear form** → racials work while shapeshifted (90-second cooldown).",
        ],
        "pvp": [
            "**Barkskin without leaving form** → it works while shapeshifted now.",
            "**Root indoors too** → Entangling Roots works inside buildings and caves now.",
            "Druids went 12–14 vs other classes in the beta tournament finals; Minpojke finished top 6.",
        ],
    },
}
for _c, _parts in _DO.items():
    CLASSES[_c].update(_parts)


# 1.5: Alliance support. Race lists per Method's Forever race/class table (Dwarf Shaman, Human Hunter,
# Gnome Priest and Alliance Skyborne Mage are new). Racials per Warcraft Tavern's racial ability guide
# (Oct 2026). Class cards pick lines by the server's faction; neutral servers see both race lists.
ALLIANCE = {
    "Warrior": {"races": "Human · Dwarf · Night Elf · Gnome · Skyborne",
                "pvp": ["**Human: save Will to Survive for the stun that matters** → it's a free PvP trinket on top of your real one."]},
    "Paladin": {"races": "Human · Dwarf",
                "role": "A plate-armored healer, tank or holy warrior. On Alliance, Humans and Dwarves can be Paladins.",
                "pvp": ["**Dwarf: hit Stoneform when you're poisoned or bleeding** → it clears those and toughens you up, and it's on its own cooldown."]},
    "Hunter": {"races": "Human (new) · Dwarf · Night Elf · Skyborne",
               "pvp": ["**Night Elf: Shadowmeld to drop a fight** → it pulls you out of sight, which resets a bad engagement or dodges an incoming attack."]},
    "Rogue": {"races": "Human · Dwarf · Night Elf · Gnome · Skyborne",
              "pvp": ["**Gnome: Escape Artist out of roots and slows** → stick to your target instead of watching them walk away.",
                      "**Human: use Perception against enemy Rogues** → it spots stealthers before they open on you."]},
    "Priest": {"races": "Human · Dwarf · Night Elf · Gnome (new)",
               "pvp": ["**Pick your race for its Priest spell** → every Alliance race gets a different one, like the Gnome's Confounding Flash crowd control or the Human's Divine Grace healing cooldown."]},
    "Shaman": {"races": "Dwarf (new: the first Alliance Shamans)",
               "role": "The hybrid: heal, throw lightning, or swing a big weapon, with totems that buff your group. New on Alliance: Dwarves can be Shamans.",
               "pvp": ["**Dwarf: pair Stoneform with your totems** → it shrugs off poisons and bleeds while you hold your ground."]},
    "Mage": {"races": "Human · Gnome · Skyborne (new)",
             "pvp": ["**Gnome: Escape Artist the moment you're rooted** → a free Mage is a dangerous Mage. Save Blink for the next one."]},
    "Warlock": {"races": "Human · Gnome",
                "pvp": ["**Human: Will to Survive breaks the stun, then Fear back** → it's a free PvP trinket, so you get two escapes."]},
    "Druid": {"races": "Night Elf · Skyborne",
              "pvp": ["**Night Elf: Shadowmeld out of combat to drink or reset** → it pairs well with travel and cat forms for picking your fights."]},
}
HORDE_ROLE = {"Shaman": None}  # Horde role text already lives in CLASSES


def class_view(cls: str, faction: str | None) -> dict:
    """The class card data for a server's faction: horde, alliance, or neutral (both race lists)."""
    base = dict(CLASSES[cls])
    a = ALLIANCE.get(cls, {})
    f = (faction or "neutral").lower()
    horde_pvp = list(base["pvp"])
    if f == "alliance":
        base["races_label"], base["races"] = "Alliance races", a.get("races", "")
        base["role"] = a.get("role", base["role"])
        # drop Horde-race tips (Undead's Will of the Forsaken) and add Alliance racial tips
        generic = [t for t in horde_pvp if not any(w in t for w in ("Undead", "Will of the Forsaken"))
                   or "Expect" in t or "answered" in t or "Scatter Shot" in t]
        base["pvp"] = a.get("pvp", [])[:2] + generic
        base["pvp_label"] = "⚔️ PvP (Alliance)"
    elif f == "horde":
        base["races_label"] = "Horde races"
        base["pvp_label"] = "⚔️ PvP (Horde)"
    else:
        base["races_label"] = "Races"
        c = lambda x: x.replace(" · ", ", ")
        base["races"] = f"Horde: {c(base['races'])} / Alliance: {c(a.get('races', ''))}"
        if cls == "Shaman":
            base["role"] = ALLIANCE["Shaman"]["role"].replace("New on Alliance: Dwarves can be Shamans.",
                                                              "New in Forever: Dwarf Shamans on Alliance and Skyborne Shamans on Horde.")
        base["pvp"] = horde_pvp + a.get("pvp", [])[:1]
        base["pvp_label"] = "⚔️ PvP"
    return base
