# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.
PRE1_11_RENAMES = {
    # Mob Entities
    "chest_minecart": "MinecartChest",
    "commandblock_minecart": "MinecartCommandBlock",
    "egg": "ThrownEgg",
    "ender_pearl": "ThrownEnderpearl",
    "falling_block": "FallingSand",
    "fireworks_rocket": "FireworksRocketEntity",
    "furnace_minecart": "MinecartFurnace",
    "hopper_minecart": "MinecartHopper",
    "horse": "EntityHorse",
    "magma_cube": "LavaSlime",
    "minecart": "MinecartRideable",
    "mooshroom": "MushroomCow",
    "ocelot": "Ozelot",
    "potion": "ThrownPotion",
    "spawner_minecart": "MinecartSpawner",
    "tnt": "PrimedTnt",
    "tnt_minecart": "MinecartTNT",
    "wither": "WitherBoss",
    "xp_bottle": "ThrownExpBottle",
    "xp_orb": "XPOrb",
    "zombie_pigman": "PigZombie",
    # Block Entities
    "brewing_stand": "Cauldron",
    "command_block": "Control",
    "daylight_detector": "DLDetector",
    "dispenser": "Trap",
    "enchanting_table": "EnchantTable",
    "end_portal": "AirPortal",
    "jukebox": "RecordPlayer",
    "noteblock": "Music",
    "structure_block": "Structure",
}


ENTITIES = {
    1: {
        "name": "item"
    }, 
    2: {
        "name": "xp_orb"
    }, 
    3: {
        "name": "area_effect_cloud"
    }, 
    4: {
        "name": "elder_guardian"
    }, 
    5: {
        "name": "wither_skeleton"
    }, 
    6: {
        "name": "stray"
    }, 
    7: {
        "name": "egg"
    }, 
    8: {
        "name": "leash_knot"
    }, 
    9: {
        "name": "painting"
    }, 
    10: {
        "name": "arrow"
    }, 
    11: {
        "name": "snowball"
    }, 
    12: {
        "name": "fireball"
    }, 
    13: {
        "name": "small_fireball"
    }, 
    14: {
        "name": "ender_pearl"
    }, 
    15: {
        "name": "eye_of_ender_signal"
    }, 
    16: {
        "name": "potion"
    }, 
    17: {
        "name": "xp_bottle"
    }, 
    18: {
        "name": "item_frame"
    }, 
    19: {
        "name": "wither_skull"
    }, 
    20: {
        "name": "tnt"
    }, 
    21: {
        "name": "falling_block"
    }, 
    22: {
        "name": "fireworks_rocket"
    }, 
    23: {
        "name": "husk"
    }, 
    24: {
        "name": "spectral_arrow"
    }, 
    25: {
        "name": "shulker_bullet"
    }, 
    26: {
        "name": "dragon_fireball"
    }, 
    27: {
        "name": "zombie_villager"
    }, 
    28: {
        "name": "skeleton_horse"
    }, 
    29: {
        "name": "zombie_horse"
    }, 
    30: {
        "name": "armor_stand"
    }, 
    31: {
        "name": "donkey"
    }, 
    32: {
        "name": "mule"
    }, 
    33: {
        "name": "evocation_fangs"
    }, 
    34: {
        "name": "evocation_illager"
    }, 
    35: {
        "name": "vex"
    }, 
    36: {
        "name": "vindication_illager"
    }, 
    40: {
        "name": "commandblock_minecart"
    }, 
    41: {
        "name": "boat"
    }, 
    42: {
        "name": "minecart"
    }, 
    43: {
        "name": "chest_minecart"
    }, 
    44: {
        "name": "furnace_minecart"
    }, 
    45: {
        "name": "tnt_minecart"
    }, 
    46: {
        "name": "hopper_minecart"
    }, 
    47: {
        "name": "spawner_minecart"
    }, 
    50: {
        "name": "creeper"
    }, 
    51: {
        "name": "skeleton"
    }, 
    52: {
        "name": "spider"
    }, 
    53: {
        "name": "giant"
    }, 
    54: {
        "name": "zombie"
    }, 
    55: {
        "name": "slime"
    }, 
    56: {
        "name": "ghast"
    }, 
    57: {
        "name": "zombie_pigman"
    }, 
    58: {
        "name": "enderman"
    }, 
    59: {
        "name": "cave_spider"
    }, 
    60: {
        "name": "silverfish"
    }, 
    61: {
        "name": "blaze"
    }, 
    62: {
        "name": "magma_cube"
    }, 
    63: {
        "name": "ender_dragon"
    }, 
    64: {
        "name": "wither"
    }, 
    65: {
        "name": "bat"
    }, 
    66: {
        "name": "witch"
    }, 
    67: {
        "name": "endermite"
    }, 
    68: {
        "name": "guardian"
    }, 
    69: {
        "name": "shulker"
    }, 
    90: {
        "name": "pig"
    }, 
    91: {
        "name": "sheep"
    }, 
    92: {
        "name": "cow"
    }, 
    93: {
        "name": "chicken"
    }, 
    94: {
        "name": "squid"
    }, 
    95: {
        "name": "wolf"
    }, 
    96: {
        "name": "mooshroom"
    }, 
    97: {
        "name": "snowman"
    }, 
    98: {
        "name": "ocelot"
    }, 
    99: {
        "name": "villager_golem"
    }, 
    100: {
        "name": "horse"
    }, 
    101: {
        "name": "rabbit"
    }, 
    102: {
        "name": "polar_bear"
    }, 
    103: {
        "name": "llama"
    }, 
    104: {
        "name": "llama_spit"
    }, 
    120: {
        "name": "villager"
    }, 
    200: {
        "name": "ender_crystal"
    }
}
