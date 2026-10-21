# -*- coding: utf-8 -*-
"""
Updates privacy.html, terms.html, disclosure.html, and contact.html to modern clean styling.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PAGES = {
    "privacy.html": {
        "title": "מדיניות פרטיות | DealVault",
        "desc": "מדיניות הפרטיות של אתר DealVault: איסוף נתונים אנונימי, עוגיות, אבטחת מידע וזכויות משתמש.",
        "h1": "מדיניות פרטיות (Privacy Policy)",
        "badge": "COMPLIANCE // LEGAL",
        "content": """
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;">עודכן לאחרונה: 2026 | תקף עבור אתר DealVault</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">1. מבוא וכללי</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">אתר DealVault (להלן: "האתר") מכבד את פרטיות המשתמשים בו. מסמך זה מפרט את מדיניות האתר בנוגע לאיסוף, שימוש, שמירה וגילוי של מידע המתקבל בעת הגלישה באתר, בהתאם לחוק הגנת הפרטיות, התשמ"א-1981, תקנות הגנת המידע הכלליות באיחוד האירופי (GDPR) והנחיות הרגולציה הבינלאומית.</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">2. המידע שאנו אוספים</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">האתר אינו דורש יצירת חשבון משתמש ואינו שומר מידע אישי מזהה (PII) כגון מספרי תעודת זהות או פרטי כרטיסי אשראי. המידע הנאסף הינו טכני ואנונימי בלבד (כתובת IP אנונימית לצורכי אבטחה, נתוני דפדפן וקליקים על קישורי שותפים).</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">3. עוגיות (Cookies) וטכנולוגיות מעקב</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">האתר עושה שימוש בקבצי Cookies מקומיים כדי לשמור את העדפות השפה, המטבע, והמסננים שבחרתם. כמו כן, קישורי שותפים (Affiliate Links) עשויים להפעיל Cookie של רשת השותפים של AliExpress במטרה לתעד את המעבר לאתר הסוחר ולהעניק עמלה לאתר במידה ובוצעה רכישה.</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">4. רכישות ואבטחת תשלומים</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">האתר אינו מבצע סליקת כספים ואינו מוכר מוצרים באופן ישיר. כל פעולת רכישה, תשלום, הזנת פרטי אשראי והזנת כתובת למשלוח מתבצעת באופן מאובטח ומלא ישירות באתר הסוחר החיצוני (AliExpress) תחת פרוטוקולי האבטחה וההצפנה של הסוחר.</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">5. יצירת קשר לבירורים</h2>
        <p style="color: var(--text-secondary); line-height: 1.7;">לכל שאלה בנושא פרטיות ואבטחת מידע ניתן לפנות אלינו דרך <a href="contact.html" style="color: var(--accent-cyan); text-decoration: underline;">עמוד יצירת קשר</a>.</p>
        """
    },
    "terms.html": {
        "title": "תנאי שימוש | DealVault",
        "desc": "תנאי השימוש באתר DealVault: זכויות יוצרים, הגבלת אחריות ותנאי הפניה לעסקאות צד שלישי.",
        "h1": "תנאי שימוש (Terms of Service)",
        "badge": "COMPLIANCE // TERMS",
        "content": """
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;">עודכן לאחרונה: 2026 | תקף עבור אתר DealVault</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">1. הסכמה לתנאים</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">הגלישה באתר DealVault והשימוש בשירותיו מהווים הסכמה מלאה ומפורשת לתנאי שימוש אלה. אם אינך מסכים לתנאים, הנך מתבקש לחדול מגלישה באתר.</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">2. אופי השירות וסקירות צד שלישי</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">DealVault הינו פורטל סקירות, המלצות ואוצרות תוכן עצמאי. האתר אינו חנות מקוונת, אינו מוכר מוצרים בעצמו ואינו מחזיק מלאי. כל הרכישות מבוצעות ישירות מול מוכרים עצמאיים באתר AliExpress.</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">3. מחירי מוצרים, משלוחים וזמינות</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">אנו עושים מאמצים לספק מידע מדויק אודות מחירים ומבצעים. עם זאת, המחיר הסופי, עלות המשלוח, זמינות המלאי ותנאי המכס נקבעים באופן בלעדי על ידי המוכר ב-AliExpress בעת ביצוע ההזמנה.</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">4. הגנת הקונה ואחריות</h2>
        <p style="color: var(--text-secondary); line-height: 1.7;">האחריות על טיב המוצרים, אספקה והחזרות כספיות חלה במלואה על המוכר באתר AliExpress ובהתאם למדיניות הרשמית של AliExpress Buyer Protection.</p>
        """
    },
    "disclosure.html": {
        "title": "גילוי נאות שותפים | DealVault",
        "desc": "גילוי נאות שותפים (FTC Affiliate Disclosure) של אתר DealVault בנוגע להשתתפות בתוכנית השותפים של AliExpress.",
        "h1": "גילוי נאות שותפים (Affiliate Disclosure)",
        "badge": "TRANSPARENCY // FTC",
        "content": """
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 20px;">בהתאם להנחיות נציבות הסחר הפדרלית (FTC) וכללי תוכנית השותפים AliExpress Portals</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">1. שקיפות מלאה מול הקוראים</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">אנו מאמינים בשקיפות מוחלטת מול קהילת הגולשים שלנו. אתר DealVault משתתף בתוכניות שותפים מקוונות, ובפרט בתוכנית השותפים הרשמית של AliExpress (AliExpress Portals Affiliate Program).</p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">2. כיצד פועלים קישורי שותפים?</h2>
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 14px;">הקישורים באתר המסומנים כקישורי רכישה ומבצע ("למעבר לדיל" / "Get Deal") הינם קישורי שותפים. משמעות הדבר היא שבמידה ותלחצו על הקישור ותבצעו רכישה באתר המוכר, ייתכן שנקבל עמלת הפניה צנועה מרשת השותפים. <b>אין לכך כל השפעה על המחיר שאתם משלמים — המחיר עבורכם זהה לחלוטין ולעיתים אף זול יותר בזכות קופונים בלעדיים!</b></p>
        <h2 style="font-size: 17px; color: #fff; margin: 24px 0 10px;">3. עצמאות בבחירת המוצרים</h2>
        <p style="color: var(--text-secondary); line-height: 1.7;">הבחירה להציג מוצר באתר מתבססת על דירוג קונים גבוה (4.8+), כמות הזמנות מאומתת ופתרון בעיות מעשי. עמלת השותפים מסייעת לנו לתחזק את השרתים ולסרוק מציאות איכותיות מדי יום.</p>
        """
    },
    "contact.html": {
        "title": "יצירת קשר ושירות לקוחות | DealVault",
        "desc": "צרו קשר עם צוות DealVault: פניות עסקיות, הצעות לגאדג'טים ושאלות שירות.",
        "h1": "יצירת קשר ושירות לקוחות (Contact)",
        "badge": "SUPPORT // INQUIRIES",
        "content": """
        <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 24px;">יש לכם הצעה לגאדג'ט מעניין שלא מופיע בקטלוג? שאלה בנוגע לדיל מסוים? או הצעה לשיתוף פעולה מסחרי? אנחנו כאן לרשותכם.</p>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 20px; display: grid; gap: 14px; margin-bottom: 24px;">
          <div style="display: flex; gap: 12px; align-items: center;">
            <span style="font-size: 24px;">✉</span>
            <div>
              <b style="color: #fff;">דואר אלקטרוני לפניות ושירות:</b>
              <div style="color: var(--accent-cyan); font-weight: 700; margin-top: 2px;">support@dealvault.pages.dev</div>
            </div>
          </div>
          <div style="display: flex; gap: 12px; align-items: center;">
            <span style="font-size: 24px;">⚡</span>
            <div>
              <b style="color: #fff;">זמן מענה ממוצע:</b>
              <div style="color: var(--text-muted); margin-top: 2px;">עד 24 שעות בימי עסקים</div>
            </div>
          </div>
        </div>
        <h2 style="font-size: 17px; color: #fff; margin: 20px 0 10px;">שאלות לגבי משלוחים והזמנות</h2>
        <p style="color: var(--text-secondary); line-height: 1.7;">שימו לב: מכיוון שאתר DealVault הינו אתר סקירות והמלצות עצמאי, אין לנו גישה ישירה לפרטי ההזמנות שלכם באתרי הסוחרים. בכל שאלה הנוגעת למספר מעקב של חבילה, עיכוב במשלוח או בקשת ביטול/החזרה — מומלץ לפנות ישירות לשירות הלקוחות של AliExpress או למוכר הספציפי דרך חשבונכם באתר הסוחר.</p>
        """
    }
}

for filename, info in PAGES.items():
    html_content = f'''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{info["title"]}</title>
  <meta name="description" content="{info["desc"]}">
  <meta name="theme-color" content="#0b0f19">
  <link rel="icon" href="assets/icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/modern.css?v=2026.2">
  <style>
    .legal-container {{ max-width: 820px; margin: 40px auto 80px; padding: 0 16px; }}
    .legal-card {{ background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 36px 30px; box-shadow: var(--shadow-card); }}
    .back-btn {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent-cyan); font-weight: 600; font-size: 13.5px; text-decoration: none; margin-bottom: 20px; }}
    .back-btn:hover {{ color: var(--accent-cyan-hover); text-decoration: underline; }}
  </style>
</head>
<body>

  <header class="modern-header">
    <div class="wrap">
      <div class="header-inner">
        <a href="index.html" class="brand-logo" aria-label="DealVault Home">
          <div class="brand-icon">⬡</div>
          <div>
            <div class="brand-text">Deal<span>Vault</span></div>
          </div>
        </a>
        <a href="index.html" class="back-btn" style="margin-bottom:0;">➔ חזרה לקטלוג הראשי</a>
      </div>
    </div>
  </header>

  <main class="legal-container">
    <a href="index.html" class="back-btn">➔ חזרה לקטלוג הראשי</a>
    <div class="legal-card">
      <span class="discount-badge" style="position:static;display:inline-block;margin-bottom:12px;background:rgba(6,182,212,0.15);color:var(--accent-cyan);border:1px solid rgba(6,182,212,0.3);box-shadow:none;">{info["badge"]}</span>
      <h1 style="font-size:24px;font-weight:900;color:#fff;margin-bottom:16px;">{info["h1"]}</h1>
      {info["content"]}
    </div>
  </main>

  <footer class="modern-footer">
    <div class="footer-inner">
      <nav class="footer-nav">
        <a href="privacy.html">מדיניות פרטיות</a>
        <span>•</span>
        <a href="terms.html">תנאי שימוש</a>
        <span>•</span>
        <a href="disclosure.html">גילוי נאות שותפים</a>
        <span>•</span>
        <a href="contact.html">יצירת קשר ושירות</a>
      </nav>
      <p>© 2026 DEALVAULT. ALL RIGHTS RESERVED.</p>
    </div>
  </footer>

</body>
</html>'''

    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Updated {filename} with modern clean UI.")

print("All legal documents updated successfully.")
