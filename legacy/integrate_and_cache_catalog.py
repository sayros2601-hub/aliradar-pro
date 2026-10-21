import os
import json
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
NEW_BATCH_FILE = os.path.join(BASE_DIR, "data", "new_portals_batch.json")
IMG_DIR = os.path.join(BASE_DIR, "assets", "img")
os.makedirs(IMG_DIR, exist_ok=True)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

with open(NEW_BATCH_FILE, "r", encoding="utf-8") as f:
    new_items = json.load(f)

# Expanded category structure matching AliExpress departments
db["categories"] = [
    {"id": "all", "name": "כל המציאות", "icon": "🔥", "slug": "all"},
    {"id": "gadgets", "name": "גאדג׳טים והמצאות כיס", "icon": "⚡", "slug": "gadgets"},
    {"id": "auto", "name": "שדרוגים חכמים לרכב", "icon": "🚗", "slug": "auto"},
    {"id": "smarthome", "name": "בית, מטבח ומיקרו-המצאות", "icon": "🏠", "slug": "smarthome"},
    {"id": "pets", "name": "המצאות לחיות מחמד", "icon": "🐾", "slug": "pets"},
    {"id": "tools", "name": "כלי עבודה ותיקונים", "icon": "🔧", "slug": "tools"},
    {"id": "under10", "name": "מציאות גאוניות עד ₪50", "icon": "💎", "slug": "under-50"},
]

