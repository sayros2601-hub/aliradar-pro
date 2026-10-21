# -*- coding: utf-8 -*-
"""
Generates data/reserve_pool.json containing 35 high-converting viral reserve products.
5 products for each category: gadgets, auto, smarthome, tech, pets, tools, under10.
Includes image preview generation for each item.
"""
import os
import json
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMG_DIR = os.path.join(BASE_DIR, "assets", "img")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def ensure_img(filename, label, cat, icon="⚡"):
    path = os.path.join(IMG_DIR, filename)
    if not os.path.exists(path):
        img = Image.new("RGB", (600, 600), color=(14, 18, 30))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(20, 20), (580, 580)], radius=20, fill=(20, 26, 42), outline=(16, 185, 129), width=2)
        draw.rounded_rectangle([(40, 40), (560, 560)], radius=16, fill=(13, 17, 28))
        draw.text((60, 65), f"SMARTPICK // {cat.upper()}", fill=(16, 185, 129))
        draw.text((540, 65), "NEW TODAY ★ 4.9", fill=(255, 198, 0), anchor="ra")
        draw.rounded_rectangle([(90, 130), (510, 440)], radius=16, fill=(24, 32, 52), outline=(16, 185, 129), width=1)
        draw.text((300, 240), icon, fill=(255, 255, 255), anchor="mm")
        draw.text((300, 340), label[:28], fill=(255, 255, 255), anchor="mm")
        draw.rounded_rectangle([(180, 485), (420, 525)], radius=10, fill=(16, 185, 129))
        draw.text((300, 505), "DAILY DROP // CHOICE DEAL", fill=(10, 14, 26), anchor="mm")
        img.save(path, "JPEG", quality=92)
    return f"assets/img/{filename}"

