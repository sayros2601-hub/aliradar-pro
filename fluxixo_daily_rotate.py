#!/usr/bin/env python3
"""
Cloud Daily Accumulator & Builder for FLUXIXO (https://www.fluxixo.shop/).
Runs daily in GitHub Actions (100% cloud, PC off):
- NEVER deletes any existing products, images, or HTML pages from the catalog.
- Adds +3 new unique studio-cutout products every day at the front of the collection, continuously growing the catalog.
- Automatically replenishes reserve_pool.json via AliExpress Official API (AppKey 557652) + rembg studio cutout pipeline when reserve runs low.
- Rebuilds SEO pages, sitemap.xml, and hashed release bundle.
- Deploys to Cloudflare Pages (`dealvault` -> https://www.fluxixo.shop/).
"""
import argparse
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import urllib.parse
import urllib.request
from pathlib import Path
import requests

REPO_ROOT = Path(__file__).resolve().parent
SITE_ROOT = REPO_ROOT / "fluxixo_site" if (REPO_ROOT / "fluxixo_site").exists() else REPO_ROOT
DIST = SITE_ROOT / "dist"
RELEASE = SITE_ROOT / "release"
RESERVE_DIR = SITE_ROOT / "reserve"
RESERVE_IMAGES = RESERVE_DIR / "images"
RESERVE_ORIGINALS = RESERVE_DIR / "originals"

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "a4be28e05f73ad2b3939d364ea8b2817")
PROJECT_NAME = "dealvault"
API_URL = "https://api-sg.aliexpress.com/sync"

