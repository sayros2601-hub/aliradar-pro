import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

ENRICHMENTS = {
    "real-101": {
        "choice_badge": "Choice",
        "card_hook": "⚡ חוסך 80% מזמן הטעינה: מטען GaN דק פי 2 שמטעין לפטופ וסמארטפון במקביל ללא התחממות ופטור ממס ($75)!",
        "card_hook_i18n": {
            "he": "⚡ חוסך 80% מזמן הטעינה: מטען GaN דק פי 2 שמטעין לפטופ וסמארטפון במקביל ללא התחממות ופטור ממס ($75)!",
            "en": "⚡ Cuts charging time by 80%: ultra-slim GaN tech powers laptop & phone simultaneously with zero heat. Fits anywhere!",
            "ru": "⚡ Заряжает на 80% быстрее: ультратонкая GaN-зарядка 100 Вт питает ноутбук и смартфон одновременно без нагрева!",
            "es": "⚡ Carga un 80% más rápido: tecnología GaN ultra fina para portátil y móvil a la vez sin calentamiento.",
            "fr": "⚡ Charge 80% plus rapide : chargeur GaN ultra-fin 100W pour PC portable et smartphone sans surchauffe.",
            "de": "⚡ Lädt 80% schneller: Ultra-dünnes 100W GaN Ladegerät für Laptop & Smartphone ohne Überhitzung.",
            "ar": "⚡ شحن أسرع بنسبة 80%: شاحن GaN فائق النحافة بقدرة 100 واط للكمبيوتر المحمول والهاتف معاً بدون حرارة!"
        },
        "highlights": [
            "טכנולוגיית GaN מתקדמת — 50% קטן וקל יותר ממטען מקורי של Apple",
            "הספק מרבי של 100W התומך בטעינת MacBook Pro / Dell XPS במהירות מקסימלית",
            "מערכת הגנה תרמית Thermal Guard 2.0 המודדת טמפרטורה 800 פעמים בשנייה",
            "תואם לכל הפרוטוקולים: PD3.0, QC4.0+, PPS, AFC, FCP"
        ],
        "specs": {
            "הספק מרבי": "100W GaN Fast Charge",
            "יציאות": "USB-C x2 + USB-A x1",
            "טכנולוגיה": "Navitas GaNFast III Chipset",
            "תאימות": "MacBook Pro/Air, iPhone 16/15/14, Samsung Galaxy S25/S24, iPad",
            "מתח כניסה": "100-240V (מתאים לשימוש בינלאומי מלא)"
        }
    },
    "real-102": {
        "choice_badge": "Choice",
        "card_hook": "🚗 עין חדה ביום ובלילה: מצלמת 2K חדה עם ראיית לילה קריסטלית f/1.55 ושמירה בחניה 24/7 מפני פגיעות ושריטות!",
        "card_hook_i18n": {
            "he": "🚗 עין חדה ביום ובלילה: מצלמת 2K חדה עם ראיית לילה קריסטלית f/1.55 ושמירה בחניה 24/7 מפני פגיעות ושריטות!",
            "en": "🚗 Day & night clarity: crisp 2K 1440P HDR with f/1.55 night aperture & 24H parking collision guard to catch license plates!",
            "ru": "🚗 Читает номера в темноте: запись 2K с диафрагмой f/1.55, ночным HDR и круглосуточным датчиком удара на парковке 24/7!",
            "es": "🚗 Claridad total día y noche: resolución 2K con apertura f/1.55, visión nocturna y vigilancia en aparcamiento 24H.",
            "fr": "🚗 Vision parfaite jour et nuit : résolution 2K 1440P, ouverture f/1.55 et surveillance parking 24h/24.",
            "de": "🚗 Glasklare Sicht Tag & Nacht: 2K 1440P mit f/1.55 Blende und 24h Parkplatzüberwachung bei Erschütterung.",
            "ar": "🚗 وضوح فائق ليلاً ونهاراً: دقة 2K مع فتحة عدسة f/1.55 وحماية للموقف على مدار 24 ساعة لكشف لوحات السيارات!"
        },
        "highlights": [
            "חיישן 2K ברזולוציה 1440P עם עדשת זווית רחבה 143° לכיסוי מלא של 3 נתיבים",
            "מפתח צמצם רחב במיוחד f/1.55 לקליטת אור מקסימלית בלילה וזיהוי לוחיות רישוי",
            "חיישן G מובנה הנועל אוטומטית סרטונים בזמן בלימת חירום או פגיעה בחניה",
            "שליטה מלאה דרך אפליקציה ייעודית ב-Wi-Fi ללא צורך בהוצאת כרטיס הזיכרון"
        ],
        "specs": {
            "רזולוציה": "2560x1440P (2K QHD)",
            "זווית צילום": "143° Ultra-Wide FOV",
            "צמצם עדשה": "f/1.55 Super Night Vision",
            "קישוריות": "Wi-Fi 2.4GHz + חיבור אפליקציית 70mai",
            "כרטיס נתמך": "MicroSD עד 128GB (Class 10 U3)"
        }
    },
    "real-103": {
        "choice_badge": "Choice",
        "card_hook": "💨 לא נתקעים בדרך: קומפרסור אלחוטי שמנפח גלגל רכב ב-3 דקות, עוצר אוטומטית וכולל פנס חירום עוצמתי!",
        "card_hook_i18n": {
            "he": "💨 לא נתקעים בדרך: קומפרסור אלחוטי שמנפח גלגל רכב ב-3 דקות, עוצר אוטומטית וכולל פנס חירום עוצמתי!",
            "en": "💨 Never get stranded: cordless pump inflates a car tire in 3 mins, auto-stops at exact PSI, plus built-in emergency LED!",
            "ru": "💨 Забудьте об очередях на шиномонтаже: накачивает колесо за 3 минуты, сам отключается на нужном давлении. Фонарик в комплекте!",
            "es": "💨 Nunca te quedes tirado: inflador inalámbrico que llena un neumático en 3 min con apagado automático y linterna LED.",
            "fr": "💨 Ne tombez plus en panne : gonfleur sans fil qui gonfle un pneu en 3 min avec arrêt automatique et lampe LED.",
            "de": "💨 Nie wieder platte Reifen: Kabelloser Kompressor pumpt Autoreifen in 3 Min auf mit Auto-Stopp & LED-Notlicht.",
            "ar": "💨 لا تقلق من ثقب الإطارات: منفاخ لاسلكي يملأ الإطار خلال 3 دقائق ويتوقف تلقائياً مع كشاف طوارئ مدمج!"
        },
        "highlights": [
            "לחץ ניפוח עצמאי עד 150PSI המתאים לרכבים פרטיים, ג'יפים, אופנועים, אופניים וכדורים",
            "מנגנון כיבוי חכם אוטומטי המפסיק את הניפוח ברגע שמגיעים ללחץ שהוגדר מראש",
            "סוללת ליתיום מובנית 4000mAh המאפשרת עבודה ללא כבלים או חיבור למצת הרכב",
            "צג דיגיטלי דיוק גבוה המציג את הלחץ בזמן אמת ב-PSI, BAR, KPA"
        ],
        "specs": {
            "לחץ מרבי": "150 PSI / 10.3 BAR",
            "קיבולת סוללה": "4000mAh (טעינת USB-C מהירה)",
            "זרימת אוויר": "25 ליטר לדקה",
            "פונקציות": "מד לחץ דיגיטלי, פנס LED חירום (כולל SOS)",
            "אביזרים כלולים": "4 מתאמים שונים + צינור ניפוח גמיש מחוזק"
        }
    },
    "real-104": {
        "choice_badge": "Choice",
        "card_hook": "🐾 שלווה ונוחות שיא: מיטת דונאט אורטופדית שמפחיתה חרדה אצל כלבים וחתולים, עם רוכסן לשליפה וכביסה במכונה!",
        "card_hook_i18n": {
            "he": "🐾 שלווה ונוחות שיא: מיטת דונאט אורטופדית שמפחיתה חרדה אצל כלבים וחתולים, עם רוכסן לשליפה וכביסה במכונה!",
            "en": "🐾 Total pet comfort: orthopaedic calming donut bed reduces anxiety, with a full zippered removable cover for washing!",
            "ru": "🐾 Здоровый сон без стресса: ортопедическая плюшевая лежанка-пончик снимает тревожность, чехол на молнии для стирки!",
            "es": "🐾 Alivio y calma para tu mascota: cama donut ortopédica antiestrés con funda extraíble con cremallera lavable.",
            "fr": "🐾 Sommeil apaisant pour chien et chat : panier orthopédique anti-stress avec housse déhoussable et lavable.",
            "de": "🐾 Himmlischer Schlaf: Orthopädisches Anti-Angst Donutbett mit abnehmbarem waschbarem Reißverschlussbezug.",
            "ar": "🐾 نوم هادئ بدون قلق: سرير دائري مريح يخفف التوتر لدى القطط والكلاب مع غطاء قابل للفك والغسيل في الغسالة!"
        },
        "highlights": [
            "שוליים מוגבהים ב-360° המעניקים תמיכה אורטופדית לראש ולצוואר ומשרים ביטחון",
            "פרוות פלוש סינטטית סופר-רכה באורך 4 ס\"מ המחקה את חמימות פרוות האם",
            "תחתית מונעת החלקה עם כפתורי סיליקון השומרים על המיטה יציבה על כל ריצוף",
            "כיסוי נשלף במלואו באמצעות רוכסן נסתר — כביסה נוחה במכונה ב-30 מעלות"
        ],
        "specs": {
            "חומר": "פלוש פרימיום 4 ס\"מ + מילוי כותנת PP נושמת",
            "תכונות": "כיסוי רוכסן נשלף, תחתית Anti-Slip עמידה למים",
            "מידות זמינות": "50 ס\"מ, 60 ס\"מ, 70 ס\"מ, 80 ס\"מ",
            "טיפול": "כביסה עדינה במכונה / ייבוש באוויר"
        }
    },
    "real-105": {
        "choice_badge": "Choice",
        "card_hook": "✨ הלהיט הוויראלי בטיקטוק: תרסיס אדים עדין שמונע התעופפות פרווה ואוסף 95% מהשערות הנושרות במשיכה אחת נקייה!",
        "card_hook_i18n": {
            "he": "✨ הלהיט הוויראלי בטיקטוק: תרסיס אדים עדין שמונע התעופפות פרווה ואוסף 95% מהשערות הנושרות במשיכה אחת נקייה!",
            "en": "✨ Viral TikTok phenomenon: gentle nano-mist stops flying fur and grooms out 95% of loose undercoat in one effortless swipe!",
            "ru": "✨ Вирусный хит: мягкое распыление микропара осаждает шерсть, избавляя от летающих волосков и вычесывая подшёрсток!",
            "es": "✨ Furor viral en redes: microvapor suave que elimina el pelo suelto y la electricidad estática de una sola pasada.",
            "fr": "✨ Le phénomène viral : brumisation douce qui capture 95% des poils morts sans aucune électricité statique.",
            "de": "✨ Viral auf TikTok: Sanfter Feuchtigkeitsnebel bindet lose Haare und entfernt 95% der Unterwolle auf einen Zug.",
            "ar": "✨ الظاهرة الأكثر انتشاراً: رذاذ بخار لطيف يمنع تطاير الفرو ويزيل 95% من الشعر المتساقط بتمريرة واحدة!"
        },
        "highlights": [
            "טכנולוגיית אולטרסוניק המייצרת ערפל ננו-עדין שאינו מרטיב את הפרווה אך מונע חשמל סטטי",
            "שיני סיליקון רכות ומעוגלות המעסות את עור חיית המחמד וממריצות את זרימת הדם",
            "מנגנון הסרת שיער קלה בלחיצה אחת — כל הפרווה שנאספה יורדת כיחידה אחת",
            "סוללה נטענת מובנית בחיבור Type-C עם זמן עבודה של שבועות לטעינה"
        ],
        "specs": {
            "טכנולוגיה": "Nano-Mist Ultrasonic Vaporizer",
            "חומר שיניים": "סיליקון רפואי רך (ללא כאב או משיכה)",
            "סוללה": "ליתיום נטענת ב-USB Type-C",
            "מיכל נוזלים": "מתאים למים רגילים או תוסף שמפו ללא שטיפה"
        }
    },
    "real-106": {
        "choice_badge": "Choice",
        "card_hook": "🎾 מעסיק את החתול שעות: כדור מתגלגל חכם שמתחמק ממכשולים, זז לבד כמו עכבר אמיתי ונטען ב-USB!",
        "card_hook_i18n": {
            "he": "🎾 מעסיק את החתול שעות: כדור מתגלגל חכם שמתחמק ממכשולים, זז לבד כמו עכבר אמיתי ונטען ב-USB!",
            "en": "🎾 Hours of pet fun: smart rolling ball navigates around furniture, mimics real prey movement, and charges via USB!",
            "ru": "🎾 Спасение от скуки: умный мячик сам катается по комнате, объезжает ножки столов и будит охотничий инстинкт!",
            "es": "🎾 Diversión sin fin: pelota inteligente que esquiva obstáculos y rueda sola imitando a una presa real. Recargable USB.",
            "fr": "🎾 Fini l'ennui pour votre chat : balle interactive avec évitement d'obstacles et mouvements réalistes. Recharge USB.",
            "de": "🎾 Stundenlanger Spielspaß: Smarter Ball weicht Möbeln automatisch aus und weckt den natürlichen Jagdtrieb.",
            "ar": "🎾 تسلية لا تنتهي لحيوانك: كرة ذكية تدور بمفردها وتتفادى العوائق وتحاكي الفريسة الحقيقية قابلة للشحن عبر USB!"
        },
        "highlights": [
            "חיישן תנועה חכם המשנה כיוון אוטומטית בכל מפגש עם קיר, רהיט או פינה",
            "שני מצבי משחק: מצב חכם (נרדם לאחר 5 דקות ומתעורר בנגיעת כף רגל) ומצב רגיל",
            "מעטפת סיליקון שקטה בולמת זעזועים שאינה מרעישה על רצפות פרקט וגרניט פורצלן",
            "כולל זנב נוצות/סרט מתחלף המגביר את המשיכה והסקרנות של החתול"
        ],
        "specs": {
            "קוטר": "43 מ\"מ (בגודל אידיאלי למשחק חתולים וגורים)",
            "חומר מעטפת": "סיליקון בטוח למאכל + ABS עמיד",
            "טעינה": "Type-C (שעה לטעינה מלאה)",
            "זמן עבודה": "עד 3 שעות משחק רציף"
        }
    },
    "real-107": {
        "choice_badge": "Choice",
        "card_hook": "🎯 משחק ללא ידיים: קולר לייזר קליל שמקרין נקודת ציד בדיוק מול כפות הרגליים ומפעיל את החתול לבד!",
        "card_hook_i18n": {
            "he": "🎯 משחק ללא ידיים: קולר לייזר קליל שמקרין נקודת ציד בדיוק מול כפות הרגליים ומפעיל את החתול לבד!",
            "en": "🎯 Hands-free exercise: ultra-light collar projects a safe laser dot ahead of pet paws for non-stop active playtime!",
            "ru": "🎯 Игра без вашего участия: невесомый ошейник с безопасным лазером проецирует точку перед лапками питомца!",
            "es": "🎯 Juego manos libres: collar láser ligero que proyecta el punto de caza delante del gato manteniéndolo activo.",
            "fr": "🎯 Jeu 100% autonome : collier ultra-léger avec faisceau laser doux pour faire courir votre chat sans effort.",
            "de": "🎯 Freihändiges Katzentraining: Federleichtes Halsband projiziert einen sicheren Laserpunkt für garantierten Spielspaß.",
            "ar": "🎯 لعب تلقائي بدون تدخل: طوق ليزر فائق الخفة يسلط نقطة الصيد أمام خطوات القطة لتشجيعها على الحركة والنشاط!"
        },
        "highlights": [
            "משקל נוצה של 29 גרם בלבד — עשוי TPU רך וגמיש שאינו מפריע לצוואר החתול",
            "ראש לייזר עם זווית מתכווננת עד 41° המכוון את הנקודה למרחק משחק מושלם",
            "טיימר חכם מובנה המכבה את הלייזר לאחר 15 דקות למניעת עייפות יתר ומפעיל מחדש אחרי שעה וחצי",
            "סוללת ליתיום נטענת ב-USB המספקת עד שבוע שימוש בטעינה אחת"
        ],
        "specs": {
            "משקל": "29 גרם בלבד",
            "חומר": "TPU גמיש וידידותי לעור חיות מחמד",
            "היקף צוואר": "מתכוונן מ-20 עד 31 ס\"מ",
            "סוללה": "נטענת USB Type-C מובנית"
        }
    },
    "real-108": {
        "choice_badge": "Choice",
        "card_hook": "🏠 שדרוג הבית החכם ב-$11: פתיחה וסגירה של שער החניה ישירות מהסמארטפון עם התראה כשנשכח פתוח!",
        "card_hook_i18n": {
            "he": "🏠 שדרוג הבית החכם ב-$11: פתיחה וסגירה של שער החניה ישירות מהסמארטפון עם התראה כשנשכח פתוח!",
            "en": "🏠 $11 Smart Home Upgrade: open & close your gate or garage directly from your smartphone with left-open alerts!",
            "ru": "🏠 Умный дом за $11: открывайте ворота и шлагбаум с телефона из любого места и получайте уведомления, если они открыты!",
            "es": "🏠 Domótica por $11: abre y cierra la puerta del garaje desde el móvil y recibe avisos si se queda abierta.",
            "fr": "🏠 Maison connectée à 11$ : contrôlez votre porte de garage depuis votre smartphone avec alertes d'ouverture.",
            "de": "🏠 Smart Home für 11$: Garagentor und Hoftor bequem per Smartphone steuern mit Erinnerung bei offenem Tor.",
            "ar": "🏠 ترقية ذكية لمنزلك بـ 11$: تحكم في فتح وإغلاق بوابة المرآب عبر الهاتف الذكي مع تنبيه عند تركها مفتوحة!"
        },
        "highlights": [
            "מתחבר בקלות לכל מנוע שער חניה קיים בחיבור שני חוטים פשוט (ללא צורך בחשמלאי)",
            "חיישן מגנטי כלול המזהה אם השער פתוח או סגור ומציג סטטוס מדויק באפליקציה",
            "תמיכה מלאה בפקודות קוליות דרך Google Assistant, Alexa וקיצורי דרך של Siri",
            "הגדרת זמני סגירה אוטומטית בלילה למניעת מצב שבו השער נשכח פתוח"
        ],
        "specs": {
            "פרוטוקול": "Tuya Smart / Smart Life (WiFi 2.4GHz או Zigbee)",
            "מתח פעולה": "AC 100-240V 50/60Hz",
            "תאימות": "כל מנועי השערים והתריסים החשמליים הסטנדרטיים",
            "אפליקציה": "Tuya Smart / Smart Life (iOS & Android)"
        }
    },
    "real-109": {
        "choice_badge": "Choice",
        "card_hook": "🔧 פירוק ותיקון מקצועי: ראשי פלדת S2 מוקשחת שלא נשחקים, עם מיסב מסתובב חלק ומגנט חזק לאלקטרוניקה וסמארטפונים!",
        "card_hook_i18n": {
            "he": "🔧 פירוק ותיקון מקצועי: ראשי פלדת S2 מוקשחת שלא נשחקים, עם מיסב מסתובב חלק ומגנט חזק לאלקטרוניקה וסמארטפונים!",
            "en": "🔧 Pro teardown kit: hardened S2 steel bits that never strip screw heads, with silky swivel cap for phone and laptop repair!",
            "ru": "🔧 Инструмент без слизанных винтов: закалённая сталь S2 твердостью 60HRC, плавный подшипник и мощный магнит для гаджетов!",
            "es": "🔧 Reparaciones de precisión: puntas de acero templado S2 que no desgastan los tornillos de móviles y portátiles.",
            "fr": "🔧 Kit de précision pro : embouts en acier trempé S2 inusables avec tête pivotante fluide pour smartphones.",
            "de": "🔧 Profi-Reparaturset: Gehärteter S2-Stahl verhindert Abrunden von Schrauben bei Smartphone- & Laptop-Reparaturen.",
            "ar": "🔧 طقم صيانة احترافي: رؤوس فولاذ S2 صلب لا يتآكل مع رأس دوار سلس ومغناطيس قوي لصيانة الهواتف والأجهزة!"
        },
        "highlights": [
            "פלדת כלי עבודה מסוג S2 שעברה טיפול בחום ברמת קשיות של 60HRC לעמידות של שנים",
            "ראשי מברג מדויקים במיוחד: Torx T2, Pentalobe 0.8 ל-iPhone, Phillips 1.5, Tri-Point Y0.6",
            "קצה מגנטי חזק המונע נפילה של ברגים זעירים לתוך לוח האם",
            "גוף אלומיניום קל עם טקסטורת אחיזה נגד החלקה ופקק עליון מסתובב 360°"
        ],
        "specs": {
            "חומר ראשי מברג": "פלדת S2 מוקשחת (קשיות 60±2 HRC)",
            "ידית": "אלומיניום תעופתי עם ציפוי אנודייז",
            "סוגי ביטים": "Torx, Pentalobe, Phillips, Tri-point, Standoff",
            "תאימות": "iPhone, MacBook, Apple Watch, Nintendo Switch, משקפיים"
        }
    },
    "real-110": {
        "choice_badge": "Choice",
        "card_hook": "💎 מציאה גאונית ב-$3: כבל טעינה 240W מחוזק עם מעמד מתקפל מובנה לצפייה בסרטונים בזמן שהטלפון נטען!",
        "card_hook_i18n": {
            "he": "💎 מציאה גאונית ב-$3: כבל טעינה 240W מחוזק עם מעמד מתקפל מובנה לצפייה בסרטונים בזמן שהטלפון נטען!",
            "en": "💎 Genius $3 find: indestructible 240W braided charging cable with a built-in foldable kickstand to watch movies while charging!",
            "ru": "💎 Находка за $3: сверхпрочный кабель 240 Вт со встроенной металлической подставкой для просмотра видео во время быстрой зарядки!",
            "es": "💎 Hallazgo genial por $3: cable reforzado 240W con soporte plegable integrado para ver vídeos mientras carga rápido.",
            "fr": "💎 Pépite à 3$ : câble blindé 240W avec béquille pliable intégrée pour regarder des vidéos pendant la charge ultra-rapide.",
            "de": "💎 Geniales 3$-Gadget: Unzerstörbares 240W Ladekabel mit integriertem ausklappbarem Ständer zum Videoschauen.",
            "ar": "💎 صفقة ذكية بـ 3$: كابل شحن 240 واط فائق القوة مع مسند مدمج لمشاهدة الفيديوهات أثناء الشحن السريع!"
        },
        "highlights": [
            "תומך בטעינת על בהספק עד 240W (48V/5A) עם שבב חכם E-Marker המגן על הסוללה",
            "רגלית מתכת מתקפלת מובנית בראש המחבר המאפשרת להעמיד את הטלפון לאורך או לרוחב",
            "סיכוך כפול ומעטפת ניילון קלועה צפופה שנבדקה בלמעלה מ-20,000 כיפופים",
            "תאימות רחבה לכל מכשירי USB-C כולל iPhone 15/16, מחשבי ניידים, טאבלטים וקונסולות"
        ],
        "specs": {
            "הספק מרבי": "240W Power Delivery (E-Marker Chip)",
            "מהירות העברת נתונים": "480Mbps USB 2.0",
            "חומרים": "סגסוגת אבץ + ניילון בליסטי קלוע",
            "אורך כבל": "1 מטר / 2 מטר"
        }
    },
    "real-111": {
        "choice_badge": "Choice",
        "card_hook": "💧 בריאות לחיות המחמד: מזרקת נירוסטה 304 שקטה לחלוטין עם סינון 6 שכבות שמעודדת שתיית מים נקיים ללא חיידקים!",
        "card_hook_i18n": {
            "he": "💧 בריאות לחיות המחמד: מזרקת נירוסטה 304 שקטה לחלוטין עם סינון 6 שכבות שמעודדת שתיית מים נקיים ללא חיידקים!",
            "en": "💧 Pet kidney health: whisper-quiet 304 stainless steel fountain with 6-layer filtration prevents bacteria & encourages daily drinking!",
            "ru": "💧 Здоровье почек питомца: бесшумный фонтанчик из пищевой стали 304 с 6-ступенчатой очисткой воды от шерсти и бактерий!",
            "es": "💧 Salud para tu mascota: fuente de acero inoxidable 304 ultra silenciosa con filtrado en 6 etapas para agua siempre fresca.",
            "fr": "💧 Santé et hydratation : fontaine en inox 304 ultra-silencieuse avec filtration 6 couches pour une eau pure sans bactéries.",
            "de": "💧 Gesundheit für Haustiere: Flüsterleiser 304-Edelstahl-Trinkbrunnen mit 6-Schicht-Filterung für keimfreies Wasser.",
            "ar": "💧 صحة ونقاء لحيوانك: نافورة من الفولاذ المقاوم للصدأ 304 فائقة الهدوء بنظام فلترة من 6 طبقات لمياه نقية دائماً!"
        },
        "highlights": [
            "נירוסטה רפואית 304 העמידה בפני שריטות והצטברות חיידקים (מונעת פצעי סנטר בחתולים)",
            "מערכת סינון רב-שכבתית מתקדמת הכוללת פחם פעיל, שרף חילוף יונים ורשת כותנה",
            "משאבת מים סופר-שקטה הפועלת בעוצמה של פחות מ-20dB (שקטה כמו נשימה)",
            "קל לפירוק ושטיפה מלאה במדיח כלים"
        ],
        "specs": {
            "קיבולת מיכל": "2.0 ליטר (מספיק ל-7-10 ימי שתייה לחתול בוגר)",
            "חומר": "נירוסטה 304 מאושרת למזון (Food-Grade)",
            "רמת רעש": "< 20dB (משאבה אילמת)",
            "מערכת סינון": "6 שכבות פחם פעיל + ספוג הגנה למשאבה"
        }
    },
    "real-112": {
        "choice_badge": "Choice",
        "card_hook": "🧲 יציבות מושלמת ב-$2: מגנט ניאודימיום עוצמתי שמחזיק כל טלפון יציב כסלע גם בפסי האטה ובכבישים משובשים!",
        "card_hook_i18n": {
            "he": "🧲 יציבות מושלמת ב-$2: מגנט ניאודימיום עוצמתי שמחזיק כל טלפון יציב כסלע גם בפסי האטה ובכבישים משובשים!",
            "en": "🧲 Rock-solid hold for $2: heavy-duty neodymium magnets keep any phone firmly in place even over speed bumps and sharp turns!",
            "ru": "🧲 Надежное крепление за $2: мощные неодимовые магниты удерживают смартфон намертво на любых ухабах и резких поворотах!",
            "es": "🧲 Sujeción firme por $2: imanes de neodimio de alta potencia que fijan el móvil incluso en baches y curvas cerradas.",
            "fr": "🧲 Fixation solide à 2$ : puissants aimants néodyme qui maintiennent fermement votre téléphone même sur route cahoteuse.",
            "de": "🧲 Bombenfester Halt für 2$: Starke Neodym-Magnete halten das Smartphone selbst bei Schlaglöchern und Vollbremsung sicher.",
            "ar": "🧲 ثبات قوي بـ 2$: مغناطيس نيوديميوم فائق القوة يثبت أي هاتف بإحكام تام حتى عند المطبات والمنعطفات الحادة!"
        },
        "highlights": [
            "טבעת של 6 מגנטי ניאודימיום N52 המייצרים אחיזה של עד 2.5 ק\"ג מבלי לשבש את הקליטה",
            "מפרק כדורי ממתכת המאפשר סיבוב של 360° וכיוון מדויק לזווית העיניים של הנהג",
            "דבק 3M VHB עמיד לחום המבטיח הדבקה חזקה לדשבורד שאינה מתנתקת בשמש הישראלית",
            "כולל שתי לוחיות מתכת דקות במיוחד להדבקה על גב הטלפון או הכיסוי"
        ],
        "specs": {
            "סוג מגנט": "6x Neodymium N52 Super Magnets",
            "חומר גוף": "סגסוגת אבץ מלוטשת בגימור יוקרתי",
            "הדבקה": "מדבקת 3M VHB מקורית עמידה בטמפרטורה עד 90°C",
            "זווית כוונון": "360° סיבוב מלא + הטיה לכל כיוון"
        }
    }
}

for p in db["products"]:
    pid = p["id"]
    if pid in ENRICHMENTS:
        enr = ENRICHMENTS[pid]
        p["choice_badge"] = enr.get("choice_badge", "Choice")
        p["card_hook"] = enr.get("card_hook", p.get("short_desc", ""))
        p["card_hook_i18n"] = enr.get("card_hook_i18n", {})
        p["highlights"] = enr.get("highlights", [])
        p["specs"] = enr.get("specs", {})

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("Enriched all 12 products with hooks, highlights, and specs successfully!")