RESERVE_PRODUCTS = [
  # GADGETS
  {
    'id': 'res-gad-01',
    'slug': 'ultralight-titanium-edc-pocket-multi-prybar',
    'category': 'gadgets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Ultra-Lightweight Titanium EDC Multi-Prybar & Bottle Opener',
    'title_i18n': {
      'en': 'Ultra-Lightweight Titanium EDC Multi-Prybar & Bottle Opener',
      'he': 'מוט חילוץ ופותחן כיס מטיטניום תעופתי EDC קל משקל',
      'es': 'Palanca EDC de Titanio Ultraligera con Abrebotellas',
      'ru': 'Титановый карманный EDC монтировка-мультитул с открывашкой'
    },
    'short_desc': 'Grade 5 aerospace titanium pocket multi-tool with bottle opener, pry edge, hex bit wrench, and pocket clip.',
    'short_desc_i18n': {
      'en': 'Grade 5 aerospace titanium pocket multi-tool with bottle opener, pry edge, hex bit wrench, and pocket clip.',
      'he': 'כלי כיס רב-תכליתי מטיטניום תעופתי דרגה 5 עם פותחן, מוט חילוץ, מפתח ברגים וקליפס לכיס.',
      'es': 'Multiherramienta de bolsillo de titanio grado 5 con palanca, abridor y clip.',
      'ru': 'Мультиинструмент из титана Grade 5 с монтировкой, открывалкой и клипсой.'
    },
    'price_usd': 9.85,
    'old_price_usd': 21.00,
    'discount_pct': 53,
    'rating': 4.9,
    'reviews_count': 342,
    'orders_count': 2190,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'titanium_edc_prybar.jpg',
    'icon': '🗡️',
    'highlights': ['Grade 5 Aerospace Titanium', 'Weighs only 34g', 'Hex Bit Driver slot', 'Integrated Pocket Clip'],
    'specs': {'Material': 'TC4 Titanium', 'Length': '105mm', 'Weight': '34g', 'Hardness': 'HRC 45+'}
  },
  {
    'id': 'res-gad-02',
    'slug': 'anti-loss-airtag-compatible-minimalist-rfid-wallet',
    'category': 'gadgets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Minimalist Aluminum Card Wallet with AirTag Slot & RFID Blocking',
    'title_i18n': {
      'en': 'Minimalist Aluminum Card Wallet with AirTag Slot & RFID Blocking',
      'he': 'ארנק כרטיסים מינימליסטי מאלומיניום עם חריץ ייעודי ל-AirTag וחסימת RFID',
      'es': 'Billetera Minimalista de Aluminio con Ranura AirTag y Bloqueo RFID',
      'ru': 'Минималистичный алюминиевый кошелек с отсеком AirTag и RFID-защитой'
    },
    'short_desc': 'Holds up to 12 cards with pop-up quick access trigger, integrated AirTag mount, and money band.',
    'short_desc_i18n': {
      'en': 'Holds up to 12 cards with pop-up quick access trigger, integrated AirTag mount, and money band.',
      'he': 'מחזיק עד 12 כרטיסים עם מנגנון שליפה מהירה בלחיצת כפתור, תושבת מובנית ל-AirTag ורצועת שטרות.',
      'es': 'Hasta 12 tarjetas con expulsión automática, soporte AirTag y banda para billetes.',
      'ru': 'До 12 карт с кнопкой быстрого выброса, креплением AirTag и резинкой для банкнот.'
    },
    'price_usd': 8.45,
    'old_price_usd': 19.90,
    'discount_pct': 57,
    'rating': 4.8,
    'reviews_count': 720,
    'orders_count': 4150,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'airtag_rfid_wallet.jpg',
    'icon': '💳',
    'highlights': ['Pop-Up Quick Card Trigger', 'Aviation Aluminum RFID Guard', 'Dedicated AirTag Bay', 'Slim 12mm Profile'],
    'specs': {'Material': 'Aviation 6061 Aluminum', 'Card Capacity': '1-12 Cards', 'RFID Guard': '13.56 MHz', 'Weight': '68g'}
  },
  {
    'id': 'res-gad-03',
    'slug': 'telescopic-self-defense-window-breaker-umbrella',
    'category': 'gadgets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Reinforced Stormproof Wind-Resistant Folding Umbrella with Tungsten Glass Breaker',
    'title_i18n': {
      'en': 'Reinforced Stormproof Wind-Resistant Folding Umbrella with Tungsten Glass Breaker',
      'he': 'מטריה מתקפלת מחוזקת עמידה בסופות עם 10 צלעות פיברגלס ושפיץ טונגסטן לניפוץ חלונות',
      'es': 'Paraguas Antiviento Reforzado 10 Varillas con Punta Rompecristales de Tungsteno',
      'ru': 'Штормовой ветрозащитный складной зонт с 10 спицами и вольфрамовым стеклобоем'
    },
    'short_desc': '10-rib fiberglass reinforced stormproof umbrella with Teflon waterproof coating and safety tungsten tip.',
    'short_desc_i18n': {
      'en': '10-rib fiberglass reinforced stormproof umbrella with Teflon waterproof coating and safety tungsten tip.',
      'he': 'מטריה עמידה לרוחות של עד 90 קמ"ש עם 10 צלעות פיברגלס גמישות, ציפוי טפלון דוחה מים ושפיץ חירום.',
      'es': 'Estructura de 10 varillas de fibra de vidrio resistente a rachas de viento y recubrimiento teflón.',
      'ru': 'Усиленный 10-спицевый каркас из фибергласа, тефлоновый водоотталкивающий купол и аварийный наконечник.'
    },
    'price_usd': 12.40,
    'old_price_usd': 28.00,
    'discount_pct': 55,
    'rating': 4.9,
    'reviews_count': 510,
    'orders_count': 3200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'stormproof_umbrella.jpg',
    'icon': '☂️',
    'highlights': ['10 Flexible Fiberglass Ribs', 'Teflon Hydrophobic Nano-Coating', 'Tungsten Carbide Emergency Breaker', 'Automatic 1-Touch Open/Close'],
    'specs': {'Diameter': '105cm', 'Ribs': '10 Glass-Fiber', 'Coating': '210T Teflon', 'Weight': '420g'}
  },
  {
    'id': 'res-gad-04',
    'slug': 'modular-magnetic-key-organizer-carbon-fiber',
    'category': 'gadgets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Silent Carbon Fiber Key Organizer with Quick-Release Magnetic Carabiner',
    'title_i18n': {
      'en': 'Silent Carbon Fiber Key Organizer with Quick-Release Magnetic Carabiner',
      'he': 'מארגן מפתחות שקט מסיבי פחמן אמיתי עם שאקל מגנטי לשחרור מהיר',
      'es': 'Organizador de Llaves Silencioso de Fibra de Carbono con Mosquetón Magnético',
      'ru': 'Бесшумный органайзер ключей из настоящего карбона с магнитным карабином'
    },
    'short_desc': 'Eliminates pocket key jingle, fits 2-10 keys securely with real 3K carbon fiber plates.',
    'short_desc_i18n': {
      'en': 'Eliminates pocket key jingle, fits 2-10 keys securely with real 3K carbon fiber plates.',
      'he': 'מבטל לחלוטין את רעש המפתחות בכיס, מחזיק 2-10 מפתחות בלוחות קרבון 3K קלים וחזקים במיוחד.',
      'es': 'Acaba con el ruido de llaves en los bolsillos, admite de 2 a 10 llaves con placas de carbono 3K.',
      'ru': 'Полностью устраняет звон ключей в кармане, вмещает от 2 до 10 ключей на пластинах из карбона 3K.'
    },
    'price_usd': 6.80,
    'old_price_usd': 15.50,
    'discount_pct': 56,
    'rating': 4.8,
    'reviews_count': 380,
    'orders_count': 2400,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'carbon_key_organizer.jpg',
    'icon': '🔑',
    'highlights': ['Real 3K Matte Carbon Fiber', 'Zero Pocket Jingle', 'Neodymium Quick Release', 'Fits 2-10 Standard Keys'],
    'specs': {'Material': '3K Real Carbon Fiber', 'Capacity': '2-10 Keys', 'Weight': '22g', 'Hardware': 'Stainless Steel'}
  },
  {
    'id': 'res-gad-05',
    'slug': 'ipx8-waterproof-floating-dry-phone-pouch-touchscreen',
    'category': 'gadgets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'IPX8 Certified Floating Waterproof Phone Pouch with Underwater HD Touchscreen',
    'title_i18n': {
      'en': 'IPX8 Certified Floating Waterproof Phone Pouch with Underwater HD Touchscreen',
      'he': 'נרתיק צף חסין מים IPX8 לטלפון עם חלון שקוף HD לתמונות ומסך מגע מתחת למים',
      'es': 'Funda Impermeable Flotante IPX8 para Móvil con Pantalla Táctil HD Subacuática',
      'ru': 'Плавающий водонепроницаемый чехол IPX8 для смартфона с HD-сенсором под водой'
    },
    'short_desc': 'Submersible to 30 meters with air-cushion floatation collar and ultra-sensitive TPU touch membrane.',
    'short_desc_i18n': {
      'en': 'Submersible to 30 meters with air-cushion floatation collar and ultra-sensitive TPU touch membrane.',
      'he': 'עמיד לצלילה עד 30 מטר, כרית אוויר מונעת שקיעה במים וממברנת TPU רגישה למסך מגע ומצלמה.',
      'es': 'Sumergible hasta 30m con borde inflable flotante y membrana sensible TPU.',
      'ru': 'Погружение до 30 метров, воздушная подушка от утопления и чувствительная TPU мембрана.'
    },
    'price_usd': 3.95,
    'old_price_usd': 9.90,
    'discount_pct': 60,
    'rating': 4.9,
    'reviews_count': 1250,
    'orders_count': 8900,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'waterproof_phone_pouch.jpg',
    'icon': '🌊',
    'highlights': ['IPX8 Certified 30m Depth', 'Air-Cushion Prevents Sinking', 'HD Optical Clear Lens Bay', 'Universal Fits Phones up to 7.2"'],
    'specs': {'Standard': 'IPX8 30m', 'Material': 'Optical Grade TPU', 'Phone Compatibility': 'Up to 7.2 inch', 'Collar': 'Air Buoyancy Ring'}
  },

  # AUTO
  {
    'id': 'res-auto-01',
    'slug': 'baseus-portable-car-vacuum-cleaner-15000pa',
    'category': 'auto',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Baseus 15,000Pa High-Power Cordless Handheld Car Vacuum Cleaner',
    'title_i18n': {
      'en': 'Baseus 15,000Pa High-Power Cordless Handheld Car Vacuum Cleaner',
      'he': 'שואב אבק נטען לרכב Baseus בעוצמת שאיבה 15,000Pa עם מנוע Brushless שקט',
      'es': 'Aspirador de Coche Inalámbrico Potente Baseus 15.000Pa con Motor Sin Escobillas',
      'ru': 'Беспроводной автомобильный пылесос Baseus 15000 Па с бесщеточным мотором'
    },
    'short_desc': '80,000 RPM brushless motor, HEPA washable filter, and 45-minute battery life in a compact metal cylinder.',
    'short_desc_i18n': {
      'en': '80,000 RPM brushless motor, HEPA washable filter, and 45-minute battery life in a compact metal cylinder.',
      'he': 'מנוע ללא מברשות 80,000 סל"ד, פילטר HEPA רחיץ, וסוללה המספיקה ל-45 דקות עבודה במבנה אלומיניום יוקרתי.',
      'es': 'Motor sin escobillas de 80.000 rpm, filtro HEPA lavable y hasta 45 minutos de autonomía.',
      'ru': 'Бесщеточный двигатель 80000 об/мин, моющийся HEPA-фильтр и до 45 минут автономной работы.'
    },
    'price_usd': 36.50,
    'old_price_usd': 75.00,
    'discount_pct': 51,
    'rating': 4.9,
    'reviews_count': 640,
    'orders_count': 3890,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'baseus_car_vacuum.jpg',
    'icon': '🧹',
    'highlights': ['15,000Pa Suction Power', '80,000 RPM Brushless Motor', 'Double Washable HEPA Filter', 'Type-C Fast Charging'],
    'specs': {'Suction': '15,000 Pa', 'Motor': 'Brushless 80K RPM', 'Battery': '4x2000mAh', 'Weight': '560g'}
  },
  {
    'id': 'res-auto-02',
    'slug': 'car-sunshade-umbrella-windshield-uv-heat-shield',
    'category': 'auto',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Titanium Silver Foldable Car Windshield Sunshade Umbrella with 99% UV Block',
    'title_i18n': {
      'en': 'Titanium Silver Foldable Car Windshield Sunshade Umbrella with 99% UV Block',
      'he': 'מטריית מגן שמש מתקפלת לשמשה קדמית ברכב בציפוי טיטניום כסוף דוחה 99% קרינת UV',
      'es': 'Parasol Plegable Tipo Paraguas para Parabrisas de Coche con Bloqueo UV 99%',
      'ru': 'Складной зонт-шторка на лобовое стекло автомобиля с защитой от солнца 99% UV'
    },
    'short_desc': 'Installs in 3 seconds like a regular umbrella, reflects heat keeping interior up to 30°C cooler.',
    'short_desc_i18n': {
      'en': 'Installs in 3 seconds like a regular umbrella, reflects heat keeping interior up to 30°C cooler.',
      'he': 'נפתחת בשלוש שניות כמו מטריה רגילה, מונעת התחממות ההגה והדשבורד ומורידה טמפרטורה בעד 30 מעלות.',
      'es': 'Se abre en 3 segundos, mantiene el volante y salpicadero frescos reduciendo hasta 30°C.',
      'ru': 'Раскрывается за 3 секунды, отражает солнечный жар и снижает температуру в салоне до 30°C.'
    },
    'price_usd': 9.20,
    'old_price_usd': 22.00,
    'discount_pct': 58,
    'rating': 4.8,
    'reviews_count': 1120,
    'orders_count': 6700,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'windshield_umbrella.jpg',
    'icon': '🛡️',
    'highlights': ['Installs in 3 Seconds', '99% UV & Heat Blocking Titanium Silver', 'Bendable 360° Handle Protects Dash', 'Fits Sedans, SUVs & Trucks'],
    'specs': {'Coating': 'Titanium Silver Cloth', 'Frame': '10 Steel Ribs', 'Folded Size': '32cm', 'Compatibility': 'Universal'}
  },
  {
    'id': 'res-auto-03',
    'slug': 'dual-port-super-fast-car-charger-120w-pd-qc',
    'category': 'auto',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': '120W Dual Port Fast Car Charger (Type-C PD 100W + USB-A QC 30W) with LED Voltage Display',
    'title_i18n': {
      'en': '120W Dual Port Fast Car Charger (Type-C PD 100W + USB-A QC 30W) with LED Voltage Display',
      'he': 'מטען רכב מהיר במיוחד 120W לשני מכשירים במקביל (100W Type-C למחשבים ניידים + 30W) עם מד מתח דיגיטלי',
      'es': 'Cargador Rápido de Coche 120W Doble Puerto (PD 100W + USB-A 30W) con Voltímetro LED',
      'ru': 'Быстрая автомобильная зарядка 120 Вт (PD 100W + USB-A 30W) с цифровым вольтметром'
    },
    'short_desc': 'Charges MacBook Pro, iPhone 16 and Galaxy at full speed simultaneously from 12V-24V socket.',
    'short_desc_i18n': {
      'en': 'Charges MacBook Pro, iPhone 16 and Galaxy at full speed simultaneously from 12V-24V socket.',
      'he': 'מטעין מחשב נייד מקבוק פרו, אייפון וגלקסי במהירות שיא בו-זמנית מכל שקע מצת ברכב.',
      'es': 'Carga portátiles MacBook, iPhone y Android a máxima potencia a la vez desde la toma de 12V-24V.',
      'ru': 'Заряжает ноутбуки MacBook, iPhone и Android на максимальной скорости одновременно.'
    },
    'price_usd': 11.50,
    'old_price_usd': 26.00,
    'discount_pct': 56,
    'rating': 4.9,
    'reviews_count': 940,
    'orders_count': 7200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'fast_car_charger_120w.jpg',
    'icon': '⚡',
    'highlights': ['100W Laptop PD Charging', 'Simultaneous Dual Fast Charge', 'Real-time Voltage Battery Monitor', 'All-Metal Heat Dissipating Shell'],
    'specs': {'Max Output': '120W', 'Type-C': '5V-20V/5A (100W Max)', 'USB-A': '30W Max', 'Input': 'DC 12-24V'}
  },
  {
    'id': 'res-auto-04',
    'slug': 'smart-solar-tire-pressure-monitoring-system-tpms',
    'category': 'auto',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Wireless Solar TPMS Car Tire Pressure Monitoring System with 4 External Sensors',
    'title_i18n': {
      'en': 'Wireless Solar TPMS Car Tire Pressure Monitoring System with 4 External Sensors',
      'he': 'מערכת ניטור לחץ אוויר וטמפרטורה בצמיגים TPMS סולארית אלחוטית עם 4 חיישנים חיצוניים',
      'es': 'Sistema Solar Inalámbrico de Monitorización de Presión de Neumáticos TPMS',
      'ru': 'Беспроводная солнечная система контроля давления в шинах TPMS с 4 датчиками'
    },
    'short_desc': 'Solar-powered dashboard HUD displays real-time tire pressure (PSI/BAR) and temperature with leak alarms.',
    'short_desc_i18n': {
      'en': 'Solar-powered dashboard HUD displays real-time tire pressure (PSI/BAR) and temperature with leak alarms.',
      'he': 'צג סולארי לדשבורד המציג בזמן אמת לחץ אוויר ומעלות חום בכל צמיג, כולל התראת דליפת אוויר מיידית.',
      'es': 'Pantalla solar que muestra presión y temperatura en tiempo real con alarmas de fuga.',
      'ru': 'Дисплей на солнечной батарее показывает точное давление и температуру в 4 колесах с сигнализацией утечки.'
    },
    'price_usd': 15.90,
    'old_price_usd': 34.00,
    'discount_pct': 53,
    'rating': 4.8,
    'reviews_count': 620,
    'orders_count': 3400,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'solar_tpms.jpg',
    'icon': '🛞',
    'highlights': ['Solar + USB Dual Powering', 'Real-time 4-Wheel Pressure & Temp', 'Instant Leak & High Temp Alert', 'Waterproof IP67 External Sensors'],
    'specs': {'Sensors': '4 External IP67', 'Units': 'BAR / PSI & °C / °F', 'Solar Panel': 'Monocrystalline', 'Battery': 'Rechargeable Lithium'}
  },
  {
    'id': 'res-auto-05',
    'slug': 'car-seat-gap-organizer-storage-box-dual-usb',
    'category': 'auto',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Premium Leather Car Seat Gap Catcher Organizer with Dual Fast USB Ports & Cup Holder',
    'title_i18n': {
      'en': 'Premium Leather Car Seat Gap Catcher Organizer with Dual Fast USB Ports & Cup Holder',
      'he': 'תא אחסון מעור למרווח בין המושבים ברכב עם מחזיק כוסות ושני שקעי טעינה מהירה USB',
      'es': 'Organizador para Hueco de Asiento de Coche de Cuero con Doble USB y Portavasos',
      'ru': 'Кожаный органайзер в щель между сиденьями авто с подстаканником и 2 USB-портами'
    },
    'short_desc': 'Prevents phones and keys from dropping down seat cracks while adding extra storage and phone charging.',
    'short_desc_i18n': {
      'en': 'Prevents phones and keys from dropping down seat cracks while adding extra storage and phone charging.',
      'he': 'מונע נפילת טלפונים ומפתחות מתחת למושב, מוסיף מקום נוח לכוס קפה, ארנק וטעינת מכשירים.',
      'es': 'Evita que caigan objetos entre los asientos a la vez que añade espacio de almacenaje y carga.',
      'ru': 'Не дает ключам и смартфонам падать в щель между сиденьями, добавляет место под напитки и зарядку.'
    },
    'price_usd': 9.90,
    'old_price_usd': 21.00,
    'discount_pct': 53,
    'rating': 4.8,
    'reviews_count': 810,
    'orders_count': 4900,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'seat_gap_organizer.jpg',
    'icon': '🚘',
    'highlights': ['Stops Dropped Phones & Keys', 'Dual Built-in USB Ports', 'Dedicated Cup Holder Compartment', 'Premium Scratch-Resistant PU Leather'],
    'specs': {'Material': 'PU Leather + ABS', 'Dimensions': '28 x 20 x 5 cm', 'Ports': '2x USB 5V/2.4A', 'Fit': 'Universal'}
  },

  # SMARTHOME
  {
    'id': 'res-smart-01',
    'slug': 'tuya-smart-wifi-ir-remote-controller-alexa-google',
    'category': 'smarthome',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Tuya Smart WiFi Universal IR Remote Control for AC, TV & Soundbar (Alexa & Google Home)',
    'title_i18n': {
      'en': 'Tuya Smart WiFi Universal IR Remote Control for AC, TV & Soundbar (Alexa & Google Home)',
      'he': 'שלט חכם אוניברסלי Tuya WiFi למיזוג אוויר, טלוויזיה ומערכות שמע — שליטה מרחוק מהנייד ופקודות קוליות',
      'es': 'Mando Universal WiFi IR Tuya para Aire Acondicionado, TV y Altavoces con Alexa y Google',
      'ru': 'Умный универсальный WiFi ИК-пульт Tuya для кондиционера, ТВ и техники с Alexa и Google'
    },
    'short_desc': 'Turns any regular infrared air conditioner and TV into smart devices controlled from your smartphone anywhere.',
    'short_desc_i18n': {
      'en': 'Turns any regular infrared air conditioner and TV into smart devices controlled from your smartphone anywhere.',
      'he': 'הופך כל מזגן וטלוויזיה רגילים למכשיר חכם הנשלט מכל מקום בעולם דרך אפליקציה ותזמונים אוטומטיים.',
      'es': 'Convierte cualquier televisor o aire acondicionado en inteligente para controlarlo desde el móvil.',
      'ru': 'Превращает обычные кондиционеры и телевизоры в умные устройства с управлением со смартфона.'
    },
    'price_usd': 5.80,
    'old_price_usd': 14.50,
    'discount_pct': 60,
    'rating': 4.9,
    'reviews_count': 1420,
    'orders_count': 9800,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'tuya_ir_remote.jpg',
    'icon': '📱',
    'highlights': ['Controls AC & TV from Anywhere', 'Voice Control via Alexa & Google', 'Automated Temperature Timers', '360° Multi-Directional Infrared Coverage'],
    'specs': {'App': 'Tuya / Smart Life', 'WiFi': '2.4GHz 802.11b/g/n', 'IR Range': '10 Meters', 'Power': 'Micro-USB 5V/1A'}
  },
  {
    'id': 'res-smart-02',
    'slug': 'ultrasonic-air-humidifier-essential-oil-diffuser-flame-light',
    'category': 'smarthome',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Realistic Flame Effect Ultrasonic Essential Oil Diffuser & Aromatherapy Humidifier',
    'title_i18n': {
      'en': 'Realistic Flame Effect Ultrasonic Essential Oil Diffuser & Aromatherapy Humidifier',
      'he': 'מפיץ ריח אולטרסוני ומכשיר אדים עם אפקט להבה מרהיב ותאורת אווירה חמה לחדר שינה וסלון',
      'es': 'Difusor de Aceites Esenciales Ultrasónico con Efecto Llama de Fuego y Luz Cálida',
      'ru': 'Ультразвуковой увлажнитель и аромадиффузор с реалистичным эффектом пламени камина'
    },
    'short_desc': 'Combines soothing mist and LED lighting to recreate a cozy fireplace flame while dispersing essential oils.',
    'short_desc_i18n': {
      'en': 'Combines soothing mist and LED lighting to recreate a cozy fireplace flame while dispersing essential oils.',
      'he': 'משלב אדים קרים ותאורת לד המדמה להבות אש אמיתיות לצד הפצת ניחוחות שמנים אתריים והפחתת יובש בחדר.',
      'es': 'Crea un ambiente cálido imitando llamas de chimenea con vapor frío ultrasónico y aceites aromáticos.',
      'ru': 'Создает уютную атмосферу камина с помощью холодного пара и подсветки, увлажняя воздух в комнате.'
    },
    'price_usd': 13.90,
    'old_price_usd': 32.00,
    'discount_pct': 57,
    'rating': 4.9,
    'reviews_count': 1850,
    'orders_count': 11400,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'flame_diffuser.jpg',
    'icon': '🔥',
    'highlights': ['Hypnotic Warm Flame Lighting Effect', 'Whisper-Quiet <28dB Ultrasonic Atomization', 'Auto Shut-Off Waterless Protection', 'Compatible with Essential Oils'],
    'specs': {'Capacity': '200ml', 'Atomization': '20-30ml/h', 'Noise': '<28dB', 'Power': 'USB Type-C 5V/2A'}
  },
  {
    'id': 'res-smart-03',
    'slug': 'smart-wireless-doorbell-camera-video-intercom-chime',
    'category': 'smarthome',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Wireless Smart WiFi Video Doorbell with 1080P HD Night Vision & Two-Way Intercom',
    'title_i18n': {
      'en': 'Wireless Smart WiFi Video Doorbell with 1080P HD Night Vision & Two-Way Intercom',
      'he': 'פעמון דלת חכם אלחוטי WiFi עם מצלמת וידאו 1080P HD, ראיית לילה ואינטרקום דו-כיווני לנייד',
      'es': 'Timbre Inteligente Inalámbrico con Cámara 1080P HD, Visión Nocturna e Intercomunicador',
      'ru': 'Беспроводной умный WiFi видеодомофон с камерой 1080P HD, ночным видением и интеркомом'
    },
    'short_desc': 'See and speak to visitors right from your phone, with motion detection alerts and free indoor wireless chime.',
    'short_desc_i18n': {
      'en': 'See and speak to visitors right from your phone, with motion detection alerts and free indoor wireless chime.',
      'he': 'ראו ושוחחו עם שליחים ומבקרים ישירות מהסמארטפון מכל מקום, עם התראת תנועה ופעמון פנימי כלול.',
      'es': 'Vea y hable con visitas desde su teléfono móvil con alertas de movimiento y timbre interior incluido.',
      'ru': 'Смотрите и разговаривайте с гостями и курьерами прямо с телефона, с датчиком движения и звонком в комплекте.'
    },
    'price_usd': 14.80,
    'old_price_usd': 35.00,
    'discount_pct': 58,
    'rating': 4.8,
    'reviews_count': 890,
    'orders_count': 5600,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'wifi_video_doorbell.jpg',
    'icon': '🔔',
    'highlights': ['Real-time 1080P HD Live Video', 'Infrared Auto Night Vision', 'Instant Push Notifications', 'Includes USB Indoor Chime'],
    'specs': {'Resolution': '1080P Full HD', 'Field of View': '125° Wide Angle', 'Wireless': '2.4GHz WiFi', 'Battery': 'Rechargeable 800mAh'}
  },
  {
    'id': 'res-smart-04',
    'slug': 'automatic-motion-sensor-trash-can-smart-kitchen-15l',
    'category': 'smarthome',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Touchless Smart Motion Sensor Trash Can (15L) with Odor Seal & Auto-Close Lid',
    'title_i18n': {
      'en': 'Touchless Smart Motion Sensor Trash Can (15L) with Odor Seal & Auto-Close Lid',
      'he': 'פח אשפה חכם 15 ליטר ללא מגע עם חיישן תנועה מהיר, אטימה מוחלטת לריחות ומכסה שקט',
      'es': 'Cubo de Basura Inteligente con Sensor de Movimiento 15L y Cierre Automático Antiolor',
      'ru': 'Умное сенсорное мусорное ведро 15 л с датчиком движения и защитой от запахов'
    },
    'short_desc': 'Opens hands-free in 0.3 seconds via wave or knee sensor, locks in odors with silicone rim seal.',
    'short_desc_i18n': {
      'en': 'Opens hands-free in 0.3 seconds via wave or knee sensor, locks in odors with silicone rim seal.',
      'he': 'נפתח אוטומטית תוך 0.3 שניות בתנועת יד או ברך, אוטם ריחות לא נעימים ונסגר בשקט מושלם.',
      'es': 'Apertura sin contacto en 0,3s al pasar la mano o rodilla con sellado hermético antiolores.',
      'ru': 'Открывается бесконтактно за 0,3 сек при взмахе руки или колена, надежно удерживает запахи.'
    },
    'price_usd': 16.40,
    'old_price_usd': 38.00,
    'discount_pct': 57,
    'rating': 4.8,
    'reviews_count': 560,
    'orders_count': 3400,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'sensor_trash_can.jpg',
    'icon': '🗑️',
    'highlights': ['0.3s Rapid Infrared Wave Detection', 'Silicone Airtight Odor Lock', 'IPX5 Waterproof Bathroom Safe', 'Slim 15-Liter Kitchen Capacity'],
    'specs': {'Capacity': '15 Liters', 'Sensor Distance': '25cm', 'Battery': 'Rechargeable USB / 2xAA', 'Rating': 'IPX5 Waterproof'}
  },
  {
    'id': 'res-smart-05',
    'slug': 'tuya-smart-soil-moisture-temperature-sensor-plants',
    'category': 'smarthome',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Zigbee / WiFi Smart Soil Moisture & Temperature Monitor for House Plants & Garden',
    'title_i18n': {
      'en': 'Zigbee / WiFi Smart Soil Moisture & Temperature Monitor for House Plants & Garden',
      'he': 'מד לחות וטמפרטורה חכם לאדמה ועציצים — התראות בנייד על השקיה נכונה ובריאות הצמחים',
      'es': 'Sensor Inteligente de Humedad y Temperatura de Suelo para Plantas y Huerto',
      'ru': 'Умный датчик влажности и температуры почвы для комнатных растений и сада'
    },
    'short_desc': 'Never overwater or dry out plants again; sends notifications to your phone when water levels drop.',
    'short_desc_i18n': {
      'en': 'Never overwater or dry out plants again; sends notifications to your phone when water levels drop.',
      'he': 'לא מייבשים ולא מציפים יותר עציצים — החיישן מתריע ישירות לטלפון בדיוק מתי צריך להשקות.',
      'es': 'Monitorea el estado de tus macetas y avisa al smartphone cuando hace falta regar.',
      'ru': 'Отслеживает влажность земли и присылает уведомление на телефон, когда цветок нужно полить.'
    },
    'price_usd': 7.60,
    'old_price_usd': 16.00,
    'discount_pct': 52,
    'rating': 4.9,
    'reviews_count': 410,
    'orders_count': 2600,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'smart_soil_sensor.jpg',
    'icon': '🌱',
    'highlights': ['Accurate Capacitive Moisture Probes', 'Tuya App Historical Graphs', 'Long 1-Year Battery Life', 'Stainless Corrosion-Proof Probes'],
    'specs': {'Protocol': 'Zigbee 3.0 / Tuya', 'Moisture Range': '0-100%', 'Temperature Range': '-10°C to 60°C', 'Battery': '2x AAA'}
  },

  # TECH
  {
    'id': 'res-tech-01',
    'slug': 'ugreen-revodok-7-in-1-usb-c-hub-4k60hz-100w-pd',
    'category': 'tech',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'UGREEN Revodok 7-in-1 USB-C Hub (4K@60Hz HDMI, 100W PD, Gigabit Ethernet, SD Reader)',
    'title_i18n': {
      'en': 'UGREEN Revodok 7-in-1 USB-C Hub (4K@60Hz HDMI, 100W PD, Gigabit Ethernet, SD Reader)',
      'he': 'מפצל רב-חיבורים מקצועי UGREEN Revodok 7-in-1 עם יציאת 4K 60Hz HDMI, טעינת 100W PD וכרטיס רשת גיגביט',
      'es': 'Hub USB-C 7 en 1 UGREEN Revodok (HDMI 4K@60Hz, 100W PD, Ethernet Gigabit, Lector SD)',
      'ru': 'Хаб USB-C 7-в-1 UGREEN Revodok (4K@60Hz HDMI, 100W PD, Gigabit LAN, SD-кардридер)'
    },
    'short_desc': 'Expands one USB-C port into full workstation: crystal clear 4K 60Hz display, fast pass-through charging, and 5Gbps USB.',
    'short_desc_i18n': {
      'en': 'Expands one USB-C port into full workstation: crystal clear 4K 60Hz display, fast pass-through charging, and 5Gbps USB.',
      'he': 'הופך חיבור USB-C בודד לעמדת עבודה מושלמת: מסך 4K 60Hz חלק ללא השהיות, טעינת מחשב מהירה והעברת קבצים 5Gbps.',
      'es': 'Convierte un puerto USB-C en una estación de trabajo completa con HDMI 4K 60Hz fluido y carga de 100W.',
      'ru': 'Расширяет порт Type-C в полноценную рабочую станцию: вывод 4K 60Hz, зарядка ноутбука 100W и скоростные порты.'
    },
    'price_usd': 21.90,
    'old_price_usd': 46.00,
    'discount_pct': 52,
    'rating': 4.9,
    'reviews_count': 1350,
    'orders_count': 8200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'ugreen_revodok_hub.jpg',
    'icon': '💻',
    'highlights': ['Ultra-Smooth 4K@60Hz Video Output', '100W Power Delivery Pass-Through', 'Gigabit RJ45 1000Mbps LAN', 'Premium Aluminum Dissipating Case'],
    'specs': {'HDMI': 'Up to 4K@60Hz', 'Power Delivery': '100W Max', 'Ethernet': '1000 Mbps RJ45', 'Card Reader': 'SD & MicroSD 104MB/s'}
  },
  {
    'id': 'res-tech-02',
    'slug': 'magnetic-cooling-fan-wireless-charger-gaming-phone',
    'category': 'tech',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Semiconductor Magnetic Phone Cooler & 15W Fast Wireless Charger with RGB Ambient Fan',
    'title_i18n': {
      'en': 'Semiconductor Magnetic Phone Cooler & 15W Fast Wireless Charger with RGB Ambient Fan',
      'he': 'מאוורר קירור מגנטי מוליך-למחצה לטלפון עם טעינה אלחוטית 15W ותאורת גיימינג RGB',
      'es': 'Enfriador Magnético Semiconductor para Móvil con Carga Inalámbrica 15W y RGB',
      'ru': 'Магнитный полупроводниковый кулер для смартфона с беспроводной зарядкой 15W и RGB'
    },
    'short_desc': 'Drops phone core temperature by up to 25°C in seconds while wirelessly fast charging during heavy gaming.',
    'short_desc_i18n': {
      'en': 'Drops phone core temperature by up to 25°C in seconds while wirelessly fast charging during heavy gaming.',
      'he': 'מוריד את חום המכשיר בעד 25 מעלות תוך שניות בטכנולוגיית פלטייר, מונע תקיעות במשחקים ומטעין במקביל.',
      'es': 'Enfría el procesador hasta 25°C en segundos mediante efecto Peltier y carga a la vez.',
      'ru': 'Снижает температуру процессора до 25°C за считанные секунды с помощью элемента Пельтье.'
    },
    'price_usd': 11.80,
    'old_price_usd': 27.00,
    'discount_pct': 56,
    'rating': 4.8,
    'reviews_count': 640,
    'orders_count': 3900,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'magnetic_phone_cooler.jpg',
    'icon': '❄️',
    'highlights': ['TEC Semiconductor Peltier Cooling', 'Simultaneous 15W MagSafe Wireless Charge', 'Dynamic RGB Breathing Lighting', 'Ultra-Quiet Hydraulic Bearing Fan'],
    'specs': {'Cooling Tech': 'Peltier Semiconductor', 'Wireless Power': 'Up to 15W', 'Attachment': 'MagSafe Magnetic', 'Weight': '65g'}
  },
  {
    'id': 'res-tech-03',
    'slug': 'baseus-bowie-ma10-tws-earbuds-48db-anc-140h-battery',
    'category': 'tech',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Baseus Bowie MA10 Hybrid ANC Earbuds (-48dB Noise Cancelling, 140H Total Playtime, IPX6)',
    'title_i18n': {
      'en': 'Baseus Bowie MA10 Hybrid ANC Earbuds (-48dB Noise Cancelling, 140H Total Playtime, IPX6)',
      'he': 'אוזניות אלחוטיות Baseus Bowie MA10 עם ביטול רעשים אקטיבי עמוק -48dB, סוללה מטורפת ל-140 שעות ועמידות למים',
      'es': 'Auriculares Baseus Bowie MA10 con Cancelación de Ruido Activa -48dB y 140H de Batería',
      'ru': 'Беспроводные наушники Baseus Bowie MA10 с активным шумоподавлением -48 дБ и до 140 ч работы'
    },
    'short_desc': 'Endorsed by OSCAR-winning sound engineers: incredible titanium diaphragm bass, extreme -48dB silence, and 140h battery case.',
    'short_desc_i18n': {
      'en': 'Endorsed by OSCAR-winning sound engineers: incredible titanium diaphragm bass, extreme -48dB silence, and 140h battery case.',
      'he': 'אושר ע"י מהנדסי סאונד זוכי אוסקר: בס עמוק בדיאפרגמת טיטניום, שקט מוחלט בטיסות ואימונים וקייס ענק ל-140 שעות.',
      'es': 'Aislamiento acústico de -48dB, graves potentes con diafragma de titanio y estuche con 140 horas.',
      'ru': 'Шумоподавление флагманского уровня -48 дБ, мощные титановые мембраны и кейс с запасом 140 часов.'
    },
    'price_usd': 24.50,
    'old_price_usd': 55.00,
    'discount_pct': 55,
    'rating': 4.9,
    'reviews_count': 2100,
    'orders_count': 14200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'baseus_ma10_earbuds.jpg',
    'icon': '🎧',
    'highlights': ['-48dB Hybrid Active Noise Cancellation', 'Titanium Composite Dynamic Diaphragms', '140 Hours Massive Total Battery Life', 'IPX6 Sweat & Rain Water Resistance'],
    'specs': {'Bluetooth': '5.3', 'ANC Depth': '-48dB', 'Playtime': '8h / 140h with Case', 'Waterproof': 'IPX6'}
  },
  {
    'id': 'res-tech-04',
    'slug': 'folding-portable-bluetooth-keyboard-with-touchpad',
    'category': 'tech',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Tri-Fold Ultra-Slim Portable Bluetooth Keyboard with Multi-Touch Touchpad for iPad & Laptop',
    'title_i18n': {
      'en': 'Tri-Fold Ultra-Slim Portable Bluetooth Keyboard with Multi-Touch Touchpad for iPad & Laptop',
      'he': 'מקלדת בלוטוס ניידת מתקפלת ל-3 חלקים עם משטח מגע Touchpad משולב לאייפד, טאבלט וסמארטפון',
      'es': 'Teclado Bluetooth Plegable Ultradelgado con Touchpad Integrado para Tablet y Móvil',
      'ru': 'Складная ультратонкая Bluetooth-клавиатура с тачпадом для планшета и смартфона'
    },
    'short_desc': 'Pocket-sized when folded, unfolds into a full tactile typing layout with built-in gestures touchpad.',
    'short_desc_i18n': {
      'en': 'Pocket-sized when folded, unfolds into a full tactile typing layout with built-in gestures touchpad.',
      'he': 'נכנסת לכיס כשהיא סגורה, ונפתחת למקלדת מלאה ונוחה עם משטח עכבר מחוות לכל מערכות ההפעלה.',
      'es': 'Cabe en el bolsillo al plegarse y se convierte en un teclado cómodo con trackpad multitáctil.',
      'ru': 'Помещается в карман в сложенном виде, раскладывается в удобную клавиатуру с тачпадом жестов.'
    },
    'price_usd': 15.60,
    'old_price_usd': 34.00,
    'discount_pct': 54,
    'rating': 4.8,
    'reviews_count': 780,
    'orders_count': 4900,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'folding_bt_keyboard.jpg',
    'icon': '⌨️',
    'highlights': ['Tri-Folding Pocket Size Portability', 'Responsive Sensitive Multi-Touchpad', 'Connects up to 3 Devices Simultaneously', 'Long 48-Hour Continuous Typing'],
    'specs': {'Connectivity': 'Bluetooth 5.1 (3 Channels)', 'Key Mechanism': 'Scissor Switch', 'Battery': 'Rechargeable Li-Ion', 'Weight': '197g'}
  },
  {
    'id': 'res-tech-05',
    'slug': 'ugreen-240w-usb-c-to-usb-c-cable-braided-pd31',
    'category': 'tech',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'UGREEN 240W Fast Charging Braided USB-C to USB-C Cable (PD 3.1 & E-Marker Chip)',
    'title_i18n': {
      'en': 'UGREEN 240W Fast Charging Braided USB-C to USB-C Cable (PD 3.1 & E-Marker Chip)',
      'he': 'כבל טעינה סופר-מהיר 240W UGREEN קלוע עמיד במיוחד בתקן PD 3.1 עם שבב הגנה חכם E-Marker',
      'es': 'Cable USB-C a USB-C Trenzado 240W UGREEN (PD 3.1 con Chip Inteligente E-Marker)',
      'ru': 'Сверхмощный плетеный кабель Type-C to Type-C UGREEN 240W (PD 3.1 с чипом E-Marker)'
    },
    'short_desc': 'Supports the fastest 240W PD 3.1 charging standard, future-proof for powerful laptops, tablets, and phones.',
    'short_desc_i18n': {
      'en': 'Supports the fastest 240W PD 3.1 charging standard, future-proof for powerful laptops, tablets, and phones.',
      'he': 'תומך בעוצמת שיא של 240 וואט, מוגן בסיבי ניילון קלועים ברמה צבאית ומטעין מחשבים ניידים במהירות מקסימלית.',
      'es': 'Admite el estándar PD 3.1 más potente de hasta 240W con funda de nailon trenzado ultra resistente.',
      'ru': 'Поддерживает самый мощный стандарт 240 Вт PD 3.1, усиленная оплетка и умный чип контроля тока.'
    },
    'price_usd': 5.20,
    'old_price_usd': 12.00,
    'discount_pct': 56,
    'rating': 4.9,
    'reviews_count': 3400,
    'orders_count': 28000,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'ugreen_240w_cable.jpg',
    'icon': '🔌',
    'highlights': ['Next-Gen 240W PD 3.1 Fast Charging', 'Certified E-Marker Safety Smart Chip', '10,000+ Bend Tested Military Braid', 'Aluminum Zinc Alloy Shell Connectors'],
    'specs': {'Power': '240W (48V/5A Max)', 'Standard': 'USB-C PD 3.1', 'Data Transfer': '480 Mbps', 'Length': '1m / 2m'}
  },

  # PETS
  {
    'id': 'res-pets-01',
    'slug': 'laser-cat-toy-automatic-interactive-rechargeable',
    'category': 'pets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Automatic Interactive Smart Laser Cat Toy with Random Trajectory & Rechargeable Battery',
    'title_i18n': {
      'en': 'Automatic Interactive Smart Laser Cat Toy with Random Trajectory & Rechargeable Battery',
      'he': 'צעצוע לייזר אוטומטי חכם לחתולים עם מסלולי תנועה אקראיים, טיימר כיבוי וסוללה נטענת USB',
      'es': 'Juguete Láser Automático Interactivo para Gatos con Trayectoria Aleatoria Recargable',
      'ru': 'Автоматическая интерактивная лазерная игрушка для кошек с переменной траекторией'
    },
    'short_desc': 'Keeps indoor cats active and entertained with silent random 360-degree laser patterns and automatic 15-minute sleep cycles.',
    'short_desc_i18n': {
      'en': 'Keeps indoor cats active and entertained with silent random 360-degree laser patterns and automatic 15-minute sleep cycles.',
      'he': 'מעסיק חתולים שעות רבות ומעודד פעילות גופנית עם קרן לייזר שקטה שנעה במסלולים בלתי צפויים וטיימר מנוחה.',
      'es': 'Mantiene activos y entretenidos a los gatos con patrones de láser impredecibles y apagado automático.',
      'ru': 'Развлекает питомца случайными траекториями лазерного луча, защищая от скуки и лишнего веса.'
    },
    'price_usd': 9.40,
    'old_price_usd': 21.00,
    'discount_pct': 55,
    'rating': 4.9,
    'reviews_count': 830,
    'orders_count': 5100,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'laser_cat_toy.jpg',
    'icon': '🐾',
    'highlights': ['Unpredictable Dual-Axis Random Movement', 'Silent Stepper Motor Mechanics', 'Automatic 15-Minute Rest Cycle', 'USB Type-C Rechargeable'],
    'specs': {'Laser': 'Safe Class II (<1mW)', 'Angles': 'Adjustable Circling Speeds', 'Battery': 'Rechargeable Lithium', 'Material': 'Durable ABS'}
  },
  {
    'id': 'res-pets-02',
    'slug': 'waterproof-silicone-pet-feeding-mat-raised-edges',
    'category': 'pets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Non-Slip Food-Grade Silicone Pet Feeding Mat with Spill-Proof Raised Edges for Dogs & Cats',
    'title_i18n': {
      'en': 'Non-Slip Food-Grade Silicone Pet Feeding Mat with Spill-Proof Raised Edges for Dogs & Cats',
      'he': 'משטח סיליקון איכותי למניעת לכלוך סביב קערות האוכל והמים של חיות מחמד עם שוליים מוגבהים',
      'es': 'Alfombrilla de Silicona Antideslizante para Mascotas con Bordes Antiderrame',
      'ru': 'Нескользящий силиконовый коврик для мисок домашних животных с высокими бортиками'
    },
    'short_desc': 'Keeps your floors spotlessly clean by catching splashed water and dropped kibble on a flexible silicone tray.',
    'short_desc_i18n': {
      'en': 'Keeps your floors spotlessly clean by catching splashed water and dropped kibble on a flexible silicone tray.',
      'he': 'שומר על רצפה נקייה לחלוטין ממים שנשפכים ומזון שמתפזר, קל לשטיפה בכיור או במדיח כלים.',
      'es': 'Evita manchas en el suelo atrapando salpicaduras de agua y comida, fácil de lavar en lavavajillas.',
      'ru': 'Защищает полы от брызг воды и крошек корма, легко моется под краном или в посудомойке.'
    },
    'price_usd': 4.90,
    'old_price_usd': 11.00,
    'discount_pct': 55,
    'rating': 4.8,
    'reviews_count': 670,
    'orders_count': 4300,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'silicone_pet_mat.jpg',
    'icon': '🥣',
    'highlights': ['100% FDA Food-Grade Silicone', 'High Raised Anti-Spill Lip', 'Non-Skid Grippy Base', 'Dishwasher Safe & Foldable'],
    'specs': {'Material': '100% Silicone', 'Size': '48 x 30 cm', 'Lip Height': '1.2 cm', 'Heat Resistance': '-40°C to 230°C'}
  },
  {
    'id': 'res-pets-03',
    'slug': 'pet-hair-remover-roller-self-cleaning-lint-brush',
    'category': 'pets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Reusable Self-Cleaning Pet Hair & Fur Remover Roller for Sofas, Carpets & Bedding',
    'title_i18n': {
      'en': 'Reusable Self-Cleaning Pet Hair & Fur Remover Roller for Sofas, Carpets & Bedding',
      'he': 'גלגלת פטנט רב-פעמית להסרת שערות ופרווה של כלבים וחתולים מספות, שטיחים ובגדים ללא צורך בסרטי הדבקה',
      'es': 'Rodillo Quitapelos Reutilizable Autolimpiable para Sofás, Alfombras y Ropa',
      'ru': 'Многоразовый самоочищающийся валик для сбора шерсти питомцев с мебели и одежды'
    },
    'short_desc': 'Static absorption nylon roller cleans dog and cat fur effortlessly with one push; empty chamber with a single click.',
    'short_desc_i18n': {
      'en': 'Static absorption nylon roller cleans dog and cat fur effortlessly with one push; empty chamber with a single click.',
      'he': 'לוכד כל שערה במהירות באמצעות חשמל סטטי, חוסך קניית גלילי נייר דביקים ונפתח לריקון בלחיצת כפתור.',
      'es': 'Atrapa todo el pelo por electricidad estática sin recambios adhesivos y se vacía con un botón.',
      'ru': 'Собирает шерсть за счет электростатического ворса, не требует липких лент и легко очищается.'
    },
    'price_usd': 5.80,
    'old_price_usd': 13.50,
    'discount_pct': 57,
    'rating': 4.9,
    'reviews_count': 1920,
    'orders_count': 12400,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'pet_hair_roller.jpg',
    'icon': '🧹',
    'highlights': ['Zero Adhesive Tape Refills Needed', 'Static Micro-Bristle Technology', '1-Click Pop-Open Waste Chamber', 'Works on Couches, Bedding & Carpets'],
    'specs': {'Material': 'ABS + Electrostatic Nylon', 'Chamber Capacity': '300ml', 'Weight': '170g', 'Lifespan': 'Unlimited Reusable'}
  },
  {
    'id': 'res-pets-04',
    'slug': 'hands-free-retractable-dog-leash-wrist-strap',
    'category': 'pets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Hands-Free 3-Meter Retractable Dog Leash with Ergonomic Wrist Ring & One-Touch Lock',
    'title_i18n': {
      'en': 'Hands-Free 3-Meter Retractable Dog Leash with Ergonomic Wrist Ring & One-Touch Lock',
      'he': 'רצועה נמתחת 3 מטר לכלב עם צמיד יד ארגונומי לשחרור הידיים ובלימה מיידית בנגיעה',
      'es': 'Correa Retráctil 3M Manos Libres para Perro con Anilla de Muñeca y Freno Rápido',
      'ru': 'Поводок-рулетка 3 м с креплением на запястье hands-free и мгновенным тормозом'
    },
    'short_desc': 'Free up your hands for holding a phone or coffee while walking your dog safely with cushioned wrist ring.',
    'short_desc_i18n': {
      'en': 'Free up your hands for holding a phone or coffee while walking your dog safely with cushioned wrist ring.',
      'he': 'משחרר את שתי הידיים לטלפון או כוס קפה בזמן הטיול עם הכלב, כולל מנגנון נעילה מהיר ובטוח.',
      'es': 'Permite llevar las manos libres para el café o móvil durante el paseo de forma segura.',
      'ru': 'Освобождает руки для кофе или смартфона во время прогулки с собакой, мягкий браслет на запястье.'
    },
    'price_usd': 8.90,
    'old_price_usd': 19.50,
    'discount_pct': 54,
    'rating': 4.8,
    'reviews_count': 510,
    'orders_count': 3200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'handsfree_dog_leash.jpg',
    'icon': '🦮',
    'highlights': ['Hands-Free Wrist Ring Design', 'Smooth 3-Meter Retractable Webbing', 'Instant 1-Thumb Braking Lock', 'Rated for Dogs up to 30kg'],
    'specs': {'Length': '3 Meters', 'Max Load': '30 kg', 'Weight': '210g', 'Material': 'High-Tensile Nylon + ABS'}
  },
  {
    'id': 'res-pets-05',
    'slug': 'slow-feeder-dog-bowl-anti-gulping-bloat-stop',
    'category': 'pets',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Eco-Friendly Anti-Gulping Slow Feeder Dog Bowl for Healthy Digestion & Bloat Prevention',
    'title_i18n': {
      'en': 'Eco-Friendly Anti-Gulping Slow Feeder Dog Bowl for Healthy Digestion & Bloat Prevention',
      'he': 'קערת האכלה איטית לכלבים מונעת חנק ובליעת מזון מהירה — שומרת על מערכת עיכול בריאה',
      'es': 'Comedero Lento Antivoracidad para Perros para Mejorar la Digestión y Evitar Gases',
      'ru': 'Миска для медленного кормления собак против быстрого заглатывания корма'
    },
    'short_desc': 'Interactive maze design slows feeding by up to 10x, preventing choking, vomiting, and canine bloat.',
    'short_desc_i18n': {
      'en': 'Interactive maze design slows feeding by up to 10x, preventing choking, vomiting, and canine bloat.',
      'he': 'מבנה מבוך חכם שמאט את קצב האכילה פי 10, מונע כאבי בטן, הקאות והשמנת יתר אצל כלבים.',
      'es': 'El laberinto interior ralentiza la ingesta hasta 10 veces favoreciendo una digestión sana.',
      'ru': 'Лабиринт замедляет прием пищи в 10 раз, предотвращая вздутие живота и улучшая пищеварение.'
    },
    'price_usd': 4.20,
    'old_price_usd': 9.90,
    'discount_pct': 57,
    'rating': 4.8,
    'reviews_count': 640,
    'orders_count': 4100,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'slow_feeder_bowl.jpg',
    'icon': '🐕',
    'highlights': ['Slows Eating Pace by 10x', 'Prevents Bloat & Regurgitation', 'Non-Slip Rubber Base Pads', 'Non-Toxic Food Safe Polypropylene'],
    'specs': {'Diameter': '20cm', 'Capacity': 'Up to 2 Cups', 'Material': 'BPA-Free Food Grade PP', 'Base': 'Rubber Non-Slip'}
  },

  # TOOLS
  {
    'id': 'res-tool-01',
    'slug': 'digital-laser-tape-measure-2-in-1-40m-5m',
    'category': 'tools',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': '2-in-1 Digital Laser Rangefinder (40m) & Traditional Steel Tape Measure (5m) with Backlit LCD',
    'title_i18n': {
      'en': '2-in-1 Digital Laser Rangefinder (40m) & Traditional Steel Tape Measure (5m) with Backlit LCD',
      'he': 'מד מרחק לייזר דיגיטלי משולב 2 ב-1: מד לייזר עד 40 מטר + סרט מדידה 5 מטר עם צג LCD מואר',
      'es': 'Telémetro Láser 2 en 1 (40m) y Cinta Métrica Tradicional (5m) con Pantalla LCD',
      'ru': 'Лазерная рулетка 2-в-1: лазерный дальномер до 40 м + лента 5 м с ЖК-экраном'
    },
    'short_desc': 'Measure large rooms instantly up to 40 meters with laser, or use the 5m physical tape for short items.',
    'short_desc_i18n': {
      'en': 'Measure large rooms instantly up to 40 meters with laser, or use the 5m physical tape for short items.',
      'he': 'מודד חדרים, קירות וגבהים תוך שנייה בלייזר מדויק עד 40 מטר, או חפצים קטנים בסרט מדידה פיזי איכותי.',
      'es': 'Mide estancias enteras en 1 segundo con láser o piezas pequeñas con la cinta métrica.',
      'ru': 'Измеряет комнаты до 40 метров лазером за секунду или детали рулеткой 5 м с автостопом.'
    },
    'price_usd': 14.80,
    'old_price_usd': 32.00,
    'discount_pct': 53,
    'rating': 4.9,
    'reviews_count': 1140,
    'orders_count': 7800,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'laser_tape_measure.jpg',
    'icon': '📐',
    'highlights': ['Laser Distance up to 40m (±2mm)', '5m High-Strength Self-Locking Tape', 'Calculates Area, Volume & Pythagoras', 'Rechargeable USB Lithium Battery'],
    'specs': {'Laser Range': '0.2 - 40m', 'Tape Length': '5m', 'Accuracy': '±2mm', 'Battery': 'Rechargeable Li-Ion'}
  },
  {
    'id': 'res-tool-02',
    'slug': 'cordless-hot-melt-glue-gun-type-c-fast-heating',
    'category': 'tools',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Cordless Rapid Heating Hot Melt Glue Gun with Anti-Drip Nozzle & USB-C Charging',
    'title_i18n': {
      'en': 'Cordless Rapid Heating Hot Melt Glue Gun with Anti-Drip Nozzle & USB-C Charging',
      'he': 'אקדח דבק חם אלחוטי נטען USB-C עם חימום מהיר ב-15 שניות ופיית מניעת טפטוף מדויקת',
      'es': 'Pistola de Silicona Caliente Inalámbrica Recargable USB-C de Calentamiento Rápido',
      'ru': 'Беспроводной термопистолет для клея с нагревом за 15 сек и зарядкой Type-C'
    },
    'short_desc': 'Heats up in just 15 seconds without tangled cords; smart auto shut-off prevents overheating and burns.',
    'short_desc_i18n': {
      'en': 'Heats up in just 15 seconds without tangled cords; smart auto shut-off prevents overheating and burns.',
      'he': 'מתחמם תוך 15 שניות בלבד לעבודה נוחה בכל מקום ללא כבלים מסורבלים, פייה מיוחדת מונעת טפטוף מעצבן.',
      'es': 'Lista para usar en 15 segundos sin cables molestos, con boquilla antigoteo y apagado de seguridad.',
      'ru': 'Нагревается за 15 секунд без мешающих проводов, сопло против подтекания и автоотключение.'
    },
    'price_usd': 11.20,
    'old_price_usd': 24.50,
    'discount_pct': 54,
    'rating': 4.8,
    'reviews_count': 590,
    'orders_count': 3700,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'cordless_glue_gun.jpg',
    'icon': '🔫',
    'highlights': ['15-Second Rapid PTC Heating', 'Anti-Drip Copper Dispensing Tip', 'Smart 3-Minute Auto Sleep Off', 'Type-C USB Universal Charging'],
    'specs': {'Warm-Up': '15 Seconds', 'Glue Stick': '7mm standard', 'Battery': '2000mAh', 'Weight': '220g'}
  },
  {
    'id': 'res-tool-03',
    'slug': 'handheld-thermal-imager-infrared-thermometer-gun',
    'category': 'tools',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Non-Contact Digital Infrared Laser Thermometer Temperature Gun (-50°C to 550°C)',
    'title_i18n': {
      'en': 'Non-Contact Digital Infrared Laser Thermometer Temperature Gun (-50°C to 550°C)',
      'he': 'מד חום לייזר אינפרא-אדום דיגיטלי ללא מגע לבישול, מנועי רכב, מזגנים ותעשייה (-50°C עד 550°C)',
      'es': 'Pistola Termómetro Láser Digital Infrarrojo Sin Contacto (-50°C a 550°C)',
      'ru': 'Бесконтактный цифровой инфракрасный пирометр-термометр от -50°C до +550°C'
    },
    'short_desc': 'Measures exact surface temperature instantly from a distance with 12:1 distance-to-spot precision.',
    'short_desc_i18n': {
      'en': 'Measures exact surface temperature instantly from a distance with 12:1 distance-to-spot precision.',
      'he': 'מודד חום מדויק מרחוק תוך חצי שנייה: מתאים לטאבון פיצה, מנועי רכב, לוחות חשמל ומזגנים.',
      'es': 'Mide la temperatura al instante a distancia para cocina, automoción y aire acondicionado.',
      'ru': 'Мгновенно измеряет температуру поверхностей с расстояния для гриля, двигателей и кондиционеров.'
    },
    'price_usd': 8.90,
    'old_price_usd': 19.90,
    'discount_pct': 55,
    'rating': 4.9,
    'reviews_count': 1480,
    'orders_count': 9200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'laser_infrared_thermometer.jpg',
    'icon': '🌡️',
    'highlights': ['High Range -50°C to 550°C (-58°F to 1022°F)', 'Rapid 0.5s Instant Response', '12:1 Distance-to-Spot Precision', 'Color Backlit LCD Display'],
    'specs': {'Range': '-50°C to 550°C', 'D:S Ratio': '12:1', 'Emissivity': '0.95 Preset', 'Power': '2x AAA Batteries'}
  },
  {
    'id': 'res-tool-04',
    'slug': 'automatic-wire-stripper-crimper-cutter-plier',
    'category': 'tools',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Multi-Function Automatic Wire Stripper, Cable Cutter & Terminal Crimper (AWG 10-24)',
    'title_i18n': {
      'en': 'Multi-Function Automatic Wire Stripper, Cable Cutter & Terminal Crimper (AWG 10-24)',
      'he': 'חושף חוטי חשמל אוטומטי מקצועי כולל חותך כבלים ומלחץ סופיות במכשיר אחד (AWG 10-24)',
      'es': 'Pelacables Automático Multifunción con Cortador y Crimpadora de Terminales',
      'ru': 'Автоматический стриппер для зачистки проводов с резаком и обжимкой клемм'
    },
    'short_desc': 'Strips insulated wire cleanly in one squeeze without damaging copper core conductors.',
    'short_desc_i18n': {
      'en': 'Strips insulated wire cleanly in one squeeze without damaging copper core conductors.',
      'he': 'מקלף בידוד מחוטי חשמל בלחיצה אחת קלה בלי לפצוע את גידי הנחושת, חוסך שעות עבודה לחשמלאים וחובבים.',
      'es': 'Pela el aislante del cable en un solo movimiento sin dañar los filamentos de cobre.',
      'ru': 'Снимает изоляцию за одно нажатие без повреждения медных жил, со встроенным кусачками и обжимом.'
    },
    'price_usd': 7.40,
    'old_price_usd': 16.50,
    'discount_pct': 55,
    'rating': 4.9,
    'reviews_count': 1630,
    'orders_count': 10500,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'automatic_wire_stripper.jpg',
    'icon': '⚡',
    'highlights': ['1-Squeeze Automatic Stripping Mechanism', 'Crimps Insulated & Bare Terminals', 'Integrated Sharp Cable Shear', 'Adjustable Stripping Length Stop'],
    'specs': {'Stripping Range': 'AWG 10-24 (0.2-6.0 mm²)', 'Crimping': '0.5-6.0 mm²', 'Jaws': 'Alloy Carbon Steel', 'Handle': 'TPR Ergonomic'}
  },
  {
    'id': 'res-tool-05',
    'slug': 'contour-gauge-profile-tool-locking-mechanism-25cm',
    'category': 'tools',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': '25cm Precision Contour Duplication Gauge with Metal Heavy-Duty Lock Mechanism',
    'title_i18n': {
      'en': '25cm Precision Contour Duplication Gauge with Metal Heavy-Duty Lock Mechanism',
      'he': 'שבלונה להעתקת צורות ופינות מעוקלות 25 ס"מ עם מנגנון נעילת מתכת לריצוף, פרקטים ונגרות',
      'es': 'Calibre Copiador de Contornos de 25cm con Bloqueo Metálico para Suelos y Carpintería',
      'ru': 'Шаблон для копирования контуров 25 см с металлическим фиксатором для плитки и ламината'
    },
    'short_desc': 'Instantly duplicates awkward curves, pipes, and corner angles for flawless tile, laminate, and woodwork cuts.',
    'short_desc_i18n': {
      'en': 'Instantly duplicates awkward curves, pipes, and corner angles for flawless tile, laminate, and woodwork cuts.',
      'he': 'מעתיק פינות עגולות, צינורות וקשתות תוך שניות לחיתוך מדויק של קרמיקה, פרקט ומשטחי עבודה ללא טעויות.',
      'es': 'Copia curvas complejas y tuberías para cortes perfectos en baldosas y tarima flotante.',
      'ru': 'Точно копирует неровные углы и трубы для идеальной подрезки плитки, ламината и панелей.'
    },
    'price_usd': 6.20,
    'old_price_usd': 14.00,
    'discount_pct': 56,
    'rating': 4.8,
    'reviews_count': 820,
    'orders_count': 5300,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'contour_gauge.jpg',
    'icon': '📏',
    'highlights': ['Aluminum Alloy Sturdy Lock Lever', 'High-Density Fine Teeth Copying', 'Double Metric & Imperial Rulers', 'Eliminates Guesswork on Tile Cuts'],
    'specs': {'Measuring Length': '25cm (10 inch)', 'Lock': 'Heavy Duty Metal Lever', 'Material': 'High-Impact ABS', 'Depth': '60mm'}
  },

  # UNDER 10
  {
    'id': 'res-under-01',
    'slug': 'portable-electric-clothes-lint-remover-shaver',
    'category': 'under10',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'USB Rechargeable Electric Fabric Shaver & Clothes Defuzzer with 6-Leaf Stainless Blades',
    'title_i18n': {
      'en': 'USB Rechargeable Electric Fabric Shaver & Clothes Defuzzer with 6-Leaf Stainless Blades',
      'he': 'מכשיר גילוח בדים וסוודרים נטען USB בעל 6 להבי נירוסטה חדים — מחדש בגדים וספות כמו חדש',
      'es': 'Quitapelusas Eléctrico Recargable USB con Cuchillas de 6 Hojas de Acero Inoxidable',
      'ru': 'Электрическая машинка для удаления катышков с одежды с 6-лопастными стальными лезвиями'
    },
    'short_desc': 'Removes pills, fuzz, and lint from wool coats, sweaters, and furniture without damaging delicate fabrics.',
    'short_desc_i18n': {
      'en': 'Removes pills, fuzz, and lint from wool coats, sweaters, and furniture without damaging delicate fabrics.',
      'he': 'מסיר ביעילות כדוריות צמר ומוך מסוודרים, מעילים וספות ומחזיר לבגדים ישנים מראה חדש לחלוטין.',
      'es': 'Elimina bolitas y pelusas de jerséis, abrigos y sofás sin dañar el tejido.',
      'ru': 'Удаляет катышки и ворс со свитеров, пальто и диванов, возвращая вещам аккуратный вид.'
    },
    'price_usd': 5.40,
    'old_price_usd': 12.00,
    'discount_pct': 55,
    'rating': 4.9,
    'reviews_count': 1870,
    'orders_count': 14800,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'fabric_shaver.jpg',
    'icon': '✨',
    'highlights': ['Upgraded 6-Leaf Stainless Steel Blades', 'Honeycomb Micro-Arc Protective Mesh', 'Magnetic Translucent Waste Bin', 'Type-C USB Rapid Recharging'],
    'specs': {'Blades': '6-Leaf Stainless Steel', 'Mesh': 'Stainless Honeycomb', 'Battery': 'Rechargeable 500mAh', 'Charging': 'USB Type-C'}
  },
  {
    'id': 'res-under-02',
    'slug': 'nano-double-sided-tape-heavy-duty-waterproof',
    'category': 'under10',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Heavy-Duty Reusable Washable Clear Nano Double-Sided Adhesive Tape (3 Meters)',
    'title_i18n': {
      'en': 'Heavy-Duty Reusable Washable Clear Nano Double-Sided Adhesive Tape (3 Meters)',
      'he': 'סרט הדבקה דו-צדדי ננו שקוף וחזק במיוחד רחיץ ורב-פעמי — מחזיק תמונות ומדפים ללא צורך במסמרים',
      'es': 'Cinta Adhesiva de Doble Cara Nano Transparente Lavable y Reutilizable (3 Metros)',
      'ru': 'Многоразовая прозрачная двухсторонняя нано-лента высокой прочности (3 метра)'
    },
    'short_desc': 'Holds pictures, power strips, and hooks firmly without nails or wall damage; washes clean with water.',
    'short_desc_i18n': {
      'en': 'Holds pictures, power strips, and hooks firmly without nails or wall damage; washes clean with water.',
      'he': 'מחזיק מראות, תמונות, שקעים ומתלים ללא קידוח וללא השארת סימנים על הקיר, נשטף במים ומוכן לשימוש חוזר.',
      'es': 'Fija cuadros, regletas y accesorios sin taladros ni dañar las paredes, lavable y reutilizable.',
      'ru': 'Держит картины, удлинители и полки без гвоздей и следов на стенах, промывается водой для повторного использования.'
    },
    'price_usd': 2.70,
    'old_price_usd': 6.50,
    'discount_pct': 58,
    'rating': 4.8,
    'reviews_count': 3200,
    'orders_count': 24000,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'nano_double_tape.jpg',
    'icon': '🩹',
    'highlights': ['Strong Hold up to 1kg per Segment', 'Residue-Free Clean Removal', 'Washable & Reusable over 600 Times', 'Transparent Invisible Acrylic Gel'],
    'specs': {'Length': '3 Meters', 'Width': '30mm', 'Thickness': '2mm', 'Material': 'Nano PU Gel'}
  },
  {
    'id': 'res-under-03',
    'slug': 'cable-organizer-clips-silicone-desktop-wire-holder',
    'category': 'under10',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Pack of 3 Silicone Cable Organizer Clips with 3M Adhesive for Desk & Nightstand',
    'title_i18n': {
      'en': 'Pack of 3 Silicone Cable Organizer Clips with 3M Adhesive for Desk & Nightstand',
      'he': 'מארז 3 תופסני כבלים מסיליקון עם דבק 3M חזק לשולחן עבודה ולשידה ליד המיטה',
      'es': 'Pack de 3 Organizadores de Cables de Silicona con Adhesivo 3M para Mesa',
      'ru': 'Набор из 3 силиконовых органайзеров для проводов с липучкой 3M для стола'
    },
    'short_desc': 'Keeps phone chargers, headphones, and mouse cords neatly anchored right where you need them.',
    'short_desc_i18n': {
      'en': 'Keeps phone chargers, headphones, and mouse cords neatly anchored right where you need them.',
      'he': 'שומר על כבלי טעינה, אוזניות ומחשב מסודרים בהישג יד ומונע מהם ליפול לרצפה מאחורי השולחן.',
      'es': 'Mantiene cargadores y cables ordenados a mano evitando que caigan detrás del escritorio.',
      'ru': 'Надежно фиксирует провода зарядки и наушников на краю стола, не давая им падать на пол.'
    },
    'price_usd': 2.30,
    'old_price_usd': 5.80,
    'discount_pct': 60,
    'rating': 4.9,
    'reviews_count': 2400,
    'orders_count': 19000,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'silicone_cable_clips.jpg',
    'icon': '📎',
    'highlights': ['Strong Non-Marking 3M Adhesive', 'Flexible Eco-Friendly Soft Silicone', 'Slots for 3, 5, and 7 Cables', 'Fits All USB & Power Wires <6mm'],
    'specs': {'Material': 'Soft Silicone', 'Quantity': '3 Holders (3, 5, 7 Slots)', 'Adhesive': 'Authentic 3M Foam', 'Wire Fit': '<6mm'}
  },
  {
    'id': 'res-under-04',
    'slug': 'electric-milk-frother-handheld-foam-maker-whisker',
    'category': 'under10',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'High-Speed Handheld Electric Milk Frother & Coffee Whisk with Stainless Stand',
    'title_i18n': {
      'en': 'High-Speed Handheld Electric Milk Frother & Coffee Whisk with Stainless Stand',
      'he': 'מקציף חלב ידני חשמלי עוצמתי לקפה, קפוצ\'ינו ומאצ\'ה עם מעמד נירוסטה יוקרתי',
      'es': 'Espumador de Leche Eléctrico de Mano Potente con Soporte de Acero para Café',
      'ru': 'Электрический ручной капучинатор-вспениватель молока со стальной подставкой'
    },
    'short_desc': 'Creates rich, creamy barista-style milk froth in 15 seconds for lattes, matcha, and protein shakes.',
    'short_desc_i18n': {
      'en': 'Creates rich, creamy barista-style milk froth in 15 seconds for lattes, matcha, and protein shakes.',
      'he': 'יוצר קצף חלב סמיך וקטיפתי כמו בבית קפה תוך 15 שניות, מתאים לקפוצ\'ינו, שוקו חם ושייקים.',
      'es': 'Crea espuma cremosa estilo barista en 15 segundos para café con leche y batidos.',
      'ru': 'Взбивает густую бархатистую молочную пенку за 15 секунд для капучино, латте и матча.'
    },
    'price_usd': 3.80,
    'old_price_usd': 8.90,
    'discount_pct': 57,
    'rating': 4.8,
    'reviews_count': 1950,
    'orders_count': 16000,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'milk_frother.jpg',
    'icon': '☕',
    'highlights': ['14,000 RPM Powerful Whisking Motor', 'Food-Grade 304 Stainless Steel Spiral', 'Includes Dedicated Counter Stand', 'Effortless 1-Touch Button Operation'],
    'specs': {'Motor': '14,000 RPM', 'Material': 'ABS + 304 Stainless', 'Power': '2x AA Batteries', 'Stand': 'Included'}
  },
  {
    'id': 'res-under-05',
    'slug': 'telescopic-magnetic-pickup-tool-with-led-flashlight',
    'category': 'under10',
    'badge': '🔥 TRENDING',
    'badge_i18n': {'en': '🔥 TRENDING', 'he': '🔥 טרנד חם', 'es': '🔥 TENDENCIA', 'ru': '🔥 В ТРЕНДЕ'},
    'title': 'Extendable Telescopic Magnetic Pick-Up Tool with Flexible 360° LED Flashlight Head',
    'title_i18n': {
      'en': 'Extendable Telescopic Magnetic Pick-Up Tool with Flexible 360° LED Flashlight Head',
      'he': 'מוט מגנטי טלסקופי נשלף עם פנס LED גמיש 360° להרמת ברגים, אומים ומפתחות ממקומות צפופים',
      'es': 'Herramienta Recogedora Magnética Telescópica con Linterna LED Flexible 360°',
      'ru': 'Телескопический магнитный щуп с гибким фонариком 360° для извлечения винтов и гаек'
    },
    'short_desc': 'Extends to 57cm with powerful magnet and bright LED neck to retrieve dropped screws from dark engine bays or furniture cracks.',
    'short_desc_i18n': {
      'en': 'Extends to 57cm with powerful magnet and bright LED neck to retrieve dropped screws from dark engine bays or furniture cracks.',
      'he': 'נפתח לאורך של 57 ס"מ עם מגנט חזק ופנס לד גמיש לשליפת ברגים ומפתחות שנפלו לתא המנוע או מאחורי רהיטים.',
      'es': 'Se extiende hasta 57cm con imán potente y cuello flexible para recuperar tornillos bajo el coche o muebles.',
      'ru': 'Раздвигается до 57 см с мощным неодимовым магнитом и подсветкой для извлечения упавших деталей из авто.'
    },
    'price_usd': 3.60,
    'old_price_usd': 8.50,
    'discount_pct': 58,
    'rating': 4.9,
    'reviews_count': 1180,
    'orders_count': 8200,
    'affiliate_url': 'https://s.click.aliexpress.com/e/_DkDealHub',
    'img_file': 'magnetic_pickup_tool.jpg',
    'icon': '🔦',
    'highlights': ['Extends from 17cm to 57cm', '360° Bendable Flexible Gooseneck', 'Powerful Neodymium Magnet Head & Base', '3 Bright LEDs Illuminate Dark Corners'],
    'specs': {'Extended Length': '57cm', 'Magnet Strength': 'Up to 2kg pull', 'LEDs': '3 High-Bright', 'Material': 'Aviation Aluminum'}
  }
]

def main():
    processed = []
    for item in RESERVE_PRODUCTS:
        img_name = item.pop("img_file", f"{item['slug']}.jpg")
        icon = item.pop("icon", "⚡")
        label = item["title_i18n"].get("en") or item["title"]
        img_path = ensure_img(img_name, label, item["category"], icon)
        item["image"] = img_path
        item["gallery"] = [img_path]
        processed.append(item)

    out_file = os.path.join(DATA_DIR, "reserve_pool.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    print(f"[Reserve Pool] Successfully created {len(processed)} reserve products in {out_file}")

if __name__ == "__main__":
    main()