# Unique product discovery pool for automatic cloud replenishment when reserve_pool runs low
CLOUD_DISCOVERY_POOL = [
    ("find-060-tire-inflator", "portable cordless car tire inflator digital air compressor", "BR", "Бразилия", "Аккумуляторный компрессор", ["Воздух", "в дороге."], "В дороге", "Портативный компрессор с цифровым манометром и автостопом для подкачки шин автомобиля, мотоцикла или велосипеда.", "blue"),
    ("find-061-neck-massager", "smart pulse neck massager heating wireless portable", "ES", "Испания", "Импульсный массажёр шеи", ["Отдых", "для шеи."], "Уход", "Лёгкий дугообразный массажёр с прогревом и импульсными электродами для расслабления мышц шеи.", "coral"),
    ("find-062-coffee-scale", "digital espresso coffee scale timer pour over led", "FR", "Франция", "Кофейные весы с таймером", ["Точный", "пролив."], "Кухня", "Кухонные весы с секундомером и скрытым LED-экраном для заваривания фильтр-кофе и эспрессо.", "sand"),
    ("find-063-cable-tester", "network cable tester rj45 rj11 lan wire tracker", "BR", "Бразилия", "Тестер сетевого кабеля", ["Проверка", "линии."], "Инструменты", "Двухблочный прибор со светодиодной индикацией для быстрой прозвонки витой пары и патч-кордов.", "lavender"),
    ("find-064-book-light", "rechargeable amber book reading light clip on led", "ES", "Испания", "Клипса-фонарик для чтения", ["Тёплый", "свет страницы."], "Дом", "Миниатюрная лампа на гибкой ножке с прищепкой для чтения бумажных книг без нагрузки на глаза.", "rose"),
    ("find-065-spice-grinder", "electric gravity salt pepper grinder adjustable coarseness", "FR", "Франция", "Гравитационная мельница", ["Свежий", "помол."], "Кухня", "Электрическая мельница для соли и перца с керамическими жерновами и автоматическим включением при наклоне.", "blue"),
    ("find-066-shoe-dryer", "portable electric shoe dryer warmer sterilization folding", "BR", "Бразилия", "Сушилка для обуви", ["Сухая", "пара."], "Дом", "Складная электрическая сушилка с таймером и мягким обдувом для бережного ухода за обувью.", "coral"),
    ("find-067-pill-organizer", "weekly travel metal pill organizer waterproof case", "ES", "Испания", "Дорожный органайзер капсул", ["Порядок", "в мелочах."], "В дороге", "Герметичный секционный пенал из анодированного сплава для удобного хранения витаминов в поездке.", "sand"),
    ("find-068-screen-cleaner", "2 in 1 screen cleaner spray microfiber block phone laptop", "FR", "Франция", "Спрей-брусок для экранов", ["Чистый", "дисплей."], "Техника", "Компактный флакон-пульверизатор в оболочке из микрофибры для быстрой очистки экрана смартфона и ноутбука.", "lavender"),
    ("find-069-luggage-scale", "digital hanging luggage scale portable travel suitcase", "BR", "Бразилия", "Дорожный безмен для багажа", ["Точный", "вес чемодана."], "В дороге", "Карманные подвесные весы на прочном ремешке с ЖК-экраном для взвешивания чемоданов перед вылетом.", "rose"),
    ("find-070-milk-thermometer", "digital kitchen probe thermometer cooking liquid candy", "ES", "Испания", "Кулинарный щуп-термометр", ["Контроль", "градуса."], "Кухня", "Тонкий стальной термощуп с мгновенным откликом на цифровом дисплее для напитков, сиропов и выпечки.", "blue"),
    ("find-071-key-safe", "wall mounted combination key lock box weatherproof", "FR", "Франция", "Кодовый мини-сейф для ключей", ["Доступ", "по коду."], "Дом", "Настенный металлический бокс с кодовым замком и защитной крышкой для безопасного хранения запасных ключей.", "coral"),
    ("find-072-usb-tester", "usb c tester digital voltmeter ammeter power meter", "BR", "Бразилия", "USB-тестер тока и напряжения", ["Замер", "заряда."], "Техника", "Компактный прибор с цветным экраном показывает напряжение, ток и мощность зарядки через порт USB-C.", "sand"),
    ("find-073-cabinet-light", "rechargeable motion sensor under cabinet led light bar magnetic", "MX", "Мексика", "Светильник с датчиком движения", ["Свет", "по шагу."], "Дом", "Тонкая аккумуляторная LED-планка на магнитном креплении включается при движении в шкафу, на кухне или в коридоре.", "lavender"),
    ("find-074-oil-sprayer", "glass olive oil sprayer bottle kitchen cooking mister", "BR", "Бразилия", "Распылитель масла для кухни", ["Тонкий", "слой масла."], "Кухня", "Стеклянная бутылка с помпой распыляет масло мелким облаком для сковороды, салата, гриля и аэрогриля.", "rose"),
    ("find-075-seat-gap-organizer", "car seat gap filler organizer storage box cup holder", "MX", "Мексика", "Органайзер в щель у сиденья", ["Всё", "под рукой."], "В дороге", "Узкий карман-вставка между сиденьем и консолью автомобиля удерживает телефон, ключи, карты и мелочи.", "blue"),
    ("find-076-digital-caliper", "digital vernier caliper 150mm stainless steel lcd measuring tool", "BR", "Бразилия", "Цифровой штангенциркуль", ["Точность", "до сотых."], "Инструменты", "Стальной измерительный инструмент с ЖК-экраном для замера наружных и внутренних размеров и глубины деталей.", "coral"),
    ("find-077-scalp-massager", "electric scalp massager rechargeable head kneading waterproof", "MX", "Мексика", "Электрический массажёр для головы", ["Отдых", "для головы."], "Уход", "Беспроводной массажёр с вращающимися силиконовыми насадками мягко разминает кожу головы дома и в душе.", "sand"),
    ("find-078-hand-gripper", "adjustable hand grip strengthener counter forearm trainer", "BR", "Бразилия", "Кистевой эспандер со счётчиком", ["Крепкий", "хват."], "Спорт", "Пружинный тренажёр для кисти и предплечья с регулировкой нагрузки и механическим счётчиком сжатий.", "lavender"),
    ("find-079-camping-lantern", "rechargeable led camping lantern magnetic hook tent light", "MX", "Мексика", "Аккумуляторный кемпинговый фонарь", ["Свет", "в палатке."], "На природе", "Подвесной светодиодный фонарь с крючком, магнитом и несколькими режимами яркости для палатки и стоянки.", "rose"),
    ("find-080-paw-cleaner", "dog paw cleaner cup silicone portable pet foot washer", "BR", "Бразилия", "Лапомойка для собак", ["Чистые", "лапы."], "Питомцы", "Стакан с мягкими силиконовыми щетинками внутри помогает смыть грязь с лап собаки после прогулки.", "blue"),
    ("find-081-presenter-remote", "wireless presenter remote clicker usb powerpoint slide pointer", "MX", "Мексика", "Беспроводной пульт для презентаций", ["Слайды", "одним нажатием."], "Техника", "Компактный кликер с USB-приёмником переключает слайды и управляет показом презентации на расстоянии.", "coral"),
    ("find-082-soap-dispenser", "automatic touchless foaming soap dispenser rechargeable sensor", "BR", "Бразилия", "Сенсорный дозатор мыла", ["Пена", "без касаний."], "Дом", "Аккумуляторный диспенсер с инфракрасным датчиком выдаёт порцию мыльной пены, когда подносишь ладонь.", "sand"),
    ("find-083-spoon-scale", "digital measuring spoon scale kitchen gram electronic lcd", "MX", "Мексика", "Мерная ложка-весы", ["Грамм", "в ложке."], "Кухня", "Электронная ложка с ЖК-экраном на ручке взвешивает специи, муку, чай и другие сыпучие продукты.", "lavender"),
    ("find-084-sunshade-umbrella", "car windshield sun shade umbrella foldable front window", "BR", "Бразилия", "Зонт-шторка на лобовое стекло", ["Тень", "в салоне."], "В дороге", "Складной солнцезащитный экран раскрывается как зонт и закрывает лобовое стекло автомобиля на стоянке.", "rose"),
    ("find-085-magnetic-wristband", "magnetic wristband tool holder screws nails drill bits", "MX", "Мексика", "Магнитный браслет для крепежа", ["Винты", "на запястье."], "Инструменты", "Тканевый напульсник со встроенными магнитами удерживает саморезы, гвозди, биты и свёрла во время работы.", "blue"),
    ("find-086-makeup-mirror", "rechargeable led travel makeup mirror foldable lighted vanity", "BR", "Бразилия", "Складное зеркало с подсветкой", ["Ровный", "свет."], "Уход", "Компактное аккумуляторное зеркало со светодиодной рамкой и регулировкой яркости для макияжа в поездке.", "coral"),
    ("find-087-ab-roller", "ab roller wheel automatic rebound elbow support core trainer", "MX", "Мексика", "Ролик для пресса с возвратом", ["Сильный", "кор."], "Спорт", "Широкое колесо с пружинным возвратом и упорами для локтей для тренировки мышц пресса и спины дома.", "sand"),
    ("find-088-camping-hammock", "camping hammock with mosquito net portable nylon tree straps", "BR", "Бразилия", "Гамак с москитной сеткой", ["Сон", "под кронами."], "На природе", "Лёгкий нейлоновый гамак со встроенной сеткой от насекомых и стропами для крепления между деревьями.", "lavender"),
    ("find-089-lick-mat", "silicone pet lick mat suction cup slow feeder dog", "MX", "Мексика", "Коврик для слизывания", ["Вкусная", "пауза."], "Питомцы", "Силиконовый рельефный коврик на присосках занимает питомца лакомством во время купания или стрижки когтей.", "rose"),
    ("find-090-endoscope-camera", "usb c endoscope inspection camera waterproof led borescope cable", "BR", "Бразилия", "Гибкая камера-эндоскоп", ["Взгляд", "внутрь."], "Техника", "Тонкая водозащищённая камера на гибком кабеле с подсветкой для осмотра труб, моторов и узких полостей.", "blue"),
    ("find-091-sunrise-alarm", "sunrise alarm clock wake up light bedside nature sounds", "MX", "Мексика", "Будильник с имитацией рассвета", ["Мягкое", "утро."], "Дом", "Прикроватная лампа-будильник постепенно прибавляет яркость перед сигналом и проигрывает звуки природы.", "coral"),
    ("find-092-garlic-chopper", "mini electric garlic chopper usb rechargeable food processor", "BR", "Бразилия", "Мини-измельчитель чеснока", ["Быстрая", "нарезка."], "Кухня", "Компактный аккумуляторный чоппер с чашей и стальными ножами для чеснока, зелени, орехов и перца чили.", "sand"),
    ("find-093-travel-adapter", "universal travel adapter worldwide plug usb c charger international", "MX", "Мексика", "Универсальный дорожный адаптер", ["Розетка", "в любой стране."], "В дороге", "Переходник с выдвижными вилками разных стандартов и портами USB для зарядки устройств в путешествии.", "lavender"),
    ("find-094-electric-screwdriver", "mini electric precision screwdriver set rechargeable magnetic bits", "BR", "Бразилия", "Электрическая отвёртка для точных работ", ["Тонкая", "работа."], "Инструменты", "Аккумуляторная отвёртка-ручка с набором магнитных бит для ремонта телефонов, ноутбуков и мелкой техники.", "rose"),
    ("find-095-brush-cleaner", "electric makeup brush cleaner spinner dryer usb", "MX", "Мексика", "Очиститель кистей для макияжа", ["Чистые", "кисти."], "Уход", "Электрическое устройство с чашей и вращающейся насадкой промывает и подсушивает косметические кисти.", "blue"),
    ("find-096-weighted-hoop", "smart weighted hula hoop detachable links counter fitness", "BR", "Бразилия", "Обруч с грузом и счётчиком", ["Талия", "в движении."], "Спорт", "Разборный обруч из звеньев с грузиком на тросе и счётчиком оборотов для домашних кардиотренировок.", "coral"),
    ("find-097-camp-shower", "portable rechargeable camping shower pump outdoor handheld", "MX", "Мексика", "Портативный походный душ", ["Душ", "без водопровода."], "На природе", "Аккумуляторная помпа с лейкой и шлангом подаёт воду из ведра или канистры на даче, в кемпинге и на пляже.", "sand"),
    ("find-098-pet-water-bottle", "portable dog water bottle travel leak proof drinking cup", "BR", "Бразилия", "Дорожная поилка для собак", ["Вода", "на прогулке."], "Питомцы", "Бутылка с откидной чашей и кнопкой-клапаном позволяет напоить питомца на прогулке и слить остаток обратно.", "lavender"),
    ("find-099-mini-keyboard", "mini wireless keyboard touchpad 2.4g backlit handheld tv box", "MX", "Мексика", "Мини-клавиатура с тачпадом", ["Пульт", "с клавишами."], "Техника", "Карманная беспроводная клавиатура с сенсорной панелью и подсветкой для ТВ-приставок, ПК и проекторов.", "rose"),
    ("find-100-kinetic-doorbell", "wireless doorbell self powered no battery waterproof kinetic", "BR", "Бразилия", "Беспроводной звонок без батареек", ["Гость", "у двери."], "Дом", "Уличная кнопка вырабатывает энергию от нажатия и передаёт сигнал на приёмник в розетке с выбором мелодий.", "blue"),
    ("find-101-cold-brew-maker", "cold brew coffee maker glass pitcher mesh filter", "MX", "Мексика", "Кувшин для колд-брю", ["Холодный", "настой."], "Кухня", "Стеклянный кувшин с мелким сетчатым фильтром для приготовления холодного кофе и чая в холодильнике.", "coral"),
]