# Definitions for each of the 24 new items
META = {
    "mini-pocket-thermal-label-printer": {
        "cat": "gadgets",
        "title_he": "מדפסת כיס תרמית ניידת ללא דיו לסמארטפון (מדבקות, תמונות, פתקים וברקודים ב-Bluetooth)",
        "title_en": "Portable Inkless Mini Pocket Thermal Printer & Sticker Maker for iPhone & Android",
        "title_ru": "Карманный термопринтер без чернил для смартфона (печать стикеров, фото и заметок по Bluetooth)",
        "hook_he": "🖨️ גאדג'ט ממכר: מדפסת כיס זעירה שמדפיסה מדבקות, תמונות ופתקים בשנייה ישירות מהטלפון ללא צורך בדיו לעולם!",
        "hook_ru": "🖨️ Карманная магия: печатает наклейки, шпаргалки и фото за 2 секунды прямо со смартфона без капли чернил!",
        "hook_en": "🖨️ Zero ink forever: mini pocket printer creates stickers, memos, and photo labels in seconds via Bluetooth!",
        "price_usd": 18.60, "old_usd": 38.00, "rating": 4.8, "reviews": 6840, "orders": "20,000+",
        "specs": {"טכנולוגיית הדפסה": "תרמית ישירה (ללא דיו)", "רזולוציה": "203 DPI", "קישוריות": "Bluetooth 5.0", "סוללה": "1200mAh נטענת USB-C", "רוחב נייר": "57 מ\"מ"},
        "highlights": ["עובדת בטכנולוגיה תרמית — לעולם אין צורך לקנות מחסניות דיו יקרות", "אפליקציה ייעודית עם אלפי תבניות מוכנות למדבקות, תוויות תבלינים וארגון הבית", "סוללת ליתיום מובנית המספיקה להדפסת עשרות גלילים בטעינה אחת", "קומפקטית וקלה — נכנסת בקלות לכל כיס או תיק קטן"]
    },
    "magnetic-3in1-foldable-magsafe-charger": {
        "cat": "gadgets",
        "title_he": "עמדת טעינה מגנטית 3 ב-1 מתקפלת לכיס (טעינה במקביל ל-iPhone, Apple Watch ו-AirPods)",
        "title_en": "3-in-1 Foldable Magnetic Wireless Charging Station for iPhone, Watch & AirPods",
        "title_ru": "Складная магнитная беспроводная зарядка 3-в-1 для iPhone, Apple Watch и AirPods",
        "hook_he": "⚡ נסיעות ללא כבלים: עמדת טעינה מגנטית חכמה שמתקפלת לגודל של ארנק ומטעינה את כל המכשירים שלכם בבת אחת!",
        "hook_ru": "⚡ Прощайте спутанные провода: складывается в компактный кошелек и заряжает телефон, часы и наушники одновременно!",
        "hook_en": "⚡ Ultimate travel charger: folds down to pocket wallet size and powers iPhone, Apple Watch & earbuds simultaneously!",
        "price_usd": 21.40, "old_usd": 45.00, "rating": 4.9, "reviews": 5420, "orders": "18,000+",
        "specs": {"הספק מרבי": "15W Fast Wireless", "תאימות": "iPhone MagSafe, Apple Watch 1-9/Ultra, AirPods 2/3/Pro", "מבנה": "מפרקים סיליקוניים גמישים מתקפלים", "חיבור": "Type-C PD", "משקל": "128 גרם"},
        "highlights": ["מגנט MagSafe חזק המחזיק את הטלפון במצב מאוזן או מאונך לשימוש כמנורת לילה StandBy", "מתקפלת בצורה שטוחה לחלוטין ותופסת 0 מקום בתיק נסיעות", "שבבי הגנה מתקדמים נגד חימום יתר, קפיצות מתח וזיהוי גופים זרים", "חוסכת סרבול של 3 כבלים ומטענים נפרדים ליד המיטה"]
    },
    "ultrasonic-cleaner-tank-glasses-jewelry": {
        "cat": "gadgets",
        "title_he": "אמבט ניקוי אולטרסוניק נייד לתכשיטים, משקפיים, שעונים ויישור שיניים (45,000Hz רטט עמוק)",
        "title_en": "Portable Ultrasonic Cleaner 45,000Hz for Eyeglasses, Jewelry, Watches & Retainers",
        "title_ru": "Ультразвуковая ванночка 45000 Гц для глубокой чистки очков, ювелирных изделий и бритв",
        "hook_he": "✨ ניקוי מקצועי במים בלבד: 45,000 תנודות בשנייה שמוציאות את כל הלכלוך הנסתר ממשקפיים, תכשיטים ושעונים תוך 3 דקות!",
        "hook_ru": "✨ Чистит до блеска одной водой: 45 000 колебаний в секунду выбивают всю въевшуюся грязь из очков, колец и украшений за 3 минуты!",
        "hook_en": "✨ Pro cleaning with plain tap water: 45,000Hz deep ultrasonic waves blast hidden grime from glasses and jewelry in 3 mins!",
        "price_usd": 13.20, "old_usd": 28.00, "rating": 4.8, "reviews": 7950, "orders": "25,000+",
        "specs": {"תדר עבודה": "45,000 Hz", "קיבולת מיכל": "350 מ\"ל נירוסטה SUS304", "טיימר": "כיבוי אוטומטי לאחר 3 דקות", "הפעלה": "כפתור מגע אחד", "רמת רעש": "< 50dB"},
        "highlights": ["מנקה ביעילות פינות בלתי נגישות בחריצי משקפיים, רצועות שעון וטבעות ללא כימיקלים", "מיכל פנימי מנירוסטה רפואית 304 עמידה לחלודה ושחיקה", "בטוח לחלוטין לשימוש ביתי יומיומי ללא חשש לשריטות", "רגליות גומי בולמות רטט לעבודה שקטה במיוחד על השיש"]
    },
    "rechargeable-fabric-shaver-lint-remover": {
        "cat": "gadgets",
        "title_he": "מכשיר נטען להסרת גולגולים וכדוריות בד מבגדים וסוודרים (להבי טיטניום 6 כנפיים עם תאורת LED)",
        "title_en": "Rechargeable Electric Fabric Shaver & Lint Remover with 6-Leaf Blades & LED Display",
        "title_ru": "Электрическая машинка для удаления катышков с одежды с 6 лезвиями и LED-дисплеем",
        "hook_he": "🧥 מחזיר בגדים ישנים לחיים: מגלח ומעלים את כל כדוריות הבד והשפשופים מסוודרים ומעילים בשניות בלי לפגוע בבד!",
        "hook_ru": "🧥 Вторая жизнь любимым свитерам: 6 острых лезвий срезают все катышки за пару минут, делая одежду как из магазина!",
        "hook_en": "🧥 Make old sweaters look brand new: 6-leaf precision blades shave off fuzz and lint pills in seconds without snagging fabric!",
        "price_usd": 10.50, "old_usd": 22.00, "rating": 4.9, "reviews": 8900, "orders": "30,000+",
        "specs": {"ראש חיתוך": "6 להבי פלדת אל-חלד צפים", "סוללה": "2000mAh נטענת USB-C", "מסך": "צג דיגיטלי לאחוזי סוללה", "מהירויות": "3 רמות עוצמה מתכווננות"},
        "highlights": ["רשת מגן בצפיפות משתנה המונעת חיתוך סיבי הבד ושומרת על הבגד שלם", "שואב פנימי מובנה השואב את כל השאריות למיכל איסוף שקוף ונשלף", "צג דיגיטלי ברור המציג את מצב הסוללה ורמת המהירות בזמן אמת", "סוללה עוצמתית המספיקה לטיפול בעשרות פריטי לבוש בטעינה יחידה"]
    },
    "apple-find-my-smart-gps-tag-tracker": {
        "cat": "gadgets",
        "title_he": "תג איתור חכם למפתחות, מזוודות וחיות מחמד תואם Apple Find My (ללא דמי מנוי, סוללה לשנה)",
        "title_en": "Smart Key & Luggage Finder Tag Compatible with Apple Find My Network (No Monthly Fee)",
        "title_ru": "Умный GPS-трекер для ключей и багажа с поддержкой Apple Find My (без абонентской платы)",
        "hook_he": "📍 לא מאבדים שום דבר: תג איתור קטן שעובד ברשת Find My של אפל בכל העולם לאיתור מזוודות ומפתחות ללא דמי מנוי!",
        "hook_ru": "📍 Больше ничего не потеряется: умный маячок работает через глобальную сеть Apple Find My по всему миру без абонплаты!",
        "hook_en": "📍 Never lose keys or luggage again: connects natively to Apple Find My network worldwide with zero monthly fees!",
        "price_usd": 7.90, "old_usd": 18.00, "rating": 4.8, "reviews": 11200, "orders": "40,000+",
        "specs": {"רשת איתור": "Apple Find My Network", "סוללה": "CR2032 סטנדרטית (מחזיקה מעל שנה)", "עמידות למים": "IP67 נגד גשם והתזה", "צפצוף מובנה": "רמקול עוצמתי 85dB"},
        "highlights": ["מתחבר ישירות לאפליקציית 'מצא את...' הרשמית ב-iPhone ללא צורך בהתקנת אפליקציות זרות", "איתור עולמי מדויק המתעדכן דרך מאות מיליוני מכשירי Apple בסביבה", "סוללת כפתור סטנדרטית הניתנת להחלפה בקלות פעם בשנה", "כולל חור מובנה לחיבור למחזיק מפתחות, קולר חתול/כלב או תא מזוודה"]
    },
    "solar-wireless-tpms-tire-pressure-monitor": {
        "cat": "auto",
        "title_he": "מערכת ניטור לחץ וטמפרטורת צמיגים סולארית אלחוטית לרכב TPMS (צג צבעוני לדשבורד + 4 חיישנים)",
        "title_en": "Solar Wireless TPMS Car Tire Pressure Monitoring System with Color LCD Display",
        "title_ru": "Беспроводная солнечная система контроля давления в шинах TPMS с цветным ЖК-экраном",
        "hook_he": "🚗 בטיחות וחיסכון בדלק: מודד לחץ וטמפרטורה ב-4 הגלגלים בזמן אמת, נטען מהשמש ומתריע מיד על תקר או דליפה!",
        "hook_ru": "🚗 Защита от аварий и экономия топлива: следит за давлением в 4 шинах в реальном времени, заряжается от солнца и пищит при проколе!",
        "hook_en": "🚗 Real-time driving safety: solar-powered LCD dash unit displays PSI & temp for all 4 tires with instant puncture alarms!",
        "price_usd": 26.80, "old_usd": 55.00, "rating": 4.9, "reviews": 6300, "orders": "20,000+",
        "specs": {"טעינה": "פאנל סולארי מובנה + גיבוי USB", "דיוק מדידה": "±0.1 BAR / ±1.5 PSI", "התקנה": "4 חיישני שסתום חיצוניים (הברגה ב-2 דקות)", "חיישן רטט": "נדלק אוטומטית עם תחילת נסיעה"},
        "highlights": ["פאנל סולארי יעיל השומר על המכשיר טעון קבוע ללא צורך בכבלים על הדשבורד", "חיישן תנועה חכם המפעיל את המסך אוטומטית ברגע פתיחת דלת הרכב ומכבה בעצירה", "התראה קולית וויזואלית מיידית על בריחת אוויר מהירה, לחץ נמוך או טמפרטורה חריגה", "עוזר למנוע שחיקת צמיגים לא אחידה וחוסך עד 10% בצריכת הדלק"]
    },
    "2in1-cordless-car-vacuum-turbo-blower": {
        "cat": "auto",
        "title_he": "שואב אבק אלחוטי עוצמתי לרכב 2 ב-1 + מפוח אוויר טורבו לניקוי פתחי מזגן ומקלדת (12,000Pa)",
        "title_en": "2-in-1 Cordless High-Power Car Vacuum Cleaner & Air Duster Turbo Blower (12,000Pa)",
        "title_ru": "Беспроводной мощный пылесос 2-в-1 для авто и турбо-воздуходувка для клавиатуры и щелей",
        "hook_he": "🌪️ שואב בצד אחד ומעיף בצד השני: מנוע טורבו עוצמתי שמנקה פירורים, חול ושערות מכל פינה צרה ברכב ובבית!",
        "hook_ru": "🌪️ С одной стороны всасывает, с другой выдувает: мощный турбо-мотор 12 000 Па выбивает всю пыль из решеток авто и клавиатуры!",
        "hook_en": "🌪️ Vacuum from the front, turbo blow from the back: 12,000Pa suction clears crumbs, dirt, and car vents with ease!",
        "price_usd": 22.50, "old_usd": 48.00, "rating": 4.8, "reviews": 8400, "orders": "25,000+",
        "specs": {"עוצמת שאיבה": "12,000 Pa מנוע Brushless", "פונקציות": "שואב אבק + מפוח אוויר דחוס + משאבת ואקום", "סוללה": "4000mAh נטענת Type-C", "מסנן": "HEPA רחיץ לשימוש חוזר"},
        "highlights": ["עיצוב דו-צדדי מהפכני: פתח יניקה קדמי ופתח פליטת אוויר דחוס אחורי לפינוי אבק", "מנוע נטול פחמים עמיד המייצר עוצמה חריגה לגודלו הקומפקטי", "מסנן HEPA איכותי הניתן לשטיפה במים ושימוש חוזר ללא הוצאות נוספות", "כולל מגוון פיות צרות, מברשת ושפופרת ניפוח מזרני ים וגלגלי הצלה"]
    },
    "telescopic-rearview-mirror-car-phone-mount": {
        "cat": "auto",
        "title_he": "מעמד טלפון טלסקופי מתכוונן 360° לרכב המתחבר למראה המרכזית (ללא חסימת שדה הראייה)",
        "title_en": "360° Retractable Car Rearview Mirror Phone Mount Holder for Navigation",
        "title_ru": "Телескопический поворотный держатель для смартфона на зеркало заднего вида 360°",
        "hook_he": "📍 ניווט בגובה העיניים: מעמד זרוע טלסקופי יציב שלא נופל מהשמש, מתכוונן לכל זווית ושומר על שדה ראייה נקי!",
        "hook_ru": "📍 Идеальный обзор навигатора: крепится на зеркало заднего вида, регулируется по длине и не отвлекает от дороги!",
        "hook_en": "📍 Eye-level GPS navigation: sturdy 360° telescoping arm clips securely to the rearview mirror with zero windshield blockage!",
        "price_usd": 6.80, "old_usd": 15.00, "rating": 4.8, "reviews": 9200, "orders": "35,000+",
        "specs": {"סיבוב וכוונון": "360° סיבוב מלא + זרוע טלסקופית נשלפת", "חומר": "ABS קשיח עם רפידות סיליקון", "תאימות מראות": "מתאים ל-98% מהמראות ברכבים", "רוחב טלפון": "4.0 עד 7.0 אינץ'"},
        "highlights": ["מונע נפילה של מעמדי ואקום שנמסים בשמש הישראלית על הדשבורד", "מאפשר סיבוב של הטלפון ממצב מאונך למצב מאוזן ביד אחת תוך כדי נהיגה", "מציב את ה-Waze בדיוק בגובה העיניים מבלי לחסום את השמשה הקדמית", "מתקפל בקלות מאחורי המראה כשאינו בשימוש"]
    },
    "retractable-fast-car-charger-dual-cable": {
        "cat": "auto",
        "title_he": "מטען מהיר לרכב למצת עם שני כבלים נשלפים אוטומטית (Type-C + Lightning באורך 80 ס\"מ ו-60W)",
        "title_en": "60W Fast Retractable Car Charger with Built-in Dual Coiled Type-C & iPhone Cables",
        "title_ru": "Быстрая зарядка в прикуриватель 60 Вт с двумя встроенными втягивающимися кабелями",
        "hook_he": "🔌 סדר מושלם ברכב: מטען מצת מהיר עם שני כבלים שנמשכים ונשלפים אוטומטית פנימה בלחיצה — בלי חוטים זרוקים!",
        "hook_ru": "🔌 Порядок в салоне: два кабеля вытягиваются до 80 см и сматываются обратно одним щелчком. Никаких болтающихся проводов!",
        "hook_en": "🔌 Clutter-free car cabin: built-in dual cables extend 80cm and retract automatically with one smooth pull!",
        "price_usd": 12.80, "old_usd": 27.00, "rating": 4.9, "reviews": 7100, "orders": "25,000+",
        "specs": {"הספק": "60W Max Fast Charge", "כבלים מובנים": "USB Type-C + Apple Lightning (נשלפים 80 ס\"מ)", "יציאות נוספות": "USB-A x1 + USB-C x1", "מתח כניסה": "12V-24V (מתאים לפרטי ומשאיות)"},
        "highlights": ["מנגנון סליל פנימי חכם המושך את הכבלים פנימה ברגע שמנתקים את הטלפון", "תומך בטעינה מהירה במקביל של עד 4 מכשירים שונים בו זמנית", "ראש מתכוונן ב-180 מעלות להתאמה לכל זווית של שקע המצת ברכב", "צג מתח LED דיגיטלי המציג את תקינות מצבר הרכב בזמן אמת"]
    },
    "solar-rotating-car-perfume-diffuser": {
        "cat": "auto",
        "title_he": "מפיץ ריח סולארי יוקרתי לרכב המסתובב אוטומטית באור השמש (טבעות מרחפות ארומתרפיות ללא סוללות)",
        "title_en": "Solar Double-Ring Rotating Car Aroma Air Freshener Diffuser (Zero Batteries Needed)",
        "title_ru": "Солнечный вращающийся ароматизатор для авто с эффектом парящих колец (без батареек)",
        "hook_he": "✨ ריח יוקרתי ומראה מהפנט: טבעות מתכת שמסתובבות ומרחפות בכוח השמש ומפיצות ניחוח מרענן ברחבי הרכב!",
        "hook_ru": "✨ Завораживающее вращение: двойные кольца крутятся от солнечного света и плавно разносят приятный аромат по салону!",
        "hook_en": "✨ Mesmerizing levitating rings: spins automatically under sunlight to disperse natural essential fragrance with zero batteries!",
        "price_usd": 7.20, "old_usd": 16.00, "rating": 4.8, "reviews": 5900, "orders": "20,000+",
        "specs": {"הפעלה": "פאנל סולארי פנימי ללא סוללות", "חומר": "סגסוגת אבץ מלוטשת עמידה בחום", "דיסקיות ריח": "עץ בירץ' טבעי הניתן לטפטוף שמן אתרי", "הדבקה": "רפידת סיליקון רחיצה שלא משאירה סימנים"},
        "highlights": ["מסתובב במהירות גבוהה בשמש ומפיץ את הריח באופן אחיד לכל פינות הרכב", "עשוי סגסוגת מתכת עמידה שאינה דוהה או מתעוותת בחום הקיץ הישראלי", "ניתן להוסיף כל בושם או שמן אתרי מועדף על דיסקית העץ הטבעית", "מראה יוקרתי ועתידני המשדרג את מראה הדשבורד"]
    },
    "magnetic-motion-sensor-led-cabinet-light": {
        "cat": "smarthome",
        "title_he": "פס תאורת לד מגנטי דק במיוחד עם חיישן תנועה ואפקט גל אור (למטבח, ארונות בגדים ומדרגות)",
        "title_en": "Ultra-Thin Magnetic Motion Sensor LED Under-Cabinet Light Bar with Cat-Eye Light Ripple",
        "title_ru": "Ультратонкий магнитный LED-светильник с датчиком движения для кухни, шкафов и подсветки полок",
        "hook_he": "💡 אור יוקרתי ברגע שמתקרבים: נדלק אוטומטית בחושך עם אפקט תאורה יוקרתי, נצמד במגנט ונטען פעם בחודשיים!",
        "hook_ru": "💡 Уютный свет без проводки: зажигается при приближении в темноте, крепится на магнит и держит заряд до 2 месяцев!",
        "hook_en": "💡 Instant upscale lighting: turns on automatically as you approach, attaches magnetically anywhere, and lasts up to 60 days per charge!",
        "price_usd": 9.80, "old_usd": 22.00, "rating": 4.9, "reviews": 12500, "orders": "45,000+",
        "specs": {"עובי": "0.9 ס\"מ דק במיוחד", "חיישן": "אינפרא-אדום PIR עד 3 מטר ו-120°", "גווני אור": "3 צבעים (חם, טבעי, קר) + עמעום בהירות", "סוללה": "ליתיום נטענת Type-C"},
        "highlights": ["התקנה ב-3 שניות ללא קידוח או חשמלאי — נצמד עם לוחיות מתכת ומדבקת 3M", "עדשות גל אור מיוחדות המייצרות תבנית תאורה יוקרתית על הקיר", "מצב חכם הפועל רק בחושך וחוסך בסוללה", "נשלף בקלות מהמגנט לצורך טעינה בחיבור Type-C"]
    },
    "automatic-electric-wine-corkscrew-opener": {
        "cat": "smarthome",
        "title_he": "פותחן יין חשמלי אוטומטי מלא + חותך נייר, פיית מזיגה ומשאבת ואקום לשמירת טריות",
        "title_en": "Automatic Electric Wine Bottle Opener Set with Foil Cutter, Aerator & Vacuum Stopper",
        "title_ru": "Электрический штопор для вина в подарочном наборе с аэратором и вакуумной пробкой",
        "hook_he": "🍷 פתיחת יין ב-6 שניות בלחיצת כפתור: חולץ את הפקק בצורה חלקה ללא מאמץ, בלי לפורר את השעם ובלי להזיע!",
        "hook_ru": "🍷 Открывает вино за 6 секунд: штопор сам достает пробку без усилий, не крошит ее и смотрится очень солидно!",
        "hook_en": "🍷 Effortless wine opening in 6 seconds: pulls corks smoothly with one touch without breaking or crumbling cork!",
        "price_usd": 14.50, "old_usd": 32.00, "rating": 4.9, "reviews": 9800, "orders": "35,000+",
        "specs": {"מהירות פתיחה": "6-8 שניות", "רמת רעש": "< 60dB שקט במיוחד", "הפעלה": "סוללות AA או נטענת USB", "ערכה כוללת": "פותחן, חותך רדיד אלומיניום, פיית מזיגה, פקק ואקום"},
        "highlights": ["מנוע פנימי חזק החולץ כל פקק שעם טבעי או סינטטי בלחיצה פשוטה", "חלון שקוף עם תאורת לד כחולה המאפשר לראות את תהליך החליצה", "כולל פקק ואקום השומר על טריות היין הפתוח למשך עד 7 ימים נוספים", "מתנה מושלמת לאירוח, שבתות וחגים"]
    },
    "digital-lcd-measuring-spoon-scale": {
        "cat": "smarthome",
        "title_he": "כף מדידה דיגיטלית חכמה עם משקל אלקטרוני מדויק 0.1 גרם (לתבלינים, קפה, אפייה ותרופות)",
        "title_en": "Digital Kitchen Measuring Spoon Scale 0.1g Precision with LCD Screen for Baking & Spices",
        "title_ru": "Электронная мерная ложка-весы с точностью 0.1 г для специй, кофе и кулинарии",
        "hook_he": "⚖️ דיוק שיא במטבח: שוקלת תבלינים, אבקות, קפה ושמן בדיוק של 0.1 גרם ישירות לתוך הסיר ללא צורך במשקל מגושם!",
        "hook_ru": "⚖️ Идеальная точность для рецептов: взвешивает специи, дрожжи и кофе прямо ложкой с точностью до 0.1 грамма!",
        "hook_en": "⚖️ Precision cooking made easy: measure spices, yeast, and coffee down to 0.1g directly with a single spoon!",
        "price_usd": 5.80, "old_usd": 13.00, "rating": 4.8, "reviews": 11400, "orders": "40,000+",
        "specs": {"טווח שקילה": "0.5 גרם עד 500 גרם", "דיוק": "0.1 גרם", "יחידות מדידה": "g, oz, ct, gn", "תכונות": "פונקציית Tare (איפוס כלי) והקפאת תצוגת משקל (Hold)"},
        "highlights": ["ראש הכף נשלף בקלות לשטיפה מהירה במים", "צג LCD ברור המציג את המשקל מיידית תוך חיסכון בלכלוך כלים", "אידיאלי לדיאטות מדויקות, אפייה עדינה, תיבול ושקילת מזון לחיות מחמד", "כיבוי אוטומטי לאחר דקה לשמירה על חיי הסוללה"]
    },
    "automatic-touchless-foaming-soap-dispenser": {
        "cat": "smarthome",
        "title_he": "מתקן סבון קצף אוטומטי ללא מגע עם חיישן אינפרא-אדום, צג דיגיטלי ומד טמפרטורה",
        "title_en": "Automatic Touchless Foaming Soap Dispenser with Infrared Sensor & Digital Temp Display",
        "title_ru": "Автоматический бесконтактный сенсорный дозатор пенного мыла с термометром",
        "hook_he": "🧼 היגיינה וחיסכון של 70%: מוציא קצף סבון עשיר ומפנק תוך 0.25 שניות בלי לגעת במכשיר, עם סוללה נטענת!",
        "hook_ru": "🧼 Чистота и экономия 70% мыла: превращает мыло в пышную пену за 0.25 секунды без прикосновений к дозатору!",
        "hook_en": "🧼 Touch-free luxury hygiene: dispenses rich, velvety micro-foam in 0.25s, saving up to 70% soap liquid!",
        "price_usd": 13.50, "old_usd": 29.00, "rating": 4.9, "reviews": 8600, "orders": "30,000+",
        "specs": {"מהירות תגובה": "0.25 שניות", "מיכל": "380 מ\"ל שקוף", "טעינה": "USB Type-C (סוללה מובנית)", "חיישן": "אינפרא-אדום חכם מונע טפטוף"},
        "highlights": ["מדללים סבון רגיל עם מים ביחס 1:4 ומקבלים קצף קטיפתי וחיסכון כספי אדיר", "מונע מעבר חיידקים במטבח ובחדר הרחצה בזכות הפעלה ללא מגע", "צג דיגיטלי עליון המציג את טמפרטורת החדר ואחוז הסוללה הנותר", "עמידות למים בתקן IPX5 לשימוש בטוח ליד הכיור"]
    },
    "smart-coffee-mug-warmer-coaster": {
        "cat": "smarthome",
        "title_he": "פלטת חימום חכמה לכוס קפה ותה עם 3 דרגות חום וכיבוי אוטומטי למשרד ולבית",
        "title_en": "Smart Coffee Mug Warmer Coaster with 3 Temp Settings & Auto Shut-Off for Desk",
        "title_ru": "Умная подставка с подогревом для кружки с 3 режимами температуры и автовыключением",
        "hook_he": "☕ הקפה לא יתקרר לעולם: פלטת חימום אלגנטית ששומרת על המשקה החם בטמפרטורה מושלמת (55°C-75°C) לאורך כל היום!",
        "hook_ru": "☕ Кофе больше не остынет: поддерживает идеальную температуру чашки весь рабочий день и сама отключается через 8 часов!",
        "hook_en": "☕ Never sip cold coffee again: keeps your mug at the ideal drinking temp (55°C-75°C) with smart 8H auto-shutoff!",
        "price_usd": 10.90, "old_usd": 24.00, "rating": 4.8, "reviews": 6500, "orders": "20,000+",
        "specs": {"דרגות חום": "55°C, 65°C, 75°C", "משטח חימום": "מתכת עמידה במים קלה לניקוי", "בטיחות": "כיבוי אוטומטי לאחר 8 שעות פעולה", "הספק": "20W חסכוני בחשמל"},
        "highlights": ["מתאים לכל סוגי הכוסות: קרמיקה, זכוכית, נירוסטה ובקבוקי תינוקות", "משטח עמיד למים שניתן לנגב בשנייה במקרה של נזילה או לכלוך", "גודל קומפקטי ואלגנטי שמשתלב מושלם על שולחן המחשב במשרד", "חימום שקט לחלוטין ללא רעשי מאוורר"]
    },
    "electric-gravity-salt-pepper-grinder": {
        "cat": "smarthome",
        "title_he": "מטחנת מלח ופלפל חשמלית אוטומטית הפועלת בהטיה (חיישן כבידה, תאורת LED וכוונון עובי טחינה)",
        "title_en": "Automatic Gravity Electric Salt & Pepper Grinder with Blue LED & Adjustable Coarseness",
        "title_ru": "Гравитационная электрическая мельница для перца и соли с синей LED-подсветкой",
        "hook_he": "🧂 טחינה ביד אחת בלי מאמץ: פשוט מטים את המטחנה מעל הסיר והיא טוחנת אוטומטית פלפל ומלח גס עם תאורת LED!",
        "hook_ru": "🧂 Работает от одного наклона: поверните мельницу над тарелкой, и она сама перемелет специи с приятной синей подсветкой!",
        "hook_en": "🧂 One-handed gravity grind: just flip the grinder over your food and it grinds fresh spices automatically with LED guide!",
        "price_usd": 10.20, "old_usd": 23.00, "rating": 4.8, "reviews": 7800, "orders": "25,000+",
        "specs": {"מנגנון טחינה": "קרמי איכותי שלא מחליד", "הפעלה": "חיישן הטיה Gravity Sensor", "מיכל": "מיכל שקוף גדול בנפח 150 מ\"ל", "כוונון": "בקרת עובי טחינה מגס ועד דק במיוחד"},
        "highlights": ["אידיאלי לבישול כששאר הידיים מלוכלכות או מחזיקות כף — מספיק להטות ביד אחת", "מנגנון טחינה קרמי השומר על הטעם המקורי של התבלינים ואינו מחליד במגע עם מלח", "תאורת LED כחולה המאירה בדיוק את כמות התבלין שנפלה לתוך המנה", "פתח מילוי רחב שאינו מלכלך את השיש"]
    },
    "soft-silicone-dog-paw-cleaner-cup": {
        "cat": "pets",
        "title_he": "כוס לשטיפת כפות רגליים לכלבים עם סיבי סיליקון רכים 360° (מונעת עקבות בוץ ולכלוך בבית)",
        "title_en": "Soft Silicone Portable Dog Paw Cleaner Cup 360° Mud Remover for Small & Large Dogs",
        "title_ru": "Стакан-лапомойка с мягкими силиконовыми щетинками 360° для собак и кошек",
        "hook_he": "🐾 בית נקי אחרי כל טיול: מכניסים את כף הרגל של הכלב לכוס ומסובבים — כל הבוץ והחול נשטפים תוך 10 שניות!",
        "hook_ru": "🐾 Чистые лапы за 10 секунд: мягкие силиконовые ворсинки бережно отмывают песок и грязь после прогулки без возни в ванной!",
        "hook_en": "🐾 Keep muddy paw prints outside: gentle silicone bristles scrub away mud, sand, and dirt in seconds after park walks!",
        "price_usd": 6.90, "old_usd": 15.00, "rating": 4.8, "reviews": 9200, "orders": "30,000+",
        "specs": {"חומר": "100% סיליקון רפואי רך נעים למגע", "מבנה": "מברשת פנימית נשלפת לשטיפה", "מידות": "מתאים לכלבים קטנים, בינוניים וגדולים", "תכונות": "מונע שריטות או כאב בכריות כף הרגל"},
        "highlights": ["סיבי סיליקון גמישים המנקים ביסודיות בין האצבעות בלי לפצוע או להכאיב", "חוסך את הצורך לסחוב את הכלב לתוך האמבטיה אחרי כל טיול בגשם או בפארק", "קל מאוד לפירוק ושטיפה תחת הברז תוך שניות", "ידידותי לסביבה ועמיד לאורך שנים"]
    },
    "automatic-ultrasonic-dog-barking-deterrent": {
        "cat": "pets",
        "title_he": "מכשיר אולטרסוניק אוטומטי להרגעת נביחות כלבים (בטוח ולא מזיק, טווח 15 מטר ועמידות לגשם)",
        "title_en": "Automatic Ultrasonic Anti-Barking Dog Training Deterrent Device (Safe, 50ft Range, IPX4)",
        "title_ru": "Ультразвуковой автоматический антилай для собак (безопасный, дальность 15 м, влагозащита)",
        "hook_he": "🤫 שקט ושלווה בבית ובשכונה: מזהה נביחה ומשמיע צליל אולטרסוניק עדין שמרגיע את הכלב ומפסיק נביחות בלי להזיק!",
        "hook_ru": "🤫 Тишина и спокойствие: автоматически улавливает лай и издает безопасный ультразвуковой сигнал, отучая собаку шуметь!",
        "hook_en": "🤫 Peaceful home without yelling: safely stops excessive barking using humane ultrasonic sound up to 50ft away!",
        "price_usd": 16.20, "old_usd": 35.00, "rating": 4.7, "reviews": 5100, "orders": "15,000+",
        "specs": {"טווח פעולה": "עד 15 מטר (50 Feet)", "רמות תדר": "3 מצבי תדר שונים לכלבים קטנים וגדולים", "עמידות למזג אוויר": "IPX4 עמיד לגשם ותלייה בחוץ", "סוללה": "נטענת USB חסכונית"},
        "highlights": ["פתרון הומני ובטוח לחלוטין — ללא שוקים חשמליים, ללא חומרים מגרים וללא כאב", "חיישן קול פנימי המזהה נביחות אוטומטית ומגיב מיד ללא צורך בהתערבות ידנית", "מתאים לתלייה על גדר החצר, במרפסת או בתוך הסלון", "אינו נשמע לאוזן אנושית ומחזיר את השקט לבית"]
    },
    "digital-laser-measure-distance-meter-40m": {
        "cat": "tools",
        "title_he": "מד טווח לייזר דיגיטלי מקצועי 40 מטר עם צג LCD מואר, חיישן זווית וחישוב שטח ונפח",
        "title_en": "40M Digital Handheld Laser Distance Meter Rangefinder with Backlit LCD & Angle Sensor",
        "title_ru": "Цифровой лазерный дальномер 40 м с датчиком угла, расчетом площади и объема",
        "hook_he": "📏 מדידה מדויקת בשבריר שנייה: מודד מרחקים עד 40 מטר בדיוק של 2 מ\"מ ומחשב שטחים ונפחים בלחיצת כפתור אחת!",
        "hook_ru": "📏 Забудьте про рулетки: измеряет расстояния до 40 м с точностью 2 мм и сам считает площадь и объем комнаты за 0.5 сек!",
        "hook_en": "📏 Measure rooms in 0.5 seconds: laser rangefinder measures up to 40m with 2mm accuracy and auto area/volume math!",
        "price_usd": 18.50, "old_usd": 39.00, "rating": 4.9, "reviews": 8900, "orders": "30,000+",
        "specs": {"טווח מדידה": "0.05 עד 40 מטר", "דיוק": "±2 מ\"מ", "פונקציות": "מרחק, שטח, נפח, פיתגורס, מדידה רציפה", "צג": "LCD עם תאורה אחורית לשימוש בחושך"},
        "highlights": ["חוסך את הצורך בעזרה של אדם נוסף להחזקת מטר מדידה מיושן", "כולל פונקציית פיתגורס חכמה למדידת גובה קירות ותקרות מרחוק", "גוף קומפקטי עמיד בפני נפילות ואבק בתקן IP54", "שומר בזיכרון את 20 המדידות האחרונות לעבודה נוחה"]
    },
    "18in1-snowflake-edc-pocket-multi-tool": {
        "cat": "tools",
        "title_he": "מפתח רב-שימושי 18 ב-1 בצורת פתית שלג מפלדת אל-חלד קשיחה (מברגים, מפתחות ברגים ופותחן)",
        "title_en": "18-in-1 Stainless Steel Snowflake Multi-Tool EDC Keychain Screwdriver Wrench",
        "title_ru": "Мультитул-снежинка 18-в-1 из нержавеющей стали (отвертки, ключи и открывалка в кармане)",
        "hook_he": "❄️ ארגז כלים שלם במחזיק המפתחות: 18 כלי עבודה שימושיים מפלדה קשיחה בגודל של מטבע לתיקוני חירום בכל מקום!",
        "hook_ru": "❄️ Целый ящик инструментов в кармане: 18 функций от отверток до ключей в форме снежинки размером с брелок!",
        "hook_en": "❄️ Entire toolbox on your keychain: 18 handy tools including hex wrenches, screwdrivers & bottle opener in one solid steel snowflake!",
        "price_usd": 3.40, "old_usd": 8.00, "rating": 4.8, "reviews": 16500, "orders": "50,000+",
        "specs": {"חומר": "פלדת אל-חלד 420 עמידה בקורוזיה", "קוטר": "6.4 ס\"מ", "משקל": "80 גרם", "כלים כלולים": "מברג שטוח, פיליפס, 6 מפתחות אלן, 7 מפתחות ברגים, פותחן בקבוקים וחור למפתחות"},
        "highlights": ["עיצוב ייחודי וקומפקטי שמתאים לתלייה על תיק גב, מחזיק מפתחות או באוטו", "מצוין לתיקון אופניים, פתיחת קופסאות, הידוק ברגי רהיטים וקמפינג", "פלדת אל-חלד מוקשחת שאינה מתעקמת או מחלידה", "פריט חובה לכל חובב EDC וטיולים"]
    },
    "rechargeable-mini-cob-keychain-flashlight": {
        "cat": "under10",
        "title_he": "פנס מחזיק מפתחות COB עוצמתי נטען USB (פנס הצפה 800 לומן, מגנט חזק, פותחן ומעמד שולחני)",
        "title_en": "Mini Rechargeable COB Keychain Work Flashlight 800 Lumens with Magnet & Bottle Opener",
        "title_ru": "Яркий мини-фонарик брелок COB 800 люмен на магните с открывалкой и штативом",
        "hook_he": "🔦 תאורה מסנוורת בגודל קופסת גפרורים: פנס הצפה עוצמתי 800 לומן שנצמד במגנט למכסה מנוע וכולל פותחן בקבוקים!",
        "hook_ru": "🔦 Светит ярче автомобильной фары: 800 люмен в корпусе размером со спичечный коробок, магнит к металлу и открывалка!",
        "hook_en": "🔦 Blinding brightness in a matchbox size: 800-lumen magnetic floodlight sticks to car hoods and pops bottles effortlessly!",
        "price_usd": 3.80, "old_usd": 9.00, "rating": 4.9, "reviews": 22400, "orders": "50,000+",
        "specs": {"עוצמת הארה": "800 Lumens COB Floodlight", "מצבי תאורה": "4 מצבים (חזק, חסכוני, הבהוב חירום, עוצמת שיא)", "תוספות": "מגנט חזק בגב, רגלית מעמד 180°, פותחן בקבוקים", "סוללה": "500mAh נטענת Type-C"},
        "highlights": ["מגנט ניאודימיום מובנה המאפשר להצמיד את הפנס לפח הרכב בזמן החלפת גלגל בלילה", "מייצר אלומת אור רחבה המאירה חדר שלם למרות גודלו המזערי", "כולל תופסן קרבינר לתלייה על לולאת מכנסיים או תיק", "עמיד בגשם ורוח לשימוש בתנאי שטח"]
    },
    "anti-theft-rfid-blocking-pop-up-cardholder": {
        "cat": "under10",
        "title_he": "ארנק כרטיסים קומפקטי מקרבון עם קפיץ שליפה מהיר והגנת RFID נגד גניבת אשראי",
        "title_en": "Slim Carbon Fiber Pop-Up Cardholder Wallet with Anti-Theft RFID Blocking Protection",
        "title_ru": "Тонкий картхолдер из карбона с автоматическим выбросом карт и защитой RFID",
        "hook_he": "💳 שליפת כרטיסים בשליק אחד: לוחצים על הידית וכל הכרטיסים קופצים בצורת מניפה נוחה, עם הגנה מגניבת נתונים!",
        "hook_ru": "💳 Выброс карт веером за секунду: нажимаете рычажок, карты аккуратно выезжают, а чип RFID защищает от списаний!",
        "hook_en": "💳 Instant card ejection with one click: fan-out mechanism presents all cards neatly while RFID shield stops electronic pickpockets!",
        "price_usd": 4.90, "old_usd": 12.00, "rating": 4.8, "reviews": 14800, "orders": "45,000+",
        "specs": {"קיבולת": "5-6 כרטיסי אשראי בתא האלומיניום + תא שטרות", "הגנה": "חסימת RFID/NFC מלאה", "חומר": "אלומיניום תעופתי + ציפוי סיבי פחמן (Carbon Fiber)", "עובי": "1.2 ס\"מ בלבד"},
        "highlights": ["מנגנון פטנט ייעודי המקפיץ את הכרטיסים במדורג כך שניתן לבחור את הכרטיס המבוקש מיד", "מגן מפני סורקים אלחוטיים המנסים לגנוב פרטי אשראי בהליכה ברחוב או ברכבת", "דק וקליל — לא יוצר בליטה מכוערת בכיס המכנסיים", "תופסן שטרות וכרטיסי ביקור חיצוני מובנה"]
    },
    "mini-portable-heat-bag-sealer-cutter": {
        "cat": "under10",
        "title_he": "מכשיר מיני נטען לאיטום שקיות חטיפים בחום 2 ב-1 עם סכין חיתוך נסתרת ומגנט למקרר",
        "title_en": "2-in-1 Rechargeable Mini Bag Sealer & Hidden Slicer Cutter with Refrigerator Magnet",
        "title_ru": "Портативный мини-запайщик пакетов 2-в-1 со встроенным скрытым ножом и магнитом на холодильник",
        "hook_he": "🥨 שומר על טריות הצ'יפס: אוטם שקיות חטיפים ומזון פתוחות בחום תוך 3 שניות, כדי שהאוכל יישאר פריך וטרי שבועות!",
        "hook_ru": "🥨 Чипсы больше не отсыреют: герметично запаивает открытые пакеты с едой за 3 секунды, крепится прямо на холодильник!",
        "hook_en": "🥨 Keep snacks crunchy forever: seals open chip and food bags airtight in 3 seconds to prevent staleness and moisture!",
        "price_usd": 4.20, "old_usd": 10.00, "rating": 4.8, "reviews": 11800, "orders": "35,000+",
        "specs": {"טכנולוגיה": "חימום מהיר PTC ללא זמן המתנה", "מבנה": "צד אחד אוטם בחום, צד שני סכין לפתיחה קלה", "סוללה": "נטענת USB Type-C מובנית", "מגנט": "מגנט אחורי להצמדה לדלת המקרר"},
        "highlights": ["אוטם הרמטית שקיות צ'יפס, אגוזים, דגני בוקר, קטניות ושקיות הקפאה", "סכין נסתרת מובנית לפתיחה מהירה של אריזות ללא צורך במספריים", "נטען ב-USB — ללא צורך בסוללות חד-פעמיות", "נצמד למקרר ותמיד זמין לשליפה מהירה"]
    },
    "360-splash-proof-kitchen-faucet-aerator": {
        "cat": "under10",
        "title_he": "ראש מאריך לברז מטבח מסתובב 360° עם 3 מצבי זרימה (מסנן מים, מונע התזות וחוסך 50% מים)",
        "title_en": "360° Swivel Splash Filter Kitchen Faucet Aerator Nozzle with 3 Water Modes",
        "title_ru": "Поворотная насадка-аэратор на кран 360° с 3 режимами струи и фильтром от брызг",
        "hook_he": "💧 סוף לשלוליות מסביב לכיור: ראש ברז גמיש שמסתובב 360°, מעניק זרם חזק לשטיפת צלחות וחוסך חצי מחשבון המים!",
        "hook_ru": "💧 Больше никаких брызг на одежду: гибкая насадка на кран 360° с 3 режимами отмывает жир мощной струей и экономит воду!",
        "hook_en": "💧 Zero sink splashback: 360° swivel faucet head reaches every corner of your sink with 3 high-pressure spray modes!",
        "price_usd": 4.50, "old_usd": 11.00, "rating": 4.8, "reviews": 19400, "orders": "50,000+",
        "specs": {"סיבוב": "360 מעלות לכל פינה בכיור", "מצבי זרימה": "מצב גשם עדין, מצב סילון עוצמתי, מצב משולב", "חומר": "נירוסטה מחוזקת + פליז עמיד באבנית", "התקנה": "הברגה ישירה לכל ברז סטנדרטי"},
        "highlights": ["מגיע לכל פינה בכיור ומאפשר שטיפה קלה של סירים גדולים וכיורים כפולים", "טכנולוגיית ערבוב אוויר המגבירה את לחץ המים וחוסכת בין 30% ל-50% בצריכת המים", "מסנן רב-שכבתי פנימי המסנן חלודה ולכלוך גס מצנרת המים", "התקנה פשוטה בידיים ללא צורך במפתח אינסטלטורים"]
    }
}

