"""Rare-gadget discovery, anti-commodity stoplists, pre-search exclusivity, and 6-market verification."""
from __future__ import annotations

from datetime import datetime, timezone
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .policy import DETAIL, MARKETS, QUERY, normalize_product
from .search import HOT, _rows

ALL_MARKETS: tuple[str, ...] = MARKETS  # ('RU', 'US', 'BR', 'MX', 'IL', 'FR')
LANG_TO_MARKET: dict[str, str] = {
    'ru': 'RU',
    'en': 'US',
    'pt': 'BR',
    'es': 'MX',
    'fr': 'FR',
    'he': 'IL',
}

# Commodity household items, replacement parts, and generic clutter buyers already have everywhere.
COMMODITY_STOPLIST: frozenset[str] = frozenset({
    'cable', 'cables', 'charger', 'charging cable', 'usb cable', 'phone case', 'case',
    'cover', 'screen protector', 'tempered glass', 'adapter', 'plug adapter', 'extension cord',
    'earpads', 'watch band', 'strap', 'replacement', 'refill', 'spare', 'part', 'parts',
    'accessory', 'accessories', 'sleeve', 'casing', 'attachment', 'battery', 'batteries',
    'sticker', 'stickers', 'decal', 'decals', 'screw', 'screws', 'bolt', 'bolts', 'nut', 'nuts',
    'washer', 'gasket', 'o-ring', 'oring', 'sponge', 'towel', 'cloth', 'rag', 'hook', 'hooks',
    'keychain', 'keyring', 'pouch', 'bag', 'socks', 'apron', 'notebook', 'ballpoint',
    'lightbulb', 'bulb', 'fuse', 'filter cartridge', 'filter', 'filters', 'brush head', 'refills',
    'shoe lace', 'shoelace', 'hanger', 'hangers', 'toothpaste', 'cotton swab', 'cotton',
})

COMMODITY_PHRASE_RE = re.compile(
    r'\b(?:'
    r'phone\s+case|screen\s+protector|tempered\s+glass|charging\s+cable|usb\s+cable|'
    r'data\s+cable|power\s+cord|watch\s+band|watch\s+strap|ear\s*pads?|'
    r'plug\s+adapter|power\s+adapter|universal\s+adapter|travel\s+adapter|extension\s+cord|power\s+strip|'
    r'replacement\s+(?:part|head|filter|blade|pad|tips?|brush|battery)|'
    r'spare\s+parts?|adhesive\s+hook|wall\s+sticker|cleaning\s+cloth|'
    r'microfiber\s+towel|garbage\s+bag|trash\s+bag|ziplock|hair\s+tie|rubber\s+band'
    r')\b',
    re.IGNORECASE,
)