def call_ae_api(method: str, extra_params: dict, app_key: str, app_secret: str) -> dict:
    for attempt in range(4):
        time.sleep(1.5 + attempt)
        params = {
            "app_key": app_key,
            "method": method,
            "sign_method": "sha256",
            "timestamp": str(int(time.time() * 1000)),
            **extra_params,
        }
        sorted_str = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        sign = hmac.new(app_secret.encode("utf-8"), sorted_str.encode("utf-8"), hashlib.sha256).hexdigest().upper()
        params["sign"] = sign
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data)
        res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
        if "error_response" in res and res["error_response"].get("code") == "ApiCallLimit":
            time.sleep(2.5)
            continue
        return res
    return {}


def replenish_reserve_via_api(existing_ids: set, existing_names: set, reserve: list, needed: int = 3) -> list:
    app_key = os.environ.get("ALI_APP_KEY", "557652")
    app_secret = os.environ.get("ALI_APP_SECRET", "")
    if not app_secret:
        print("ALI_APP_SECRET not set; skipping cloud API replenishment.")
        return reserve

    from PIL import Image
    from rembg import remove, new_session

    session = new_session("u2net")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.aliexpress.com/",
    }
    RESERVE_IMAGES.mkdir(parents=True, exist_ok=True)
    RESERVE_ORIGINALS.mkdir(parents=True, exist_ok=True)

    added = 0
    for pid, kw, country, country_ru, name, headline, category, desc, theme in CLOUD_DISCOVERY_POOL:
        if pid in existing_ids or name in existing_names or any(r["id"] == pid for r in reserve):
            continue
        res = call_ae_api(
            "aliexpress.affiliate.product.query",
            {
                "keywords": kw,
                "target_currency": "USD",
                "target_language": "EN",
                "ship_to_country": country,
                "page_size": "5",
                "tracking_id": "default",
            },
            app_key,
            app_secret,
        )
        prods = (
            res.get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
            .get("result", {})
            .get("products", {})
            .get("product", [])
        )
        if not prods:
            continue
        p = prods[0]
        img_url = p.get("product_main_image_url")
        detail_url = p.get("product_detail_url", "").split("?")[0]
        promo_link = p.get("promotion_link")
        if detail_url:
            lres = call_ae_api(
                "aliexpress.affiliate.link.generate",
                {"promotion_link_type": "0", "source_values": detail_url, "tracking_id": "default"},
                app_key,
                app_secret,
            )
            links = (
                lres.get("aliexpress_affiliate_link_generate_response", {})
                .get("resp_result", {})
                .get("result", {})
                .get("promotion_links", {})
                .get("promotion_link", [])
            )
            if links and links[0].get("promotion_link"):
                promo_link = links[0]["promotion_link"]

        tmp_ref = RESERVE_DIR / f"{pid}_tmp.jpg"
        r = requests.get(img_url, headers=headers, timeout=20)
        r.raise_for_status()
        tmp_ref.write_bytes(r.content)

        img = Image.open(tmp_ref).convert("RGBA")
        cut = remove(img, session=session)
        r_ch, g_ch, b_ch, a_ch = cut.split()
        a_ch = a_ch.point(lambda px: 0 if px < 28 else px)
        cut.putalpha(a_ch)
        bbox = cut.getbbox()
        cropped = cut.crop(bbox) if bbox else cut
        w, h = cropped.size
        max_inner = int(1254 * 0.72)
        scale = min(max_inner / max(w, 1), max_inner / max(h, 1))
        nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
        resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (1254, 1254), (0, 0, 0, 0))
        canvas.paste(resized, ((1254 - nw) // 2, (1254 - nh) // 2), resized)
        tmp_png = RESERVE_DIR / f"{pid}_tmp.png"
        canvas.save(tmp_png, "PNG")

        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(tmp_png), "-c:v", "libwebp", "-quality", "92", str(RESERVE_IMAGES / f"{pid}.webp")],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(tmp_ref), "-c:v", "libwebp", "-quality", "88", str(RESERVE_ORIGINALS / f"{pid}.webp")],
            check=True,
        )
        tmp_ref.unlink(missing_ok=True)
        tmp_png.unlink(missing_ok=True)

        entry = {
            "id": pid,
            "name": name,
            "headline": headline,
            "category": category,
            "description": desc,
            "image": f"assets/images/{pid}.webp",
            "original": f"assets/originals/{pid}.webp",
            "imageNote": "Студийная ИИ-визуализация по фотографии продавца. Исходное фото доступно для сравнения; состав заказа уточняйте на AliExpress.",
            "affiliateUrl": promo_link or detail_url,
            "sourceUrl": promo_link or detail_url,
            "demo": False,
            "theme": theme,
            "scale": 0.85,
            "rotation": 0,
            "details": (
                f"{desc}\n\n"
                f"Студийное изображение — визуализация выбранного варианта. Исходная фотография продавца доступна ниже. "
                f"Комплектация, цвет, совместимость, характеристики, наличие и доставка определяются вариантом, выбранным на AliExpress."
            ),
            "facts": [{"label": "Подборка", "value": country_ru}],
        }
        reserve.append(entry)
        added += 1
        print(f"Cloud API harvested & cut out new reserve item: {pid}")
        if added >= needed:
            break
    return reserve


