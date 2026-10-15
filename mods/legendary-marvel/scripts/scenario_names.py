"""Name matching shared by the build (Python) and the in-game browser (Lua scnNorm must do exactly the same steps).

norm(): lower-case, '&' -> 'and', punctuation removed, the word 'the' dropped, 'doctor' -> 'dr', spaces removed.
ALIASES maps a name as printed in the Marvel History scenarios PDF to the name of the library deck, for the cases where
the two differ in spelling or in how the team is written. Only mappings that are certain from the deck tags are listed."""
import re


def norm(s):
    s = ' ' + s.lower().replace('&', ' and ') + ' '
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    for _ in range(2): s = s.replace(' the ', ' ')
    s = s.replace(' doctor ', ' dr ')
    return s.replace(' ', '')


ALIASES = {
    'heroes': {
        'Wolverine X-Men': 'Wolverine',            # Core Wolverine carries the XMen tag
        'Wolverine X-Force': 'XForce Wolverine',
        'Beast X-Men': 'XMen Beast',
        'Beast Illuminati': 'Beast',               # Secret Wars V2 Beast carries the Illuminati tag
        'Venom Venomverse': 'Venom',
        'Skaar Son of Hulk': 'Skarr Son Of Hulk',
        'Steve Rogers Director of SHIELD': 'Steve Rodgers Director Of SHIELD',
        'Winter Solider': 'Winter Soldier',
        'Hulking': 'Hulkling',
        'Dr. Punisher Soldier Supreme': 'Dr Punisher The Soldier Supreme',
        'Deadpool Mercs for Money': 'Deadpool Deadpool',   # the Deadpool expansion's Deadpool (tag Mercs For Money)
        'Deadpool Merc for Money': 'Deadpool Deadpool',
        'Daredevil Iron Fist': 'Danny Rand Daredevil',
        'Captain and Devil Dinosaur': 'The Captain And The Devil',
        'Prof. X': 'Professor X',
        'Vison': 'Vision',
        'Hirioim': 'Hiroim',
        'Captain America Secret Avengers': 'Captain America Secret Avenger',
        'Steve Rogers Director of SHIED': 'Steve Rodgers Director Of SHIELD',
        'Wolverine Force': 'XForce Wolverine',
        'Kraven the Hunter': 'Kraven',
    },
    'villains': {
        'Four Horseman': 'Four Horsemen',
        'Dark Descendents': 'Dark Descendants',
        'Master of Evil WWII': 'Masters Of Evil WWII',
        'Hydra Marvel Studios': 'Hydra',
    },
    'henchmen': {
        'Maggia': 'Maggia Goons',
        'Sakaarian Hivelings': 'Sakaaran Hivelings',
        'Skaaran Hivelings': 'Sakaaran Hivelings',
        'Ten Rings Fanatic': 'Ten Rings Fanatics',
        'HYDRA Pilots': 'Hydra Pilots',
        'Cyctoplasm Spikes': 'Cytoplasm Spikes',
        "Shi'ar Death Commados": "Shi'ar Death Commandos",
        'Savage Land Mutate': 'Savage Land Mutates',
        'Hand Ninja': 'Hand Ninjas',
        'Asgardians Warriors': 'Asgardian Warriors',
        'Asgardian Warrior': 'Asgardian Warriors',
        'Khonshu Warriors': 'Khonshu Guardians',
    },
    'masterminds': {
        'Maria Hill': 'Maria Hill Director Of SHIELD',
        'Immortal Emperor Zhang Zhu': 'Immortal Emperor Zheng-Zhu',
        'King Hulk Sakaaron': 'King Hulk, Sakaarson',
        'Adrian Toomes, Vulture': 'Adrian Toomes',
    },
    'schemes': {
        'X-Men Danger Room Goes Berserk': 'X-Men Danger Room Goes Beserk',
        'Detonate the Hellicarrier': 'Detonate the Helicarrier',
        'Pull Reality in the Negative Zone': 'Pull Reality Into the Negative Zone',
        'Flood the Earth with Melted Glaciers': 'Flood the Planet with Melted Glaciers',
        'Mass Produce War Machine Amor': 'Mass Produce War Machine Armor',
        'Deadland Hordes Charge the Wall': 'Deadlands Hordes Charge the Wall',
        'Rescue Baby Hope': 'Capture Baby Hope',
        'Dark Alliance (3 players)': 'Dark Alliance',
        'Forge the Infinity Gauntlet - 3 players': 'Forge the Infinity Gauntlet',
        'The Dark Phoenix Saga (modified)': 'The Dark Phoenix Saga',
        'Transform Citizens into Demons (modified)': 'Transform Citizens into Demons',
        'Trap Heroes in the Multiverse': 'Trap Heroes in the Microverse',
        'Divine and Conquer': 'Divide and Conquer',
        'Resurrect Heroes with Norn Stones': 'Resurrect Heroes with the Norn Stones',
        'Destroy the Cities of Earth': 'Destroy the Cities of Earth!',
        'Portals to the Dark Dimensions': 'Portals to the Dark Dimension',
        'Secret Invasion of Skull Shapeshifters': 'Secret Invasion of the Skrull Shapeshifters',
        "Cage Villains in Power-Suppressing Cells": 'Cage Villains in Power Suppressing Cells',
        "Replace Earth's Leader's with Killbots": "Replace Earth's Leaders with Killbots",
        "Last Stand at Avengers' Tower": 'Last Stand at Avengers Tower',
        'Sinister Ambition': 'Sinister Ambitions',
    },
}