print(f"Total new batch items to integrate: {len(new_items)}")

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

# Existing slugs
existing_slugs = {p["slug"]: p for p in db["products"]}

for idx, item in enumerate(new_items, 1):
    slug = item["slug"]
    pid = f"real-{112 + idx}"
    meta = META.get(slug)
    if not meta:
        print(f"Skipping unknown meta for {slug}")
        continue
    
    # Download images locally
    remote_imgs = item.get("images", [])
    local_gallery = []
    print(f"Downloading images for {slug}...")
    
    for img_idx, img_url in enumerate(remote_imgs[:5]):
        ext = ".png" if ".png" in img_url else ".jpg"
        fname = f"{slug}-{img_idx+1}{ext}"
        local_path = os.path.join(IMG_DIR, fname)
        web_path = f"assets/img/{fname}"
        
        ok = download_file(img_url, local_path)
        if ok:
            local_gallery.append(web_path)
        else:
            local_gallery.append(img_url)
        time.sleep(0.3)

    if not local_gallery:
        continue

    product_record = {
        "id": pid,
        "slug": slug,
        "category": meta["cat"],
        "badge": "מציאה גאונית",
        "badge_i18n": {
            "he": "מציאה גאונית",
            "en": "Hidden Gem",
            "ru": "Редкая находка",
            "es": "Chollo Top",
            "fr": "Pépite Tech",
            "de": "Geheimtipp",
            "ar": "صفقة ذكية"
        },
        "choice_badge": "Choice",
        "title": meta["title_he"],
        "title_i18n": {
            "he": meta["title_he"],
            "en": meta["title_en"],
            "ru": meta["title_ru"],
            "es": meta["title_en"],
            "fr": meta["title_en"],
            "de": meta["title_en"],
            "ar": meta["title_he"]
        },
        "card_hook": meta["hook_he"],
        "card_hook_i18n": {
            "he": meta["hook_he"],
            "en": meta["hook_en"],
            "ru": meta["hook_ru"],
            "es": meta["hook_en"],
            "fr": meta["hook_en"],
            "de": meta["hook_en"],
            "ar": meta["hook_he"]
        },
        "price_usd": meta["price_usd"],
        "old_price_usd": meta["old_usd"],
        "discount_pct": int(round((1 - meta["price_usd"] / meta["old_usd"]) * 100)),
        "rating": meta["rating"],
        "reviews_count": meta["reviews"],
        "orders_count": meta["orders"],
        "affiliate_url": item.get("affiliate_url", "https://s.click.aliexpress.com/e/_c4XMCrnL"),
        "image": local_gallery[0],
        "gallery": local_gallery,
        "highlights": meta.get("highlights", []),
        "specs": meta.get("specs", {})
    }

    if slug in existing_slugs:
        # update existing
        for i, existing in enumerate(db["products"]):
            if existing["slug"] == slug:
                db["products"][i] = product_record
                break
    else:
        db["products"].append(product_record)

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"\nCatalog successfully integrated! Total products in catalog now: {len(db['products'])}")