def accumulate_catalog(count: int) -> None:
    """
    Purely additive catalog update:
    Adds `count` new unique products before the previous collection.
    NEVER deletes any existing products, images, or HTML pages from the catalog.
    """
    cat_path = DIST / "js" / "catalog.js"
    reserve_path = RESERVE_DIR / "reserve_pool.json"
    catalog = json.loads(cat_path.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
    products = catalog["products"]
    reserve = json.loads(reserve_path.read_text(encoding="utf-8")) if reserve_path.exists() else []

    existing_ids = {p["id"] for p in products}
    existing_names = {p["name"] for p in products}
    reserve = [r for r in reserve if r["id"] not in existing_ids and r["name"] not in existing_names]

    if len(reserve) < count:
        reserve = replenish_reserve_via_api(existing_ids, existing_names, reserve, needed=count - len(reserve))

    if not reserve:
        print(f"No new reserve items to add today; keeping all {len(products)} existing products intact.")
        return

    incoming = reserve[:count]
    remaining_reserve = reserve[count:]

    (DIST / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (DIST / "assets" / "originals").mkdir(parents=True, exist_ok=True)

    for p in incoming:
        pid = p["id"]
        src_img = RESERVE_IMAGES / f"{pid}.webp"
        src_orig = RESERVE_ORIGINALS / f"{pid}.webp"
        if src_img.exists():
            shutil.copy2(src_img, DIST / "assets" / "images" / f"{pid}.webp")
            src_img.unlink()
        if src_orig.exists():
            shutil.copy2(src_orig, DIST / "assets" / "originals" / f"{pid}.webp")
            src_orig.unlink()

    # Always place the 3 newest products at positions #1, #2, #3 (index 0, 1, 2) and preserve ALL existing items!
    catalog["products"] = incoming + products
    cat_path.write_text(
        "/* FLUXIXO catalog: existing collection + daily accumulated finds. */\nwindow.MIRA_CATALOG = "
        + json.dumps(catalog, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    reserve_path.write_text(json.dumps(remaining_reserve, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Added +{len(incoming)} new products (0 deleted): {[p['id'] for p in incoming]}")
    print(f"Total products in catalog now: {len(catalog['products'])}")
    print(f"Remaining pre-rendered reserve items: {len(remaining_reserve)}")


def deploy_release() -> None:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        from deploy_to_cloudflare import get_token
        token = get_token()

    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = token
    env["CLOUDFLARE_ACCOUNT_ID"] = ACCOUNT_ID

    cmd = "npx.cmd" if os.name == "nt" else "npx"
    subprocess.run(
        [
            cmd,
            "wrangler",
            "pages",
            "deploy",
            str(RELEASE),
            f"--project-name={PROJECT_NAME}",
            "--branch=main",
            "--commit-dirty=true",
            "--commit-message=Deploy FLUXIXO release",
        ],
        env=env,
        check=True,
    )



def submit_indexnow() -> None:
    """Push all canonical URLs from sitemap.xml to IndexNow (Bing, Yandex, Naver, Seznam)."""
    key_file = SITE_ROOT / "tools" / "indexnow-key.txt"
    sitemap_file = DIST / "sitemap.xml"
    if not key_file.exists() or not sitemap_file.exists():
        return
    key = key_file.read_text(encoding="utf-8").strip()
    urls = [loc.text for loc in ET.parse(sitemap_file).findall(".//{*}loc") if loc.text]
    # Search engines ask for changed pages only; resubmitting the whole site every run gets the signal ignored.
    state_file = SITE_ROOT / "tools" / "search-build-state.json"
    if state_file.exists():
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=36)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        recent = {
            "https://www.fluxixo.shop" + path
            for path, entry in state.items()
            if datetime.fromisoformat(entry["lastmod"]) >= cutoff
        }
        urls = [url for url in urls if url in recent]
    if not urls:
        print("IndexNow: no pages changed, nothing to submit.")
        return
    payload = {
        "host": "www.fluxixo.shop",
        "key": key,
        "keyLocation": f"https://www.fluxixo.shop/{key}.txt",
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    for endpoint in ["https://api.indexnow.org/indexnow", "https://yandex.com/indexnow"]:
        try:
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "FLUXIXO-SEO-Bot/2.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                print(f"IndexNow ({endpoint}): HTTP {resp.status} for {len(urls)} URLs")
        except urllib.error.HTTPError as e:
            print(f"IndexNow ({endpoint}): HTTP {e.code} for {len(urls)} URLs")
        except Exception as e:
            print(f"IndexNow ({endpoint}) warning: {e}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rotate", "--add", dest="add_count", type=int, default=3, help="Number of new products to add (0 to rebuild only)")
    parser.add_argument("--deploy", action="store_true", help="Deploy to Cloudflare Pages")
    args = parser.parse_args()

    if args.add_count > 0:
        accumulate_catalog(args.add_count)

    # Price and rating come from the official API; a failure here never blocks the release.
    subprocess.run([sys.executable, str(SITE_ROOT / "tools" / "refresh_offers.py")], check=False)
    subprocess.run([sys.executable, str(SITE_ROOT / "tools" / "build_search.py")], check=True)
    subprocess.run([sys.executable, str(SITE_ROOT / "build_release.py")], check=True)
    # A release with broken pages stops here instead of reaching the live site.
    subprocess.run([sys.executable, str(SITE_ROOT / "tools" / "verify_release.py"), str(RELEASE)], check=True)

    if args.deploy:
        deploy_release()
        submit_indexnow()


if __name__ == "__main__":
    main()
