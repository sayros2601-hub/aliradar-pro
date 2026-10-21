# -*- coding: utf-8 -*-
"""
EXPANDED 110 VIRAL GADGET CATALOG COMPILER
Generates complete multilingual database (EN, HE, ES, RU) for SmartPick Deal Hub.
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")

# Categories definition across 4 languages
CATEGORIES = [
    {
        "id": "all",
        "icon": "⚡",
        "name": "כל המציאות",
        "name_i18n": {
            "en": "All Gadgets",
            "he": "כל המציאות",
            "es": "Todos los Chollos",
            "ru": "Все находки"
        }
    },
    {
        "id": "gadgets",
        "icon": "🚀",
        "name": "גאדג׳טים ופטנטים",
        "name_i18n": {
            "en": "Pocket Tech & EDC",
            "he": "גאדג׳טים ופטנטים",
            "es": "Gadgets y EDC",
            "ru": "Карманные гаджеты и EDC"
        }
    },
    {
        "id": "auto",
        "icon": "🚗",
        "name": "שדרוגים חכמים לרכב",
        "name_i18n": {
            "en": "Smart Car Tech",
            "he": "שדרוגים חכמים לרכב",
            "es": "Accesorios Coche",
            "ru": "Умные автотовары"
        }
    },
    {
        "id": "smarthome",
        "icon": "🏠",
        "name": "בית, מטבח וניקיון",
        "name_i18n": {
            "en": "Home & Kitchen",
            "he": "בית, מטבח וניקיון",
            "es": "Hogar y Cocina",
            "ru": "Дом, кухня и уборка"
        }
    },
    {
        "id": "tech",
        "icon": "🎧",
        "name": "אודיו, מטענים וציוד",
        "name_i18n": {
            "en": "Audio & Fast GaN",
            "he": "אודיו, מטענים וציוד",
            "es": "Sonido y Carga",
            "ru": "Аудио, GaN и сетапы"
        }
    },
    {
        "id": "pets",
        "icon": "🐾",
        "name": "המצאות לחיות מחמד",
        "name_i18n": {
            "en": "Clever Pet Tech",
            "he": "המצאות לחיות מחמד",
            "es": "Mascotas Listas",
            "ru": "Товары для питомцев"
        }
    },
    {
        "id": "tools",
        "icon": "🔧",
        "name": "כלי עבודה ותיקונים",
        "name_i18n": {
            "en": "Precision Tools",
            "he": "כלי עבודה ותיקונים",
            "es": "Herramientas",
            "ru": "Точный инструмент"
        }
    },
    {
        "id": "under10",
        "icon": "💰",
        "name": "מציאות עד ₪35",
        "name_i18n": {
            "en": "Under $10 Deals",
            "he": "מציאות עד ₪35",
            "es": "Menos de 10$",
            "ru": "Находки до $10"
        }
    }
]

SITE_META = {
    "title": "SmartPick // Curated Smart Gadgets & Trending Life Hacks",
    "description": "Discover problem-solving smart gadgets, auto innovations, home tech and verified AliExpress bargains with free shipping and duty-free under $75.",
    "domain": "https://smartpick-deals.com",
    "supported_languages": ["en", "he", "es", "ru"],
    "supported_currencies": ["USD", "ILS", "EUR", "RUB"]
}
