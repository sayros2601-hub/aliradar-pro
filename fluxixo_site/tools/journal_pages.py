"""Multilingual FLUXIXO buying guides restored and adapted for all six target markets."""
from __future__ import annotations

from html import escape as e

JOURNAL_UI = {
    'ru': {
        'slug_prefix': '/journal/',
        'eyebrow': 'Журнал FLUXIXO',
        'h1': 'Практические памятки перед покупкой на AliExpress',
        'intro': 'Короткие чек-листы по выбору техники, кабелей и аксессуаров без лишней рекламы: на что смотреть в карточке товара до оплаты.',
        'title': 'Памятки покупателя AliExpress: зарядки, кабели и цены | FLUXIXO',
        'desc': 'Практические чек-листы FLUXIXO: как сравнить итоговую цену с доставкой, проверить USB-C и подобрать органайзер проводов.',
        'catalog_cta': 'Открыть весь каталог',
        'home': 'Главная',
        'catalog': 'Каталог',
        'related_product_label': 'Смотреть подходящий товар в каталоге',
        'date': '2026-11-01',
    },
    'en': {
        'slug_prefix': '/en/journal/',
        'eyebrow': 'FLUXIXO Journal',
        'h1': 'Practical AliExpress buying checklists',
        'intro': 'Short, practical buyer checklists on comparing delivered totals, USB-C compatibility, and measuring desk space for cable organizers before you order.',
        'title': 'AliExpress Buying Checklists: USB-C, Prices & Desk Gear | FLUXIXO',
        'desc': 'Clean FLUXIXO buying guides on checking final checkout pricing, USB-C specs, and measuring desk cable organizers.',
        'catalog_cta': 'Browse the catalog',
        'home': 'Home',
        'catalog': 'Catalog',
        'related_product_label': 'Inspect related item in catalog',
        'date': '2026-11-01',
    },
    'pt': {
        'slug_prefix': '/pt/journal/',
        'eyebrow': 'Guia FLUXIXO',
        'h1': 'Guias práticos antes de comprar no AliExpress',
        'intro': 'Listas objetivas para comparar o valor total no checkout, conferir carregadores USB-C e medir organizadores de mesa antes do pedido.',
        'title': 'Guias de Compra AliExpress Brasil: USB-C e Preço Final | FLUXIXO',
        'desc': 'Guias FLUXIXO para o Brasil sobre cálculo do valor final com frete, carregadores USB-C e organização de cabos.',
        'catalog_cta': 'Explorar o catálogo',
        'home': 'Início',
        'catalog': 'Catálogo',
        'related_product_label': 'Ver item relacionado no catálogo',
        'date': '2026-11-01',
    },
    'es': {
        'slug_prefix': '/es/journal/',
        'eyebrow': 'Guía FLUXIXO',
        'h1': 'Guías prácticas antes de pedir en AliExpress',
        'intro': 'Listas claras para comparar el total al pagar, revisar cargadores USB-C y medir organizadores de escritorio antes de confirmar tu compra.',
        'title': 'Guías de Compra AliExpress México: USB-C y Precio Final | FLUXIXO',
        'desc': 'Guías prácticas FLUXIXO para México sobre total con envío, compatibilidad USB-C y orden de cables en el escritorio.',
        'catalog_cta': 'Ver todo el catálogo',
        'home': 'Inicio',
        'catalog': 'Catálogo',
        'related_product_label': 'Ver producto relacionado en el catálogo',
        'date': '2026-11-01',
    },
    'fr': {
        'slug_prefix': '/fr/journal/',
        'eyebrow': 'Guide FLUXIXO',
        'h1': 'Guides pratiques avant de commander sur AliExpress',
        'intro': 'Des listes concrètes pour comparer le total final au paiement, vérifier un chargeur USB-C et mesurer vos passe-câbles avant d’acheter.',
        'title': 'Guides d’Achat AliExpress : USB-C et Prix Final | FLUXIXO',
        'desc': 'Guides pratiques FLUXIXO sur le prix final livré, la compatibilité USB-C et le rangement des câbles de bureau.',
        'catalog_cta': 'Explorer le catalogue',
        'home': 'Accueil',
        'catalog': 'Catalogue',
        'related_product_label': 'Voir un produit associé dans le catalogue',
        'date': '2026-11-01',
    },
    'he': {
        'slug_prefix': '/he/journal/',
        'eyebrow': 'מדריך FLUXIXO',
        'h1': 'מדריכי קנייה מעשיים לפני הזמנה ב־AliExpress',
        'intro': 'רשימות בדיקה קצרות להשוואת סכום סופי בקופה, בדיקת מטען USB-C וארגון כבלים על שולחן העבודה לפני שמזמינים.',
        'title': 'מדריכי קנייה ל־AliExpress: USB-C ומחיר סופי | FLUXIXO',
        'desc': 'מדריכים מעשיים של FLUXIXO להשוואת מחיר כולל משלוח, בדיקת מטעני USB-C וארגון כבלים.',
        'catalog_cta': 'לכל הקטלוג',
        'home': 'ראשי',
        'catalog': 'קטלוג',
        'related_product_label': 'צפו במוצר מתאים בקטלוג',
        'date': '2026-11-01',
    },
}