# Names that are in the printed card catalog but under another spelling or team label, and whose catalog set is not in the mod.
# Value = set the card comes from. (Not aliases to library decks: Venom Sinister Six is NOT the Venomverse Venom.)
CATALOG_SET_ALIASES = {
    'heroes': {'Venom Sinister Six': 'Villains', 'Kraven the Hunter': 'Villains', 'Dr. Octopus': 'Villains'},
    'villains': {}, 'henchmen': {}, 'masterminds': {}, 'schemes': {},
}

# Catalog set names that this mod already holds (Core plus the 22 expansion bags).
MOD_SETS = {'Legendary (First Edition)', 'Dark City', 'Fantastic Four', 'Paint the Town Red', 'Guardians of the Galaxy', 'Secret Wars Volume 1',
            'Secret Wars Volume 2', 'Captain America 75th Anniversary', 'Civil War', 'Deadpool', 'Noir', 'X-Men', 'Champions', 'World War Hulk',
            'Ant-Man', 'Venom', 'Dimensions', 'Revelations', 'S.H.I.E.L.D.', 'Heroes of Asgard', 'New Mutants', 'Into the Cosmos', 'Realm of Kings'}

# Sets the owner deliberately leaves out (MCU / What If tie-ins). Scenarios that need them are reported separately and never recommended.
EXCLUDED_SETS = {'Marvel Studios Phase 1', "Marvel Studios' Guardians of the Galaxy", 'Marvel Studios The Infinity Saga', 'Marvel Studios What If\u2026?',
                 'Ant-Man and the Wasp', 'Black Panther', 'Black Widow', 'Spider-Man Homecoming'}


# The Villains core set is written for a game in which you play the Villains. Its card text, translated for normal Legendary.
import re as _re
_TERMS = [
    (r'Backup Adversary groups', 'Henchmen groups'), (r'Backup Adversary group', 'Henchmen group'), (r'Backup Adversaries', 'Henchmen groups'), (r'Backup Adversary', 'Henchman'),
    (r'Adversary Deck', 'Villain Deck'), (r'Adversaries', 'Villains'), (r'Adversary', 'Villain'),
    (r'Commanders', 'Masterminds'), (r'Commander', 'Mastermind'), (r'Command Strike', 'Master Strike'),
    (r'Overrun Pile', 'Escape Pile'), (r'Overrun pile', 'Escape Pile'), (r'overruns', 'escapes'), (r'Overruns', 'Escapes'),
    (r'overrun', 'escape'), (r'Overrun', 'Escape'),
    (r'Plot Twists?', 'Scheme Twist'), (r'Plots', 'Schemes'), (r'Plot', 'Scheme'),
    (r'Ally Deck', 'Hero Deck'), (r'Allies', 'Heroes'), (r'Ally', 'Hero'), (r'Lair', 'HQ'),
    (r'Good Wins', 'Evil Wins'), (r'Bindings', 'Wounds'), (r'Binding', 'Wound'),
]


def to_normal_play(text):
    for pat, rep in _TERMS:
        text = _re.sub(r'\b' + pat + r'\b', rep, text)
    return text.replace('Henchmen group groups', 'Henchmen groups')


VILLAINS_GLOSSARY = "\n".join([
    "The Villains core set was written for a game in which you play the Villains. Its cards use the words below. In normal Legendary read them like this; the Plot and Commander text shown in Card Reference is already translated.",
    "- Adversary = Villain. Adversary Deck = Villain Deck. Adversary group = Villain group.",
    "- Backup Adversary = Henchman. A Backup Adversary group is a Henchmen group (S.H.I.E.L.D. Assault Squad, Cops, Multiple Man, Asgardian Warriors).",
    "- Commander = Mastermind. Command Strike = Master Strike. Commander Tactic = Mastermind Tactic.",
    "- Plot = Scheme. Plot Twist = Scheme Twist. Good Wins = Evil Wins.",
    "- Ally = Hero, the cards you recruit. Ally Deck = Hero Deck.",
    "- Lair = HQ. Overrun Pile = Escape Pile (the Escaped Villains). To overrun = to escape.",
    "- Bindings = Wounds.",
    "- Demolish, Elusive, X-Treme Attack and the other new keywords are explained in 'Villains Core Set Rules.pdf' in the Villains Core Set folder.",
    "- New Recruits, Madame HYDRA and the other Starting Cards belong to the Villains game and are not in this save.",
])
