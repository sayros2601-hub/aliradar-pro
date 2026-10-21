import os
import json
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
IMG_DIR = os.path.join(BASE_DIR, "assets", "img")
os.makedirs(IMG_DIR, exist_ok=True)

# Full 8 marketplace categories matching AliExpress department structure
CATEGORIES = [
    {"id": "all", "name": "כל המציאות", "name_i18n": {"he": "כל המציאות", "en": "All Deals", "ru": "Все находки", "es": "Todas", "fr": "Tous", "de": "Alle", "ar": "كل العروض"}, "icon": "🔥", "slug": "all"},
    {"id": "gadgets", "name": "גאדג׳טים והמצאות כיס", "name_i18n": {"he": "גאדג׳טים והמצאות כיס", "en": "Smart Inventions & EDC", "ru": "Гаджеты и EDC", "es": "Inventos y EDC", "fr": "Gadgets EDC", "de": "EDC Gadgets", "ar": "أجهزة ذكية محمولة"}, "icon": "⚡", "slug": "gadgets"},
    {"id": "auto", "name": "שדרוגים חכמים לרכב", "name_i18n": {"he": "שדרוגים חכמים לרכב", "en": "Car Gear & Auto Tech", "ru": "Автотовары и апгрейд", "es": "Accesorios Coche", "fr": "Auto & Conduite", "de": "Auto & Zubehör", "ar": "مستلزمات السيارات"}, "icon": "🚗", "slug": "auto"},
    {"id": "smarthome", "name": "בית, מטבח ומיקרו-המצאות", "name_i18n": {"he": "בית, מטבח ומיקרו-המצאות", "en": "Smart Home & Kitchen", "ru": "Дом, кухня и лайфхаки", "es": "Hogar y Cocina", "fr": "Maison & Cuisine", "de": "Heim & Küche", "ar": "المنزل والمطبخ"}, "icon": "🏠", "slug": "smarthome"},
    {"id": "pets", "name": "המצאות לחיות מחמד", "name_i18n": {"he": "המצאות לחיות מחמד", "en": "Clever Pet Tech", "ru": "Инновации для питомцев", "es": "Para Mascotas", "fr": "Animaux de Compagnie", "de": "Haustier-Gadgets", "ar": "مستلزمات الحيوانات"}, "icon": "🐾", "slug": "pets"},
    {"id": "tools", "name": "כלי עבודה ותיקונים", "name_i18n": {"he": "כלי עבודה ותיקונים", "en": "Precision Tools & Repair", "ru": "Точный инструмент", "es": "Herramientas", "fr": "Outils Précision", "de": "Werkzeuge", "ar": "أدوات الصيانة"}, "icon": "🔧", "slug": "tools"},
    {"id": "under10", "name": "מציאות גאוניות עד ₪50", "name_i18n": {"he": "מציאות גאוניות עד ₪50", "en": "Under $15 Brilliant Finds", "ru": "Хиты до 50 шекелей", "es": "Chollos < $15", "fr": "Pépites < 15$", "de": "Schnäppchen < 15$", "ar": "صفقات أقل من 50 شيكل"}, "icon": "💎", "slug": "under-50"},
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
            if len(data) > 500:
                with open(target_path, "wb") as out:
                    out.write(data)
                return True
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
    return False

print("Helper script ready.")