ARTICLES = [
    {
        'slug': 'compare-the-final-price',
        'preferred_product': 'katord-wifi-repeater',
        'translations': {
            'ru': (
                'Почему цена в карточке и при оформлении отличается | FLUXIXO',
                'Как правильно сравнить итоговую стоимость товара и доставки на AliExpress в выбранной комплектации.',
                'Почему цена в карточке и при оформлении отличается',
                [
                    ('Начните с одинакового варианта', 'Сравнивайте одну модель, размер, цвет, количество и комплектацию. Низкая цена в заголовке часто относится к аксессуару или меньшему варианту. Откройте оба предложения и выберите одинаковую версию.'),
                    ('Считайте стоимость доставки', 'Укажите свою страну и одну валюту. Запишите стоимость товара, доставки и итог на странице оформления заказа. Оценка в списке и сумма на шаге оплаты могут отличаться.'),
                    ('Проверьте условия скидки', 'Купон продавца, первый заказ или минимальная сумма корзины влияют на расчёт. Не закладывайте скидку, которая не применяется к вашему аккаунту.'),
                    ('Короткая таблица сравнения', 'Фиксируйте вариант, количество, страну доставки, стоимость товара, доставки и итог к оплате. FLUXIXO не публикует актуальные цены и наличие: уточняйте условия у продавца.'),
                ],
            ),
            'en': (
                'Why the price changes between a listing and checkout | FLUXIXO',
                'How to compare exact SKU options, US shipping, and the delivered total on AliExpress before paying.',
                'Why the price changes between a listing and checkout',
                [
                    ('Start with the exact variant', 'A headline number is not enough to compare two listings. Match the exact model, size, color, quantity, and included accessories on both pages first.'),
                    ('Compare the delivered total', 'Set your actual US delivery address and currency before comparing. Record the item subtotal, shipping, and any checkout charges together.'),
                    ('Separate conditional discounts', 'Check whether an offer requires a new account coupon or minimum spend. Save your selected option so you can tell when an offer changes.'),
                    ('Use a simple comparison note', 'Write down variant, destination, item subtotal, shipping, and final total. FLUXIXO does not publish live pricing; confirm current terms directly on AliExpress.'),
                ],
            ),
            'pt': (
                'Por que o preço muda entre o anúncio e o pagamento | FLUXIXO',
                'Como comparar variações exatas, frete para o Brasil e valor total exibido no checkout do AliExpress.',
                'Por que o preço muda entre o anúncio e o pagamento',
                [
                    ('Compare a mesma variação', 'Anote modelo, tamanho, cor, quantidade e acessórios. Um valor inicial baixo pode ser apenas um cabo ou versão menor do produto.'),
                    ('Considere o total entregue no Brasil', 'Defina seu endereço no Brasil e a mesma moeda antes de comparar. Registre produto, frete e tributos mostrados diretamente no checkout do AliExpress.'),
                    ('Separe descontos condicionais', 'Verifique se um cupom exige valor mínimo ou conta nova. Só considere o desconto que aparece aplicado no seu carrinho.'),
                    ('Anotação rápida de comparação', 'Anote variação, frete, tributos e valor final. O catálogo FLUXIXO não publica preços em tempo real: confirme os valores atualizados com o vendedor.'),
                ],
            ),
            'es': (
                'Por qué cambia el precio entre el anuncio y el pago | FLUXIXO',
                'Cómo comparar la misma variante, el envío a México y el total final en el pago de AliExpress.',
                'Por qué cambia el precio entre el anuncio y el pago',
                [
                    ('Compara la misma variante', 'Anota modelo, tamaño, color, cantidad y accesorios incluidos. Un valor de entrada bajo puede corresponder a un accesorio o a una versión más pequeña.'),
                    ('Revisa el total con envío a México', 'Elige México como destino y mantén la misma moneda. Registra el artículo, el envío y los cargos mostrados en la pantalla final de pago.'),
                    ('Revisa condiciones de cupones', 'Comprueba si una rebaja exige cupón o compra mínima. Un ajuste que no aplica a tu carrito no cambia tu pago real.'),
                    ('Resumen por oferta', 'Anota variante, destino, envío y total final. FLUXIXO no publica precios en tiempo real: confirma el importe exacto con el vendedor antes de pagar.'),
                ],
            ),
            'fr': (
                'Pourquoi le prix change entre la fiche et le paiement | FLUXIXO',
                'Comment comparer la même déclinaison, la livraison vers la France et le montant final sur AliExpress.',
                'Pourquoi le prix change entre la fiche et le paiement',
                [
                    ('Comparez la même variante', 'Notez le modèle, la taille, la couleur, la quantité et les accessoires inclus. Le premier montant affiché correspond parfois à un simple accessoire.'),
                    ('Calculez le total livré en France', 'Réglez votre adresse en France et gardez une devise identique. Relevez le produit, la livraison et la TVA affichés à l’étape du paiement.'),
                    ('Vérifiez les conditions de remise', 'Regardez si la réduction demande un coupon ou un montant minimum de panier avant de comparer deux vendeurs.'),
                    ('Mémo de comparaison simple', 'Notez variante, destination, livraison et total final. FLUXIXO ne publie pas les prix en temps réel : vérifiez le montant chez le vendeur.'),
                ],
            ),
            'he': (
                'למה המחיר בקופה שונה מהמחיר בעמוד המוצר | FLUXIXO',
                'איך להשוות דגם זהה, משלוח לישראל ואת הסכום הסופי במסך התשלום של AliExpress לפני שמזמינים.',
                'למה המחיר בקופה שונה מהמחיר בעמוד המוצר',
                [
                    ('השוו את אותה גרסה', 'רשמו דגם, מידה, צבע, כמות ואביזרים כלולים. מחיר התחלתי נמוך מתייחס פעמים רבות לאביזר נפרד או לגרסה בסיסית יותר.'),
                    ('השוו את הסכום הסופי לישראל', 'הגדירו את ישראל כיעד המשלוח והישארו באותו מטבע. השוו את מחיר הפריט, המשלוח והתוספות במסך התשלום הסופי ולא רק בתוצאות החיפוש.'),
                    ('בדקו תנאי קופונים והנחות', 'ודאו אם ההנחה דורשת קופון או סכום מינימלי. התחשבו רק בהנחה שכבר מופיעה בחשבון שלכם.'),
                    ('רשימת בדיקה קצרה', 'תעדו דגם, יעד, משלוח וסכום סופי. FLUXIXO אינה מפרסמת מחירים בזמן אמת: בדקו את הסכום העדכני בעמוד המוצר ב־AliExpress.'),
                ],
            ),
        },
    },
    {
        'slug': 'usb-c-buying-checklist',
        'preferred_product': 'import-0010',
        'translations': {
            'ru': (
                'Перед покупкой USB-C: проверка зарядки и кабеля | FLUXIXO',
                'Чек-лист совместимости зарядок и кабелей USB Type-C, режимов питания и мощности на AliExpress.',
                'Перед покупкой USB-C: проверка зарядки и кабеля',
                [
                    ('Определите задачу', 'Зарядка телефона, питание ноутбука и передача данных требуют разных характеристик. Подходящий разъём Type-C сам по себе не гарантирует быструю зарядку или видеосигнал.'),
                    ('Прочитайте требования устройства', 'Сверьте паспортную мощность и поддерживаемый протокол USB PD с характеристиками выходов в описании зарядного устройства, а не только с цифрой в заголовке.'),
                    ('Отдельно проверьте кабель', 'Уточните допустимую мощность кабеля и длину от розетки до рабочего стола с учётом расстановки мебели.'),
                    ('Чек-лист перед заказом', 'Запишите модель устройства, нужную мощность (Вт), протоколы и распределение нагрузки при одновременном подключении перед заказом у продавца.'),
                ],
            ),
            'en': (
                'Before buying a USB-C charger: compatibility checklist | FLUXIXO',
                'Verify device USB PD profiles, port power sharing, and US Type A/B plug details on AliExpress.',
                'Before buying a USB-C charger: check the whole connection',
                [
                    ('Identify the job first', 'Charging a phone, powering a laptop, and sending video over USB Type-C rely on different specifications even though the connector shape looks the same.'),
                    ('Read your device requirements', 'Compare your laptop or phone power input specs against the stated USB PD output table in the listing instead of relying only on a headline wattage number.'),
                    ('Check the cable separately', 'Confirm that your USB-C cable handles the required wattage and measure the real distance from your US wall outlet to your desk.'),
                    ('Verify multi-port sharing', 'When several devices plug in at once, check how wattage splits across ports and verify the US plug option with the seller before checkout.'),
                ],
            ),
            'pt': (
                'Antes de comprar carregador USB-C: checklist completo | FLUXIXO',
                'Como conferir perfis USB PD, divisão entre portas, cabo e padrão de tomada no Brasil.',
                'Antes de comprar carregador USB-C: confira carregador, cabo e tomada',
                [
                    ('Defina o uso principal', 'Carregar celular, alimentar notebook ou transferir dados exige recursos distintos, mesmo com o mesmo conector USB Type-C.'),
                    ('Compare os requisitos do aparelho', 'Confira o manual do aparelho com as tabelas de saída USB PD informadas pelo vendedor, e não apenas o número total de watts do título.'),
                    ('Verifique o cabo separadamente', 'Confirme se o cabo suporta a potência desejada e meça a distância real até a tomada NBR 14136.'),
                    ('Cheque a divisão entre portas', 'Em modelos com várias saídas, observe como a energia é repartida no uso simultâneo e escolha o padrão de tomada correto.'),
                ],
            ),
            'es': (
                'Antes de comprar un cargador USB-C: guía práctica | FLUXIXO',
                'Revisa perfiles USB PD, reparto de potencia entre puertos, cable y clavija para México.',
                'Antes de comprar un cargador USB-C: revisa cargador, cable y clavija',
                [
                    ('Define para qué lo necesitas', 'Cargar un teléfono, alimentar una laptop o pasar datos rápidos requiere especificaciones distintas, aunque el conector USB Type-C encaje igual.'),
                    ('Lee los requisitos del equipo', 'Compara el manual de tu equipo con la tabla de voltajes USB PD que publica el vendedor y no te fíes solo de la cifra más grande del título.'),
                    ('Comprueba el cable aparte', 'Asegúrate de que el cable soporte la potencia necesaria y mide el recorrido real desde el enchufe Tipo A/B hasta tu mesa.'),
                    ('Revisa puertos simultáneos', 'Si conectas varios aparatos a la vez, verifica cómo se reparte la salida entre puertos antes de completar tu pedido.'),
                ],
            ),
            'fr': (
                'Avant d’acheter un chargeur USB-C : liste de contrôle | FLUXIXO',
                'Vérifiez les profils USB PD, le partage multi-ports, le câble et la prise européenne avant de commander.',
                'Avant d’acheter un chargeur USB-C : vérifiez chargeur, câble et prise',
                [
                    ('Définissez l’usage réel', 'Charger un téléphone, alimenter un ordinateur portable ou transférer des fichiers demande des caractéristiques précises malgré un port USB Type-C identique.'),
                    ('Lisez les besoins de l’appareil', 'Comparez la documentation de votre appareil aux tableaux de sortie USB PD annoncés par le vendeur plutôt qu’au seul chiffre du titre.'),
                    ('Contrôlez le câble à part', 'Vérifiez la puissance acceptée par le câble et mesurez la longueur réelle jusqu’à la prise murale 230V.'),
                    ('Vérifiez le partage multi-ports', 'En usage simultané sur plusieurs ports, consultez la répartition exacte de puissance et sélectionnez la prise européenne.'),
                ],
            ),
            'he': (
                'לפני רכישת מטען USB-C: רשימת בדיקה | FLUXIXO',
                'בדקו פרופילי טעינה USB PD, חלוקת הספק בין יציאות, כבל מתאים ותקע ישראלי ב־AliExpress.',
                'לפני שקונים מטען USB-C: מה חשוב לבדוק',
                [
                    ('הגדירו את הצורך', 'טעינת טלפון, הפעלת מחשב נייד והעברת נתונים דורשות מפרט שונה, למרות שמדובר באותו חיבור USB Type-C.'),
                    ('קראו את דרישות המכשיר', 'השוו בין נתוני היצרן של המכשיר לטבלת היציאות והתמיכה ב־USB PD בעמוד המוצר, במקום להסתמך רק על נתון ההספק הראשי בכותרת.'),
                    ('בדקו את הכבל בנפרד', 'ודאו שהכבל מתאים להספק הנדרש ומדדו את המרחק האמיתי מהשקע הישראלי עד לשולחן.'),
                    ('חלוקת הספק בין יציאות', 'במטען מרובה יציאות בדקו איך ההספק מתחלק כשמחברים כמה מכשירים יחד, ובחרו תקע תואם לפני ההזמנה.'),
                ],
            ),
        },
    },
    {
        'slug': 'desk-cable-management',
        'preferred_product': 'find-063-cable-tester',
        'translations': {
            'ru': (
                'Порядок в проводах: сначала измерьте, потом покупайте | FLUXIXO',
                'Как разметить провода, измерить столешницу и подобрать крепления для рабочего места без лишних деталей.',
                'Порядок в проводах: сначала измерьте, потом покупайте',
                [
                    ('Составьте схему проводов', 'Разделите устройства на постоянные и переносные. Проследите каждый провод от розетки до стола и уберите лишние кабели до заказа органайзеров.'),
                    ('Измерьте место крепления', 'Замерьте толщину столешницы, бортик, раму и глубину до стены. Для клеевых клипс проверьте совместимость с покрытием стола.'),
                    ('Оставьте запас движения', 'Предусмотрите свободный ход для перемещения ноутбука, поворота кресла и подъёма стола, держа провода подальше от тепла.'),
                    ('Решите конкретную задачу', 'Пара клипс нужного диаметра часто решает проблему лучше громоздкого лотка. Проверяйте внутренние размеры крепления в карточке продавца.'),
                ],
            ),
            'en': (
                'Tidy desk cables: measure first, buy fewer accessories | FLUXIXO',
                'Map active cables, measure desk edge thickness, and choose practical organizers before ordering.',
                'Tidy desk cables: measure first, buy fewer accessories',
                [
                    ('Map the cables you actually use', 'Separate fixed desk devices from portable gear. Trace each lead from the outlet and clear unused cables before picking organizers.'),
                    ('Measure the mounting points', 'Check desk top thickness, lip depth, and wall gap. Compare clamp openings against the actual desk frame rather than guessing from photos.'),
                    ('Leave room for movement', 'Allow slack for movable laptops, turning chairs, or height-adjustable desks while keeping power bricks ventilated.'),
                    ('Buy for the exact gap', 'A few properly sized clips often fix falling leads without an oversized tray. Verify interior measurements with the seller listing first.'),
                ],
            ),
            'pt': (
                'Organizar cabos da mesa: meça antes de comprar | FLUXIXO',
                'Mapeie os cabos reais, meça a espessura da mesa e evite acessórios incompatíveis.',
                'Organizar cabos da mesa: meça antes de comprar',
                [
                    ('Mapeie os cabos em uso', 'Separe equipamentos fixos dos portáteis que você retira com frequência e elimine fios sem uso antes de escolher suportes.'),
                    ('Meça o ponto de fixação', 'Confira a espessura do tampo, bordas e distância até a parede. Compare a abertura de garras e a compatibilidade do adesivo com a superfície.'),
                    ('Deixe folga para movimento', 'Garanta margem para mover notebook, cadeira e regulagem de altura sem esticar conectores nem bloquear ventilação.'),
                    ('Compre para o problema real', 'Clipes no tamanho certo costumam resolver cabos soltos melhor do que grandes bandejas. Confira medidas internas no anúncio do vendedor.'),
                ],
            ),
            'es': (
                'Ordena los cables del escritorio: mide antes de comprar | FLUXIXO',
                'Traza los cables reales, mide el grosor del tablero y elige sujetadores compatibles.',
                'Ordena los cables del escritorio: mide antes de comprar',
                [
                    ('Dibuja el recorrido real', 'Separa los aparatos fijos de los portátiles que desconectas a diario y retira cables sin uso antes de sumar accesorios.'),
                    ('Mide el montaje', 'Revisa el grosor del tablero, marcos metálicos y espacio inferior. Compara la apertura de pinzas y compatibilidad del adhesivo con tu escritorio.'),
                    ('Deja margen de movimiento', 'Mantén holgura suficiente para girar la silla, ajustar la altura o mover tu laptop sin tensar entradas ni tapar ventilación.'),
                    ('Elige justo lo necesario', 'Unos clips del diámetro correcto suelen bastar para sostener dos cables. Verifica las medidas interiores en la ficha del vendedor.'),
                ],
            ),
            'fr': (
                'Ranger les câbles de bureau : mesurer avant d’acheter | FLUXIXO',
                'Cartographiez vos câbles utiles, mesurez l’épaisseur du plateau et choisissez des fixations adaptées.',
                'Ranger les câbles de bureau : mesurer avant d’acheter',
                [
                    ('Cartographiez les câbles utilisés', 'Distinguez les appareils fixes des équipements déplacés chaque jour et retirez d’abord les câbles inutiles.'),
                    ('Mesurez les zones de fixation', 'Vérifiez l’épaisseur du plateau, le rebord et l’espace disponible au mur avant de choisir une pince ou un support adhésif.'),
                    ('Laissez du jeu de mouvement', 'Prévoyez assez de longueur pour le mouvement d’un écran, d’un ordinateur portable ou d’un bureau réglable sans bloquer l’aération.'),
                    ('Ciblez le besoin exact', 'Quelques clips bien dimensionnés suffisent souvent. Contrôlez toujours les cotes intérieures sur la fiche vendeur AliExpress.'),
                ],
            ),
            'he': (
                'סדר בכבלי השולחן: מודדים לפני שקונים | FLUXIXO',
                'מפו את הכבלים הקבועים, מדדו את עובי השולחן ובחרו פתרון ארגון מתאים לפני ההזמנה.',
                'סדר בכבלי השולחן: מודדים לפני שקונים',
                [
                    ('מפו את הכבלים שבשימוש', 'הפרידו בין מכשירים קבועים לציוד נייד ונתקו כבלים מיותרים עוד לפני רכישת אביזרי ארגון.'),
                    ('מדדו את מקום ההתקנה', 'בדקו את עובי פלטת השולחן, השפה התחתונה והמרחק מהקיר. השוו את מפתח הקליפס או התאמת הדבק לסוג המשטח שלכם.'),
                    ('השאירו חופש תנועה', 'השאירו אורך כבל מספק לתזוזת מחשב נייד, סיבוב כיסא ושולחן מתכוונן, ואל תחסמו פתחי אוורור.'),
                    ('פתרו בעיה ממוקדת', 'בשביל שני כבלים שנופלים מאחורי השולחן מספיקים לרוב כמה קליפסים מתאימים. בדקו מידות פנימיות מדויקות בעמוד המוצר ב־AliExpress.'),
                ],
            ),
        },
    },
]