# High-curiosity, unusual gadgets ("things people do not already own at home") rotating across all 9 worlds & 6 markets.
CURATED_RARE_QUERIES: list[dict[str, Any]] = [
    {'key': 'rare_stirling_stove_fan', 'query': 'heat powered wood stove fan thermal', 'groups': (('stove', 'fireplace'), ('fan',)), 'category': 'Дом', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_endoscope_borescope', 'query': 'articulated usb borescope inspection camera', 'groups': (('borescope', 'endoscope'), ('camera',)), 'category': 'Техника', 'market': 'IL', 'theme': 'blue'},
    {'key': 'rare_ultrasonic_cleaner_pod', 'query': 'ultrasonic jewelry denture retainer cleaner pod', 'groups': (('ultrasonic',), ('cleaner',)), 'category': 'Уход', 'market': 'US', 'theme': 'lavender'},
    {'key': 'rare_gyro_powerball', 'query': 'auto start gyroscopic wrist ball exerciser', 'groups': (('gyro', 'gyroscopic', 'wrist'), ('ball',)), 'category': 'Спорт', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_gravity_spice_mill', 'query': 'gravity induction electric pepper grinder', 'groups': (('gravity',), ('grinder', 'mill')), 'category': 'Кухня', 'market': 'BR', 'theme': 'sand'},
    {'key': 'rare_obd_windshield_hud', 'query': 'car obd2 windshield head up display hud', 'groups': (('hud', 'head up'), ('car', 'obd', 'windshield')), 'category': 'В дороге', 'market': 'MX', 'theme': 'rose'},
    {'key': 'rare_contour_profile_gauge', 'query': 'contour gauge duplicator lock', 'groups': (('contour', 'profile'), ('gauge',)), 'category': 'Инструменты', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_plasma_arc_lighter', 'query': 'waterproof dual arc plasma lighter usb outdoor', 'groups': (('plasma', 'arc'), ('lighter',)), 'category': 'На природе', 'market': 'US', 'theme': 'blue'},
    {'key': 'rare_auto_rolling_pet_ball', 'query': 'smart automatic rolling interactive cat dog ball', 'groups': (('automatic', 'smart', 'interactive'), ('ball',)), 'category': 'Питомцы', 'market': 'IL', 'theme': 'lavender'},
    {'key': 'rare_laser_level_inclinometer', 'query': 'digital magnetic inclinometer angle cube gauge', 'groups': (('angle', 'inclinometer'), ('digital', 'gauge')), 'category': 'Инструменты', 'market': 'FR', 'theme': 'sand'},
    {'key': 'rare_vacuum_wine_preserver', 'query': 'electric vacuum wine bottle stopper preserver', 'groups': (('vacuum',), ('wine',)), 'category': 'Кухня', 'market': 'MX', 'theme': 'rose'},
    {'key': 'rare_uv_toothbrush_pod', 'query': 'portable uv toothbrush sanitizer travel case', 'groups': (('uv', 'uvc'), ('toothbrush',)), 'category': 'Уход', 'market': 'BR', 'theme': 'lavender'},
    {'key': 'rare_solar_crank_beacon', 'query': 'hand crank solar emergency weather radio lantern', 'groups': (('crank', 'solar'), ('radio', 'lantern')), 'category': 'На природе', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_pixel_desk_clock', 'query': 'smart pixel art desk clock ambient weather display', 'groups': (('pixel',), ('clock', 'display')), 'category': 'Техника', 'market': 'US', 'theme': 'blue'},
    {'key': 'rare_rapid_defrost_tray', 'query': 'defrosting tray thawing plate', 'groups': (('defrost', 'defrosting', 'thaw', 'thawing'), ('tray', 'plate', 'board')), 'category': 'Кухня', 'market': 'IL', 'theme': 'sand'},
    {'key': 'rare_turbine_air_duster', 'query': 'jet dry compressed air blower turbo duster fan', 'groups': (('turbo', 'jet'), ('duster', 'blower')), 'category': 'Техника', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_magnetic_vortex_mug', 'query': 'automatic magnetic self stirring insulated coffee mug', 'groups': (('magnetic', 'self stirring'), ('mug', 'cup')), 'category': 'Кухня', 'market': 'US', 'theme': 'rose'},
    {'key': 'rare_folding_camping_shower', 'query': 'rechargeable portable outdoor electric camping shower', 'groups': (('portable', 'electric'), ('shower',)), 'category': 'На природе', 'market': 'BR', 'theme': 'blue'},
    {'key': 'rare_tennis_ball_pressurizer', 'query': 'tennis padel ball pressurizer saver canister', 'groups': (('pressurizer', 'pressure'), ('tennis', 'padel')), 'category': 'Спорт', 'market': 'MX', 'theme': 'sand'},
    {'key': 'rare_digital_spoon_scale', 'query': 'digital gram measuring spoon lcd scale coffee', 'groups': (('spoon',), ('scale',)), 'category': 'Кухня', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_mini_thermal_printer', 'query': 'pocket inkless thermal bluetooth note printer', 'groups': (('thermal',), ('printer',)), 'category': 'Техника', 'market': 'BR', 'theme': 'lavender'},
    {'key': 'rare_timed_lock_vault', 'query': 'phone timer lock box', 'groups': (('timer', 'time'), ('lock', 'box')), 'category': 'Дом', 'market': 'IL', 'theme': 'rose'},
    {'key': 'rare_bike_laser_lane_light', 'query': 'bicycle rear taillight laser lane safety signal', 'groups': (('laser',), ('bicycle', 'bike', 'taillight')), 'category': 'Спорт', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_pet_grooming_vacuum', 'query': 'low noise pet nail grinder clipper led light', 'groups': (('nail', 'claw'), ('grinder',)), 'category': 'Питомцы', 'market': 'US', 'theme': 'sand'},
    {'key': 'rare_usb_voltage_analyzer', 'query': 'usb c digital power meter tester ammeter screen', 'groups': (('usb', 'type c'), ('tester', 'meter')), 'category': 'Техника', 'market': 'RU', 'theme': 'blue'},
    {'key': 'rare_auto_soap_foamer', 'query': 'touchless automatic infrared foaming soap dispenser', 'groups': (('touchless', 'automatic', 'sensor'), ('dispenser',)), 'category': 'Дом', 'market': 'MX', 'theme': 'coral'},
    {'key': 'rare_portable_tire_compressor', 'query': 'cordless digital air compressor car tire inflator', 'groups': (('inflator', 'compressor'), ('tire',)), 'category': 'В дороге', 'market': 'IL', 'theme': 'blue'},
    {'key': 'rare_infrared_pizza_thermometer', 'query': 'non contact infrared laser surface thermometer gun', 'groups': (('infrared',), ('thermometer',)), 'category': 'Кухня', 'market': 'FR', 'theme': 'sand'},
    {'key': 'rare_survival_filter_straw', 'query': 'personal hollow fiber emergency water filter straw', 'groups': (('water',), ('filter', 'straw')), 'category': 'На природе', 'market': 'MX', 'theme': 'coral'},
    {'key': 'rare_cordless_precision_driver', 'query': 'electric precision micro screwdriver magnetic bit set', 'groups': (('electric',), ('screwdriver',)), 'category': 'Инструменты', 'market': 'US', 'theme': 'lavender'},
    {'key': 'rare_hydroponic_herb_pod', 'query': 'smart indoor desktop hydroponic grow garden led', 'groups': (('hydroponic',), ('garden', 'grow')), 'category': 'Дом', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_sonic_brush_spinner', 'query': 'electric makeup brush cleaner spinner dryer', 'groups': (('makeup', 'brush'), ('cleaner', 'spinner')), 'category': 'Уход', 'market': 'RU', 'theme': 'rose'},
    {'key': 'rare_car_gap_caddy', 'query': 'car seat gap console organizer pocket usb', 'groups': (('gap',), ('seat', 'car', 'organizer')), 'category': 'В дороге', 'market': 'BR', 'theme': 'sand'},
    {'key': 'rare_visual_ear_otoscope', 'query': 'wifi visual ear cleaner camera led otoscope', 'groups': (('camera', 'visual', 'otoscope'), ('ear',)), 'category': 'Уход', 'market': 'IL', 'theme': 'lavender'},
    {'key': 'rare_cordless_electric_scissors', 'query': 'rechargeable electric rotary fabric cardboard scissors', 'groups': (('electric', 'cordless'), ('scissors', 'cutter')), 'category': 'Инструменты', 'market': 'BR', 'theme': 'coral'},
    {'key': 'rare_leakproof_dog_flask', 'query': 'portable dog water bottle dispenser outdoor cup', 'groups': (('dog', 'pet'), ('bottle', 'water')), 'category': 'Питомцы', 'market': 'MX', 'theme': 'blue'},
    # Expanded evergreen rare-gadget pool (weighted toward underrepresented worlds: Outdoors, Care, Sports, Pets)
    {'key': 'rare_pocket_fire_bellows', 'query': 'collapsible stainless pocket fire bellows camping blowpipe', 'groups': (('bellows', 'blowpipe', 'blow'), ('fire', 'camping')), 'category': 'На природе', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_folding_titanium_stove', 'query': 'folding ultralight titanium wood burning camping stove', 'groups': (('folding', 'ultralight', 'portable'), ('stove', 'wood')), 'category': 'На природе', 'market': 'US', 'theme': 'sand'},
    {'key': 'rare_magnetic_hand_warmer', 'query': 'magnetic split rechargeable electric hand warmer pocket', 'groups': (('hand',), ('warmer',)), 'category': 'На природе', 'market': 'FR', 'theme': 'coral'},
    {'key': 'rare_folding_solar_panel', 'query': 'foldable portable waterproof solar power panel hiking', 'groups': (('solar',), ('panel', 'power')), 'category': 'На природе', 'market': 'IL', 'theme': 'blue'},
    {'key': 'rare_hanging_tent_fan', 'query': 'rechargeable camping tent ceiling fan led lantern hook', 'groups': (('tent', 'camping'), ('fan',)), 'category': 'На природе', 'market': 'BR', 'theme': 'blue'},
    {'key': 'rare_dry_bag_compression', 'query': 'waterproof roll top dry bag kayak hiking pack', 'groups': (('dry', 'waterproof'), ('bag', 'sack')), 'category': 'На природе', 'market': 'MX', 'theme': 'sand'},
    {'key': 'rare_ultralight_camp_pillow', 'query': 'ultralight inflatable ergonomic camping travel air pillow', 'groups': (('inflatable', 'camping'), ('pillow',)), 'category': 'На природе', 'market': 'RU', 'theme': 'lavender'},
    {'key': 'rare_flint_compass_whistle', 'query': 'titanium emergency survival whistle compass flint tool', 'groups': (('survival', 'emergency'), ('whistle', 'flint')), 'category': 'На природе', 'market': 'US', 'theme': 'coral'},
    {'key': 'rare_cordless_water_flosser', 'query': 'portable cordless oral irrigator water flosser telescopic', 'groups': (('water', 'oral'), ('flosser', 'irrigator')), 'category': 'Уход', 'market': 'IL', 'theme': 'lavender'},
    {'key': 'rare_cryo_ice_roller', 'query': 'stainless steel cryo facial ice roller cooling massager', 'groups': (('ice', 'cryo'), ('roller', 'globe')), 'category': 'Уход', 'market': 'FR', 'theme': 'rose'},
    {'key': 'rare_heated_eyelash_curler', 'query': 'rechargeable heated electric eyelash curler temperature display', 'groups': (('heated', 'electric'), ('eyelash', 'lash')), 'category': 'Уход', 'market': 'BR', 'theme': 'rose'},
    {'key': 'rare_scalp_oil_applicator', 'query': 'liquid scalp oil applicator comb rolling ball dispenser', 'groups': (('scalp', 'oil'), ('applicator', 'comb')), 'category': 'Уход', 'market': 'MX', 'theme': 'lavender'},
    {'key': 'rare_electric_nasal_rinse', 'query': 'electric nasal irrigator sinus cleaner gentle mist', 'groups': (('nasal', 'sinus'), ('irrigator', 'cleaner')), 'category': 'Уход', 'market': 'RU', 'theme': 'blue'},
    {'key': 'rare_grip_dynamometer', 'query': 'digital electronic hand grip strength dynamometer lcd', 'groups': (('grip', 'hand'), ('dynamometer', 'strength')), 'category': 'Спорт', 'market': 'US', 'theme': 'blue'},
    {'key': 'rare_agility_reaction_ball', 'query': 'silicone hexagon agility reaction reflex training ball', 'groups': (('reaction', 'reflex', 'agility'), ('ball',)), 'category': 'Спорт', 'market': 'FR', 'theme': 'coral'},
    {'key': 'rare_wooden_balance_board', 'query': 'wooden wobble balance board core stability trainer', 'groups': (('balance', 'wobble'), ('board',)), 'category': 'Спорт', 'market': 'IL', 'theme': 'sand'},
    {'key': 'rare_forearm_wrist_roller', 'query': 'forearm wrist roller blaster weight strength trainer', 'groups': (('forearm', 'wrist'), ('roller', 'blaster')), 'category': 'Спорт', 'market': 'BR', 'theme': 'blue'},
    {'key': 'rare_foldable_pushup_board', 'query': 'foldable color coded multi position push up board', 'groups': (('push', 'pushup'), ('board', 'stand')), 'category': 'Спорт', 'market': 'MX', 'theme': 'coral'},
    {'key': 'rare_electrostatic_pet_roller', 'query': 'reusable electrostatic pet fur hair remover roller self cleaning', 'groups': (('pet', 'fur', 'hair'), ('roller', 'remover')), 'category': 'Питомцы', 'market': 'RU', 'theme': 'lavender'},
    {'key': 'rare_dog_puzzle_feeder', 'query': 'interactive sliding dog treat puzzle slow feeder board', 'groups': (('puzzle', 'interactive'), ('feeder', 'dog')), 'category': 'Питомцы', 'market': 'US', 'theme': 'sand'},
    {'key': 'rare_cat_window_hammock', 'query': 'suction cup cat window perch hammock seat', 'groups': (('cat',), ('hammock', 'perch')), 'category': 'Питомцы', 'market': 'FR', 'theme': 'rose'},
    {'key': 'rare_led_dog_collar', 'query': 'rechargeable waterproof led glowing safety dog collar', 'groups': (('led', 'glowing'), ('collar',)), 'category': 'Питомцы', 'market': 'IL', 'theme': 'blue'},
    {'key': 'rare_digital_torque_adapter', 'query': 'digital electronic torque wrench meter buzzer lcd', 'groups': (('digital', 'electronic'), ('torque',)), 'category': 'Инструменты', 'market': 'BR', 'theme': 'coral'},
    {'key': 'rare_ratchet_finger_wrench', 'query': 'mini thumb finger ratchet socket wrench tight space', 'groups': (('finger', 'thumb', 'mini'), ('ratchet', 'wrench')), 'category': 'Инструменты', 'market': 'MX', 'theme': 'sand'},
    {'key': 'rare_mezzaluna_herb_chopper', 'query': 'double blade stainless steel mezzaluna herb chopper rocking', 'groups': (('mezzaluna', 'rocking', 'herb'), ('chopper', 'knife')), 'category': 'Кухня', 'market': 'RU', 'theme': 'sand'},
    {'key': 'rare_collapsible_sink_colander', 'query': 'expandable collapsible silicone over sink strainer colander', 'groups': (('collapsible', 'expandable'), ('colander', 'strainer')), 'category': 'Кухня', 'market': 'US', 'theme': 'coral'},
    {'key': 'rare_flame_mist_diffuser', 'query': 'ultrasonic realistic flame effect essential oil air diffuser', 'groups': (('flame', 'fire'), ('diffuser', 'humidifier')), 'category': 'Дом', 'market': 'FR', 'theme': 'rose'},
    {'key': 'rare_car_escape_hammer', 'query': 'tungsten car window breaker seatbelt cutter safety hammer', 'groups': (('window', 'seatbelt'), ('breaker', 'hammer')), 'category': 'В дороге', 'market': 'IL', 'theme': 'coral'},
    {'key': 'rare_luggage_cup_holder', 'query': 'travel suitcase handle drink cup holder luggage caddy', 'groups': (('luggage', 'suitcase'), ('cup', 'drink')), 'category': 'В дороге', 'market': 'BR', 'theme': 'sand'},
    {'key': 'rare_pocket_thermal_camera', 'query': 'handheld infrared thermal imaging camera screen pcb', 'groups': (('thermal', 'infrared'), ('imaging', 'camera')), 'category': 'Техника', 'market': 'MX', 'theme': 'blue'},
]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r'[a-z0-9а-яё]+', (text or '').casefold()))


# Curated product types that already have a product of the same kind on the site, or one so close that a visitor
# would see a repeat (owner, 2026-11-14: "даже похожее что-то с таким товаром не нужно никогда"). Audited by hand
# against the English names and seller titles of all 96 products; newer repeats are caught by type_already_listed().
RETIRED_TYPES = frozenset({
    'rare_ultrasonic_cleaner_pod',      # find-051 Ultrasonic Cleaner
    'rare_gravity_spice_mill',          # find-065 Electric Gravity Salt & Pepper Grinder
    'rare_obd_windshield_hud',          # find-042 Car GPS HUD Speedometer Display
    'rare_uv_toothbrush_pod',           # find-057 UV Toothbrush Holder & Sanitizer
    'rare_tennis_ball_pressurizer',     # find-018 Tennis & Padel Ball Pressurizer
    'rare_mini_thermal_printer',        # find-059 Bluetooth Thermal Label Printer
    'rare_auto_soap_foamer',            # auto-1005010357329711 Touchless Foam Soap Dispenser
    'rare_portable_tire_compressor',    # find-060 / import-0074 tire inflators
    'rare_cordless_electric_scissors',  # find-035 Cordless Electric Rotary Scissors
    'rare_turbine_air_duster',          # import-0119 Cordless Electric Air Duster Blower
    'rare_hydroponic_herb_pod',         # find-048 hydroponic garden
    'rare_infrared_pizza_thermometer',  # find-002 kitchen thermometer: a second one is a repeat
    'rare_digital_spoon_scale',         # find-062 kitchen scale: a second one is a repeat
    'rare_pixel_desk_clock',            # find-039 LED matrix pixel panel
    'rare_bike_laser_lane_light',       # find-028 LED Bicycle Tail Light
    'rare_usb_voltage_analyzer',        # USB dongle: close to the cable/charger junk the site never shows
    'rare_endoscope_borescope',         # USB camera wire/probe: cousin of find-040 microscope & cable-like
    'rare_pet_grooming_vacuum',         # rotary claw grinder: cousin of find-011 nail drill
    'rare_car_gap_caddy',               # car seat organizer with USB: cousin of existing car mounts/organizers
    'rare_magnetic_vortex_mug',         # drink mixer: cousin of find-056 milk frother
    'rare_laser_level_inclinometer',    # digital angle meter: cousin of find-052 laser distance meter
})
# Fallback seed types that must never run: the owner treats anything cable-like as junk.
EXCLUDED_SEED_TYPES = frozenset({'cable_fish_tape'})
_STEM_SUFFIXES = ('ings', 'ing', 'ers', 'er', 'ies', 'es', 's', 'ed')


def _stem(word: str) -> str:
    for suffix in _STEM_SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)] + ('y' if suffix == 'ies' else '')
    return word


def _stem_words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r'[a-z0-9]+', (text or '').casefold())}


def type_already_listed(task: dict[str, Any], catalog_texts: list[str], used_task_keys: set[str]) -> bool:
    """True when this product type is already on the site: retired by hand, used before (sourceTask), or every word
    group of the task found (with plural/-ing forms folded) in an existing product's English name or seller title.
    Unlike matches_rare_query this ignores the commodity ban list, which made real repeats look new."""
    key = str(task.get('key') or '')
    if key in RETIRED_TYPES or key in EXCLUDED_SEED_TYPES or key in used_task_keys:
        return True
    groups = task.get('groups') or ()
    if not groups:
        return False
    stem_groups = [[[_stem(w) for w in str(term).casefold().split()] for term in group] for group in groups]
    for text in catalog_texts:
        words = _stem_words(text)
        if all(any(all(w in words for w in term) for term in group) for group in stem_groups):
            return True
    return False


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Normalized token overlap between two product titles or descriptions."""
    a = _tokens(text_a)
    b = _tokens(text_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_ordinary_or_banned_listing(title: str) -> tuple[bool, str | None]:
    """Reject everyday commodity basics, parts, cables, covers, and generic refill items."""
    clean = (title or '').strip()
    if len(clean) < 10:
        return True, 'title_too_short'
    if COMMODITY_PHRASE_RE.search(clean):
        return True, 'commodity_phrase'
    words = set(re.findall(r'[a-z0-9]+', clean.casefold()))
    # Single utility words like "replacement", "refill", "spare", "cable" disqualify non-complete items.
    strict_single_ban = {
        'replacement', 'refill', 'refills', 'spare', 'part', 'parts', 'accessory',
        'accessories', 'sticker', 'stickers', 'decal', 'decals', 'casing', 'sleeve',
        'earpads', 'shoelace', 'gasket', 'oring', 'o-ring', 'keychain', 'keyring',
        'socks', 'toothpaste', 'hanger', 'hangers', 'sponge', 'sponges', 'towel',
        'towels', 'rag', 'rags', 'ballpoint', 'notebook', 'apron', 'lightbulb',
    }
    hit = words & strict_single_ban
    if hit:
        return True, f'banned_token:{sorted(hit)[0]}'
    # Catch commodity cable/case/adapter listings unless paired with specialty diagnostic/novelty hardware.
    diagnostic_whitelist = {
        'borescope', 'endoscope', 'tester', 'analyzer', 'otoscope', 'scanner',
        'thermal', 'laser', 'ultrasonic', 'gyroscopic', 'stirling', 'sanitizer',
        'uv', 'uvc', 'inclinometer', 'microscope', 'oscilloscope', 'soldering',
        'telemetry', 'hud',
    }
    if {'cable', 'charger', 'adapter', 'case', 'cover'} & words and not (words & diagnostic_whitelist):
        return True, 'everyday_commodity_accessory'
    return False, None


def compatible_markets_for_title(title: str, candidate_markets: tuple[str, ...] | list[str] = ALL_MARKETS) -> list[str]:
    """Filter out countries whose mains voltage/plug standard conflicts with an explicit single-voltage title."""
    text = (title or '').casefold()
    markets = [m for m in candidate_markets if m in ALL_MARKETS]

    has_110 = bool(re.search(r'\b110\s*v\b|\b120\s*v\b|\bus\s+plug\b', text))
    has_220 = bool(re.search(r'\b220\s*v\b|\b230\s*v\b|\b240\s*v\b|\beu\s+plug\b', text))
    is_dual_voltage = any(tok in text for tok in (
        'bivolt', '100-240v', '100~240v', '110-240v', '110v-240v', '110-220v', '110v/220v',
    )) or (has_110 and has_220)

    if is_dual_voltage or (not has_110 and not has_220):
        return markets
    if has_110 and not has_220:
        # 110V-only mains device -> unsafe for 220V regions (RU, IL, FR) and mixed-grid BR.
        return [m for m in markets if m in ('US', 'MX')]
    if has_220 and not has_110:
        # 220V-only mains device -> unsuitable for 110-127V regions (US, MX) and 127V states in BR.
        return [m for m in markets if m in ('RU', 'IL', 'FR')]
    return markets


def parse_evaluate_rate(raw_val: Any) -> float | None:
    if raw_val is None:
        return None
    if isinstance(raw_val, (int, float)):
        return float(raw_val)
    match = re.search(r'(\d+(?:[.,]\d+)?)', str(raw_val))
    if not match:
        return None
    return float(match.group(1).replace(',', '.'))


def parse_volume(raw_val: Any) -> int | None:
    if raw_val is None or isinstance(raw_val, bool):
        return None
    if isinstance(raw_val, (int, float)):
        return int(raw_val)
    digits = re.sub(r'[^\d]', '', str(raw_val))
    return int(digits) if digits else None


def seller_quality_check(raw: dict[str, Any]) -> tuple[bool, str, float]:
    """Evaluate seller reliability & non-commodity niche sweet-spot without inventing missing metrics."""
    rate = parse_evaluate_rate(
        raw.get('evaluate_rate')
        or (raw.get('seller_metrics', {}) or {}).get('evaluate_rate', {}).get('raw_value')
    )
    volume = parse_volume(
        raw.get('lastest_volume')
        or (raw.get('seller_metrics', {}) or {}).get('lastest_volume', {}).get('raw_value')
    )
    if rate is not None and rate < 88.0:
        return False, f'low_seller_rating:{rate}', -100.0
    bonus = 0.0
    if rate is not None:
        bonus += min(10.0, max(0.0, (rate - 88.0) * 0.8))
    if volume is not None:
        if volume > 30000:
            return False, f'mass_commodity_volume:{volume}', -50.0
        if 15 <= volume <= 3500:
            bonus += 6.0
        elif volume == 0:
            bonus -= 2.0
    return True, 'ok', bonus


def matches_rare_query(task: dict[str, Any], title: str) -> bool:
    banned, _ = is_ordinary_or_banned_listing(title)
    if banned:
        return False
    words = set(re.findall(r'[a-z0-9]+', (title or '').casefold()))
    return all(
        any(all(w in words for w in group_term.split()) for group_term in group)
        for group in task['groups']
    )


PEAK_PUBLISH_SLOTS: tuple[dict[str, Any], ...] = (
    {
        'id': 'americas_prime',
        'cron': '0 1 * * *',
        'utc_hour': 1,
        'slot_target': 1,
        'preferred_markets': ('US', 'MX'),
        'window_note': 'US (17:00-21:00) & Mexico (19:00 CST) evening prime',
    },
    {
        'id': 'eurasia_prime',
        'cron': '0 17 * * *',
        'utc_hour': 17,
        'slot_target': 2,
        'preferred_markets': ('RU', 'IL', 'FR'),
        'window_note': 'Russia (20:00 MSK), Israel (19:00 IST) & France (18:00 CET) evening prime',
    },
    {
        'id': 'brazil_latam_prime',
        'cron': '0 21 * * *',
        'utc_hour': 21,
        'slot_target': 3,
        'preferred_markets': ('BR', 'US', 'MX'),
        'window_note': 'Brazil (18:00-19:00 BRT) prime & US/MX late afternoon',
    },
    {
        'id': 'americas_catchup',
        'cron': '30 22 * * *',
        'utc_hour': 22,
        'slot_target': 3,
        'preferred_markets': ('BR', 'MX', 'US', 'RU', 'IL', 'FR'),
        'window_note': 'Catch-up slot (19:30 BRT / 17:30 EST / 16:30 CST) only when done < 3',
    },
)


def resolve_peak_slot(
    now_utc: datetime | None = None,
    *,
    cron_expr: str | None = None,
    done_today: int = 0,
    daily_max: int = 3,
) -> dict[str, Any]:
    """Map the current cron/UTC window to one target-country wave adding at most 1 product."""
    instant = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    clean_cron = (cron_expr or '').strip()
    matched = next((slot for slot in PEAK_PUBLISH_SLOTS if clean_cron and slot['cron'] == clean_cron), None)
    if matched is None:
        hour = instant.hour
        if hour < 14:
            matched = PEAK_PUBLISH_SLOTS[0]
        elif hour < 20:
            matched = PEAK_PUBLISH_SLOTS[1]
        elif hour < 22:
            matched = PEAK_PUBLISH_SLOTS[2]
        else:
            matched = PEAK_PUBLISH_SLOTS[3]

    done = max(0, int(done_today))
    cap = max(0, int(daily_max))
    remaining_cap = max(0, cap - done)
    should_publish = done < matched['slot_target'] and remaining_cap > 0
    return {
        **matched,
        'utc_day': instant.date().isoformat(),
        'done_today': done,
        'add_count': 1 if should_publish else 0,
        'skip': not should_publish,
    }


def select_rotating_queries(
    now_ordinal: int,
    target_markets: tuple[str, ...] = ALL_MARKETS,
    pool: list[dict[str, Any]] | None = None,
    preferred_markets: tuple[str, ...] | list[str] | None = None,
) -> list[dict[str, Any]]:
    """Order curated queries so peak-window target markets come first without starving fallback markets."""
    # Types already on the site never enter the rotation (see RETIRED_TYPES).
    items = [q for q in (pool if pool is not None else CURATED_RARE_QUERIES) if q.get('key') not in RETIRED_TYPES]
    if not items:
        return []
    offset = now_ordinal % len(items)
    rotated = items[offset:] + items[:offset]
    buckets: dict[str, list[dict[str, Any]]] = {}
    for entry in rotated:
        mkt = entry.get('market', 'US')
        if mkt in target_markets:
            buckets.setdefault(mkt, []).append(entry)

    ordered: list[dict[str, Any]] = []
    pref = [m for m in (preferred_markets or ()) if m in target_markets]
    pref_set = set(pref)
    rotated_all = list(target_markets[now_ordinal % len(target_markets):] + target_markets[:now_ordinal % len(target_markets)])
    rest = [m for m in rotated_all if m not in pref_set]

    for wave in (pref, rest):
        if not wave:
            continue
        while any(buckets.get(m) for m in wave):
            for m in wave:
                lst = buckets.get(m)
                if lst:
                    ordered.append(lst.pop(0))
    return ordered


def fetch_hot_background_ids(call: Callable[[str, dict[str, str]], dict], query: str, market: str) -> tuple[set[str], list[str]]:
    """Pre-search check against AliExpress hot-products list to spot saturated commodity clones."""
    try:
        rows = _rows(
            call(
                HOT,
                {
                    'keywords': query.strip(),
                    'ship_to_country': market,
                    'target_currency': 'USD',
                    'target_language': 'EN',
                    'page_size': '20',
                    'tracking_id': 'default',
                },
            ),
            HOT,
        )
    except Exception:
        return set(), []
    hot_ids: set[str] = set()
    hot_titles: list[str] = []
    for r in rows[:20]:
        if isinstance(r, dict) and r.get('product_id'):
            hot_ids.add(str(r['product_id']))
            if r.get('product_title'):
                hot_titles.append(str(r['product_title']))
    return hot_ids, hot_titles


def default_web_presearch(query_title: str, *, timeout: float = 4.0) -> dict[str, Any]:
    """Optional lightweight web pre-search for market saturation check (non-blocking offline fallback)."""
    # Query DuckDuckGo Instant Answer JSON (public, zero-key) to verify if title matches common retail commodities.
    q = ' '.join(re.findall(r'[A-Za-z0-9]+', query_title)[:6])
    if not q:
        return {'checked': False, 'status': 'empty_query', 'saturated': False}
    url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote_plus(q) + '&format=json&no_redirect=1&no_html=1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'fluxixo-presearch/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read(200_000).decode('utf-8', 'replace')
        import json
        data = json.loads(payload)
        heading = str(data.get('Heading') or '')
        abstract = str(data.get('AbstractText') or '')
        # Note: a generic Wikipedia entry directly matching an everyday staple indicates mundane commodity rather than novel gadget.
        generic_signals = ('basic tool', 'everyday object', 'common household', 'stationery')
        saturated = any(sig in abstract.casefold() for sig in generic_signals)
        return {'checked': True, 'status': 'ok', 'heading': heading[:80], 'saturated': saturated}
    except Exception as exc:
        return {'checked': False, 'status': f'unavailable:{type(exc).__name__}', 'saturated': False}


def presearch_exclusivity_check(
    candidate: dict[str, Any],
    existing_items: list[dict[str, Any]],
    *,
    hot_ids: set[str] | None = None,
    hot_titles: list[str] | None = None,
    presearch_fn: Callable[[str], dict[str, Any]] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Run pre-publication uniqueness and non-commodity screening before downloading media."""
    title = str(candidate.get('title') or candidate.get('product_title') or '').strip()
    pid = str(candidate.get('product_id') or '')

    banned, ban_reason = is_ordinary_or_banned_listing(title)
    if banned:
        return False, f'rejected:{ban_reason}', {'stage': 'stoplist', 'reason': ban_reason}

    q_ok, q_reason, q_bonus = seller_quality_check(candidate)
    if not q_ok:
        return False, f'rejected:{q_reason}', {'stage': 'seller_quality', 'reason': q_reason}

    # Check semantic overlap against existing published catalog so we avoid clones of similar gadgets.
    for existing in existing_items:
        if not isinstance(existing, dict):
            continue
        for field in ('sourceTitle', 'name_en', 'name'):
            other = str(existing.get(field) or '').strip()
            if not other:
                continue
            sim = jaccard_similarity(title, other)
            if sim >= 0.58:
                return False, f'rejected:catalog_concept_duplicate:{existing.get("id", "")}', {
                    'stage': 'catalog_overlap',
                    'similarity': round(sim, 3),
                    'matched_id': existing.get('id', ''),
                }

    # Check AliExpress Hot Product flood: exact ID inside top commodity spam OR >=3 clones.
    hot_penalty = 0.0
    if hot_ids and pid in hot_ids:
        hot_penalty -= 8.0
    clone_hits = sum(1 for ht in (hot_titles or ()) if jaccard_similarity(title, ht) >= 0.60)
    if clone_hits >= 3:
        return False, 'rejected:hotproduct_commodity_saturation', {
            'stage': 'hot_saturation',
            'clone_hits': clone_hits,
        }

    presearch_info: dict[str, Any] = {'checked': False, 'status': 'not_run', 'saturated': False}
    if presearch_fn is not None:
        try:
            res = presearch_fn(title)
            if isinstance(res, dict):
                presearch_info = res
                if res.get('saturated'):
                    return False, 'rejected:web_presearch_ordinary', {'stage': 'web_presearch', **res}
        except Exception as exc:
            presearch_info = {'checked': False, 'status': f'error:{type(exc).__name__}', 'saturated': False}

    score = 10.0 + q_bonus + hot_penalty - (clone_hits * 1.5)
    return True, 'passed', {'score': round(score, 2), 'presearch': presearch_info}


def verify_markets_for_candidate(
    call: Callable[[str, dict[str, str]], dict],
    candidate: dict[str, Any],
    markets_to_check: tuple[str, ...] | list[str],
    utc_iso: str,
) -> dict[str, Any]:
    """Query AliExpress productdetail.get per market and enforce regional voltage/plug compatibility."""
    pid = str(candidate['product_id'])
    title = str(candidate.get('title') or '')
    primary_market = candidate.get('source', {}).get('queried_market') or candidate.get('market')
    voltage_ok = set(compatible_markets_for_title(title, tuple(markets_to_check)))

    confirmed: list[str] = []
    market_states = dict(candidate.get('markets') or {})
    if primary_market and market_states.get(primary_market, {}).get('sellable') == 'confirmed':
        if primary_market in voltage_ok:
            confirmed.append(primary_market)

    for market in markets_to_check:
        if market not in ALL_MARKETS:
            continue
        if market == primary_market and market in market_states:
            continue
        # One more try when the API errors: a country that did not answer is not a country that does not sell it
        # (2026-11-15: a cat ball sold in France was first recorded without France).
        for attempt in range(2):
            try:
                rows = _rows(
                    call(
                        DETAIL,
                        {
                            'product_ids': pid,
                            'country': market,
                            'target_currency': 'USD',
                            'target_language': 'EN',
                            'tracking_id': 'default',
                        },
                    ),
                    DETAIL,
                )
            except Exception:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                break
            try:
                matched = [r for r in rows[:20] if isinstance(r, dict) and str(r.get('product_id')) == pid]
                if matched:
                    norm = normalize_product(matched[0], market, DETAIL, utc_iso)
                    market_states[market] = norm['markets'][market]
                    if market in voltage_ok and market not in confirmed:
                        confirmed.append(market)
            except Exception:
                pass
            break

    # Preserve canonical order from ALL_MARKETS.
    ordered_confirmed = [m for m in ALL_MARKETS if m in confirmed]
    candidate['markets'] = market_states
    candidate['availableMarkets'] = ordered_confirmed
    return candidate


def generate_ai_discovery_queries(
    existing_items: list[dict[str, Any]],
    *,
    target_markets: tuple[str, ...] = ALL_MARKETS,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Optionally brainstorm fresh rare-gadget searches via Google AI Studio (direct or Worker transport)."""
    if limit <= 0 or not target_markets:
        return []
    try:
        from fluxixo_site.tools import ai_seo
    except Exception:
        return []
    try:
        if not ai_seo.has_ai_provider():
            return []
    except Exception:
        return []

    categories_order = ('Техника', 'Дом', 'Кухня', 'В дороге', 'Инструменты', 'Уход', 'Спорт', 'На природе', 'Питомцы')
    cat_counts: dict[str, int] = {c: 0 for c in categories_order}
    seen_sample: set[str] = set()
    recent_names: list[str] = []
    catalog_texts: list[str] = []
    used_task_keys: set[str] = set()
    for p in existing_items:
        if not isinstance(p, dict):
            continue
        c = str(p.get('category') or '').strip()
        if c in cat_counts:
            cat_counts[c] += 1
        tk = str(p.get('sourceTask') or '').strip()
        if tk:
            used_task_keys.add(tk)
        for field in ('name_en', 'sourceTitle', 'name'):
            val = str(p.get(field) or '').strip()
            if val:
                catalog_texts.append(val)
        label = str(p.get('name_en') or p.get('sourceTitle') or p.get('name') or '').strip()
        if label and label.casefold() not in seen_sample:
            seen_sample.add(label.casefold())
            recent_names.append(label[:65])

    # Keep prompt bounded regardless of catalog size (works at 100 or 5,000+ products) and steer toward sparse worlds.
    underrepresented = sorted(categories_order, key=lambda c: (cat_counts[c], c))[:4]
    bounded_recent = recent_names[:35]
    keyword_freq: dict[str, int] = {}
    stop_kw = {'with', 'for', 'and', 'the', 'mini', 'smart', 'portable', 'electric', 'digital', 'wireless', 'usb', 'led', 'auto', 'tool', 'kit', 'set'}
    for name in recent_names:
        for tok in re.findall(r'[a-z]{4,}', name.casefold()):
            if tok not in stop_kw:
                keyword_freq[tok] = keyword_freq.get(tok, 0) + 1
    top_existing_kw = [k for k, _ in sorted(keyword_freq.items(), key=lambda kv: (-kv[1], kv[0]))[:30]]

    sys_prompt = (
        'You curate unusual, genuinely clever non-everyday physical gadgets from AliExpress '
        'that people do NOT already own at home (kinetic/physics items, outdoor survival gear, '
        'clever compact tools, pet enrichment, specialty kitchen or care devices). Avoid common commodity cables, '
        'phone cases, stickers, screws, or spare parts. Reply strictly with JSON: '
        '{"queries":[{"query":"english 4-6 word query","keyword_required":"single core word","category":"Техника|Дом|Кухня|В дороге|Инструменты|Уход|Спорт|На природе|Питомцы"}]}'
    )
    user_prompt = (
        f'Catalog has {len(recent_names)} items. Prioritize these underrepresented categories: {underrepresented}. '
        f'Recent items to avoid repeating: {bounded_recent}. '
        f'Overused topics to skip: {top_existing_kw}. '
        f'Propose {limit} completely distinct gadget ideas.'
    )
    raw_obj = None
    try:
        raw_obj, _ = ai_seo.complete_json(sys_prompt, user_prompt)
    except Exception:
        raw_obj = None
    if not isinstance(raw_obj, dict) or not isinstance(raw_obj.get('queries'), list):
        return []

    categories = set(categories_order)
    themes = ('blue', 'coral', 'sand', 'lavender', 'rose')
    out: list[dict[str, Any]] = []
    seen_req: set[str] = set()
    for idx, q in enumerate(raw_obj['queries'][: max(limit * 2, limit)]):
        if len(out) >= limit:
            break
        if not isinstance(q, dict):
            continue
        text = str(q.get('query') or '').strip()
        req = re.sub(r'[^a-z0-9]', '', str(q.get('keyword_required') or '').casefold())
        cat = str(q.get('category') or 'Техника').strip()
        if not text or len(req) < 3 or req in seen_req or cat not in categories:
            continue
        banned, _ = is_ordinary_or_banned_listing(text)
        if banned:
            continue
        cand_task = {
            'key': 'ai_rare_' + req,
            'query': text[:100],
            'groups': ((req,),),
            'category': cat,
            'market': target_markets[len(out) % len(target_markets)],
            'theme': themes[len(out) % len(themes)],
        }
        # Programmatic dedup against 100% of existing catalog (never relies solely on LLM memory).
        if type_already_listed(cand_task, catalog_texts, used_task_keys):
            continue
        if any(jaccard_similarity(text, prev) >= 0.45 for prev in recent_names):
            continue
        seen_req.add(req)
        out.append(cand_task)
    return out


def _lazy_check_texts():
    try:
        from fluxixo_site.tools import check_texts
        return check_texts
    except ImportError:
        tools_dir = str((__import__('pathlib').Path(__file__).resolve().parents[1] / 'fluxixo_site/tools'))
        import sys
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import check_texts  # noqa: E402
        return check_texts


def pre_deploy_catalog_gate(
    prepared_items: list[dict[str, Any]],
    existing_catalog: list[dict[str, Any]],
    *,
    require_markets: bool = True,
    translations: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, list[str]]:
    """Final strict pre-publication audit before any newly prepared item can be committed/deployed."""
    errors: list[str] = []
    check_texts = _lazy_check_texts()
    seen_ids = {str(p.get('id') or '') for p in existing_catalog if isinstance(p, dict)}
    seen_source_ids = {str(p.get('sourceProductId') or '') for p in existing_catalog if isinstance(p, dict) and p.get('sourceProductId')}

    for item in prepared_items:
        pid = str(item.get('id') or '')
        spid = str(item.get('sourceProductId') or '')
        src_title = str(item.get('sourceTitle') or item.get('name') or '')
        name = str(item.get('name') or '')
        desc = str(item.get('description') or '')
        details = str(item.get('details') or '')
        if not pid or pid in seen_ids:
            errors.append(f'{pid}:duplicate_catalog_id')
        if spid and spid in seen_source_ids:
            errors.append(f'{pid}:duplicate_source_product_id')
        seen_ids.add(pid)
        if spid:
            seen_source_ids.add(spid)

        if len(name) > 62:
            errors.append(f'{pid}:title_too_long:{len(name)}')
        if any(check_texts.has_placeholder_copy(text) for text in (name, desc, details)):
            errors.append(f'{pid}:placeholder_copy_forbidden')

        banned, reason = is_ordinary_or_banned_listing(src_title)
        if banned:
            errors.append(f'{pid}:ordinary_or_banned:{reason}')

        avail = item.get('availableMarkets')
        if require_markets:
            if not isinstance(avail, list) or not avail or any(m not in ALL_MARKETS for m in avail):
                errors.append(f'{pid}:missing_verified_availableMarkets')
            else:
                compat = set(compatible_markets_for_title(src_title, tuple(avail)))
                if not compat or set(avail) - compat:
                    errors.append(f'{pid}:voltage_incompatible_market')

        if item.get('imageQualityVerified') is False:
            errors.append(f'{pid}:image_quality_not_verified')

        if desc and item.get('headline'):
            if translations is not None and pid in translations:
                lint_errs = check_texts.lint_product_bundle(pid, item, translations[pid], reject_placeholders=True)
            else:
                lint_errs = check_texts.lint_ru_product(item, reject_placeholders=True)
            for err in lint_errs:
                errors.append(f'{pid}:text_lint:{err}')

    return not errors, errors