def article_path(lang, slug):
    prefix = JOURNAL_UI[lang]['slug_prefix']
    return f'{prefix}{slug}/'


def index_path(lang):
    return JOURNAL_UI[lang]['slug_prefix']


def generate_journal_pages(origin, products, i18n_data, page_fn, write_fn, alternates_fn):
    """Render multilingual journal index and guide pages; returns generated route paths."""
    routes = []
    by_id = {p['id']: p for p in products}
    fallback_prod = products[0] if products else None
    index_alternates = {lang: index_path(lang) for lang in JOURNAL_UI}

    for lang, ui in JOURNAL_UI.items():
        prefix_ru = '' if lang == 'ru' else f'/{lang}'
        catalog_href = '/catalog/' if lang == 'ru' else f'/{lang}/'
        home_href = '/catalog/' if lang == 'ru' else f'/{lang}/'
        cards_html = []
        for article in ARTICLES:
            slug = article['slug']
            meta_title, meta_desc, h1, sections = article['translations'][lang]
            rel_prod = by_id.get(article['preferred_product']) or fallback_prod
            img_path = rel_prod['image'] if rel_prod else 'assets/images/import-0010.webp'
            thumb_rel = 'assets/thumbs/' + img_path.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '-480.webp'
            art_url = article_path(lang, slug)
            art_alternates = {l: article_path(l, slug) for l in JOURNAL_UI}
            routes.append(art_url)

            prod_href = f'{prefix_ru}/products/{rel_prod["id"]}/' if rel_prod else catalog_href
            if rel_prod:
                prod_name = (rel_prod['name'] if lang == 'ru'
                             else (i18n_data.get('products', {}).get(rel_prod['id'], {}).get(lang, {}) or {}).get('name', rel_prod['name']))
            else:
                prod_name = ui['catalog']

            sec_html = ''.join(f'<section><h2>{e(h2)}</h2><p>{e(body)}</p></section>' for h2, body in sections)
            crumbs = [(ui['home'], home_href), (ui['eyebrow'], index_path(lang)), (h1, art_url)]
            crumb_nav = (
                f'<nav class="breadcrumb"><a href="{home_href}">FLUXIXO</a>'
                f'<span class="breadcrumb-sep">/</span><a href="{index_path(lang)}">{e(ui["eyebrow"])}</a>'
                f'<span class="breadcrumb-sep">/</span><span>{e(h1)}</span></nav>'
            )
            art_schema = {
                '@context': 'https://schema.org',
                '@graph': [
                    {
                        '@type': 'Article',
                        'headline': h1,
                        'description': meta_desc,
                        'image': origin + '/' + img_path,
                        'datePublished': ui['date'],
                        'dateModified': ui['date'],
                        'inLanguage': lang,
                        'author': {'@type': 'Organization', 'name': 'FLUXIXO', 'url': origin + '/'},
                        'publisher': {'@type': 'Organization', 'name': 'FLUXIXO', 'url': origin + '/'},
                        'mainEntityOfPage': origin + art_url,
                    },
                    {
                        '@type': 'BreadcrumbList',
                        'itemListElement': [
                            {'@type': 'ListItem', 'position': idx + 1, 'name': label, 'item': origin + href}
                            for idx, (label, href) in enumerate(crumbs)
                        ],
                    },
                ],
            }
            colon = ' : ' if lang == 'fr' else ': '
            art_body = (
                f'{crumb_nav}'
                f'<article class="about-page journal-article">'
                f'<p class="eyebrow">{e(ui["eyebrow"])}</p>'
                f'<h1>{e(h1)}</h1>'
                f'<div class="cta-row"><a class="button secondary" href="{prod_href}">{e(ui["related_product_label"])}{colon}{e(prod_name)}</a>'
                f'<a class="button" href="{catalog_href}">{e(ui["catalog_cta"])}</a></div>'
                f'{sec_html}'
                f'</article>'
            )
            write_fn(
                art_url.strip('/') + '/index.html',
                page_fn(meta_title, meta_desc, art_url, art_body, schema=art_schema, image=img_path, language=lang, alternate_paths=art_alternates),
            )
            cards_html.append(
                f'<li><a class="card" href="{art_url}">'
                f'<div class="card-visual"><img src="/{e(thumb_rel)}" alt="{e(h1)}" width="400" height="300" loading="lazy"></div>'
                f'<p class="eyebrow">{e(ui["eyebrow"])}</p><h2>{e(h1)}</h2><p>{e(meta_desc)}</p></a></li>'
            )

        idx_url = index_path(lang)
        routes.append(idx_url)
        idx_schema = {
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            'name': ui['h1'],
            'description': ui['desc'],
            'url': origin + idx_url,
            'inLanguage': lang,
        }
        idx_body = (
            f'<p class="eyebrow">{e(ui["eyebrow"])}</p>'
            f'<h1>{e(ui["h1"])}</h1>'
            f'<p>{e(ui["intro"])}</p>'
            f'<ul class="grid">{"".join(cards_html)}</ul>'
            f'<p><a class="button secondary" href="{catalog_href}">{e(ui["catalog_cta"])}</a></p>'
        )
        write_fn(
            idx_url.strip('/') + '/index.html',
            page_fn(ui['title'], ui['desc'], idx_url, idx_body, schema=idx_schema, language=lang, alternate_paths=index_alternates),
        )
    return routes
