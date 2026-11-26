"""Multilingual FLUXIXO buying guides restored and adapted for all six target markets."""
from __future__ import annotations

import json
from html import escape as e
import comparison_guides
from pathlib import Path

# Guides that exist in Russian only (written for readers who come from Yandex). Each row:
# {"slug", "preferred_product", "title", "description", "h1", "sections": [[heading, paragraph], ...], "date"}.
EXTRA_RU_FILE = Path(__file__).resolve().parent / 'journal_ru_extra.json'
EXTRA_MULTILINGUAL_FILE = Path(__file__).resolve().parent / 'journal_multilingual_extra.json'
DIST = Path(__file__).resolve().parents[1] / 'dist'

JOURNAL_RELATED_HEADING = {
    'ru': 'Товары из каталога по этой теме',
    'en': 'Related finds in the catalog',
    'pt': 'Itens relacionados no catálogo',
    'es': 'Artículos relacionados en el catálogo',
    'fr': 'Articles associés dans le catalogue',
    'he': 'מוצרים קשורים בקטלוג',
}

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
        'intro': 'Practical checklists for choosing a Wi-Fi range extender, checking USB-C compatibility, organizing desk cables, and comparing prices with shipping.',
        'title': 'AliExpress Buying Guides for Wi-Fi, USB-C & More | FLUXIXO',
        'desc': 'Check Wi-Fi range extenders, USB-C chargers, and desk cable organizers, and compare the full price with shipping before you order.',
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
        'related_products': ('katord-wifi-repeater', 'import-0010', 'import-0051', 'find-059-label-printer'),
        'modified_dates': {'en': '2026-11-24'},
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
                    ('Учитывайте пошлины и налоги', 'В некоторых странах к посылкам из-за рубежа применяются пошлины или налог сверх беспошлинного порога. На шаге оформления AliExpress обычно показывает такие начисления отдельной строкой. Если строки нет, уточните правила своей страны заранее: доплата при получении меняет итог сильнее, чем разница в цене между двумя продавцами.'),
                    ('Сравнивайте способ и срок доставки', 'Дешёвый способ доставки часто идёт дольше и хуже отслеживается. Посмотрите, какой перевозчик указан, есть ли трек-номер на всём пути и до какой даты продавец обещает доставку. Иногда разумнее немного доплатить за отслеживаемую посылку, особенно если вещь нужна к определённому дню.'),
                    ('Не забудьте про возврат', 'Перед оплатой откройте условия возврата у конкретного продавца: кто оплачивает обратную пересылку и в какой срок можно открыть спор. У двух одинаковых по цене предложений условия бывают разными, и это тоже часть итоговой стоимости покупки.'),
                ],
            ),
            'en': (
                'Why the price changes between a listing and checkout | FLUXIXO',
                'Compare the exact AliExpress SKU variant, US shipping fees, taxes, and conditional coupons before placing an order.',
                'Why the price changes between a listing and checkout',
                [
                    ('Match the exact SKU variant first', 'A low headline figure on search cards frequently points to a spare nozzle, empty case, or bare tool without a battery. Open both listings, click the identical model, size, US plug type, and accessory bundle, and compare only after the option thumbnails match.'),
                    ('Compare the full delivered US total', 'Set your United States ZIP code and keep both tabs in USD. A listing with a slightly higher item price and free tracked shipping often beats a rock-bottom listing that adds steep shipping per unit at checkout.'),
                    ('Separate one-time or conditional coupons', 'New-shopper welcome deals, store follower coupons, and minimum-cart thresholds can distort search previews. Only count discounts that remain active on the final checkout summary screen in your own account.'),
                    ('Account for state sales tax and customs rules', 'AliExpress calculates applicable US state sales tax at the final payment step. Reviewing the itemized subtotal, shipping line, and tax line side by side prevents checkout surprises.'),
                    ('Check carrier tracking and delivery promises', 'Ultra-economy shipping tiers may lack end-to-end USPS handoff tracking. Check whether the selected shipping method includes full tracking milestones and an on-time delivery guarantee.'),
                    ('Verify return terms before paying', 'Two identically priced sellers can offer very different return policies. Check whether free local return applies to the specific SKU you selected; FLUXIXO never publishes live prices, so always confirm current checkout terms on AliExpress.'),
                ],
            ),
            'pt': (
                'Por que o preço muda entre o anúncio e o pagamento | FLUXIXO',
                'Como comparar a variação exata, o frete para o Brasil, os tributos no carrinho e os cupons no AliExpress.',
                'Por que o preço muda entre o anúncio e o pagamento',
                [
                    ('Selecione exatamente a mesma variação', 'O menor valor exibido na busca quase sempre corresponde a um cabo avulso, refil ou versão menor. Abra os dois anúncios e clique no mesmo modelo, cor, voltagem ou plugue NBR 14136 antes de comparar.'),
                    ('Some produto, frete e impostos no Brasil', 'Informe seu CEP brasileiro e mantenha tudo em reais (BRL). Compare sempre a tela final do checkout, onde aparecem somados o item, o frete e os tributos de importação calculados diretamente no carrinho.'),
                    ('Desconte apenas cupons realmente aplicados', 'Ofertas de primeira compra, moedas e cupons de loja com gasto mínimo mudam o valor anunciado na vitrine. Considere apenas o abatimento que continua visível no resumo final da sua conta.'),
                    ('Atenção ao aumento de frete por quantidade', 'Ao pedir duas ou três unidades de um organizador ou refil, alguns vendedores multiplicam o frete por peça. Teste a quantidade exata no carrinho antes de decidir qual anúncio compensa mais.'),
                    ('Compare rastreamento e prazo estimado', 'Modalidades econômicas sem rastreio passo a passo demoram mais na triagem. Prefira envios com código rastreável completo até a entrega no seu endereço.'),
                    ('Confira regras de devolução antes de fechar', 'Verifique na página do vendedor como funciona a devolução e a garantia do comprador para aquela variação específica; o catálogo FLUXIXO não exibe preços fixos em tempo real.'),
                ],
            ),
            'es': (
                'Por qué cambia el precio entre el anuncio y el pago | FLUXIXO',
                'Cómo comparar la misma variante, el envío a México, cargos de importación y cupones reales al pagar en AliExpress.',
                'Por qué cambia el precio entre el anuncio y el pago',
                [
                    ('Empieza marcando la misma variante exacta', 'El importe más bajo del título suele pertenecer a una funda vacía, un repuesto suelto o un modelo sin batería. Entra a ambas publicaciones y selecciona idéntico tamaño, clavija tipo A/B y accesorios antes de comparar.'),
                    ('Calcula el total puesto en México', 'Configura tu código postal en México y usa pesos mexicanos (MXN) en ambas pestañas. Un artículo con envío incluido suele resultar más conveniente que otro aparentemente barato que suma envío alto al pasar a caja.'),
                    ('Distingue descuentos exclusivos o con mínimo', 'Los precios de bienvenida para cuentas nuevas o cupones por monto mínimo no siempre aplican a tu carrito actual. Fíjate únicamente en el descuento que permanece activo en el resumen final de pago.'),
                    ('Revisa impuestos y cargos mostrados al pagar', 'En envíos internacionales hacia México, la pantalla de pago desglosa cargos aplicables o impuestos según el monto y la mensajería. Revisar esa línea antes de pagar evita diferencias inesperadas.'),
                    ('Compara guía rastreable y fecha promesa', 'Un envío estándar con rastreo puerta a puerta suele compensar frente al correo económico sin seguimiento detallado, sobre todo en herramientas o electrónica.'),
                    ('Confirma políticas de devolución del vendedor', 'Revisa las condiciones de devolución y protección al comprador en la ficha seleccionada; FLUXIXO no publica precios en vivo, así que confirma siempre el importe final en AliExpress.'),
                ],
            ),
            'fr': (
                'Pourquoi le prix change entre la fiche et le paiement | FLUXIXO',
                'Comparer la même déclinaison, les frais de port vers la France, la TVA et les remises réelles sur AliExpress.',
                'Pourquoi le prix change entre la fiche et le paiement',
                [
                    ('Sélectionnez d’abord la même déclinaison', 'Le tarif d’appel affiché dans les résultats correspond souvent à un embout seul, une housse vide ou une prise étrangère. Ouvrez chaque fiche et cochez exactement le même modèle, la prise européenne 230V et le même lot d’accessoires.'),
                    ('Comparez le montant total livré en France', 'Renseignez votre adresse en France et conservez l’affichage en euros. Additionnez le sous-total de l’article, les frais d’expédition et la TVA directement sur l’écran final de validation.'),
                    ('Écartez les remises réservées aux nouveaux comptes', 'Les offres de bienvenue ou coupons soumis à un minimum d’achat abaissent artificiellement l’aperçu en liste. Ne retenez que les réductions réellement déduites dans votre propre panier.'),
                    ('Surveillez les frais de port sur les achats multiples', 'Lorsque vous ajoutez deux ou trois exemplaires d’un petit accessoire, certains vendeurs facturent l’envoi à l’unité. Vérifiez toujours le total après avoir réglé la quantité finale.'),
                    ('Contrôlez le suivi du colis et le délai annoncé', 'Un mode d’expédition suivi de bout en bout jusqu’en boîte aux lettres ou point relais évite bien des incertitudes par rapport à un envoi économique non tracé.'),
                    ('Lisez les modalités de retour avant règlement', 'D’un vendeur à l’autre, la prise en charge du retour et le délai de réclamation varient ; FLUXIXO n’affiche aucun prix figé, vérifiez toujours le panier en direct sur AliExpress.'),
                ],
            ),
            'he': (
                'למה המחיר בקופה שונה מהמחיר בעמוד המוצר | FLUXIXO',
                'איך להשוות את אותו וריאנט בדיוק, דמי משלוח לישראל, קופונים ומדיניות החזרה לפני שמאשרים הזמנה ב־AliExpress.',
                'למה המחיר בקופה שונה מהמחיר בעמוד המוצר',
                [
                    ('התחילו מבחירת אותו וריאנט בדיוק', 'המחיר הנמוך שמופיע בתוצאות החיפוש שייך לעיתים קרובות לראש חילוף בלבד, נרתיק ריק או דגם ללא סוללה. פתחו את שני העמודים ובחרו בדיוק את אותו דגם, תקע מתאים לישראל ותכולת ערכה זהה.'),
                    ('השוו את הסכום הסופי כולל משלוח לישראל', 'הגדירו את ישראל כיעד המשלוח והציגו את המחירים באותו מטבע. השוו את השורה התחתונה במסך התשלום, משום שמוצר זול עם משלוח יקר עלול לעלות יותר ממוצר מקביל עם משלוח חינם.'),
                    ('הפרידו בין קופונים מותנים להנחה אמיתית', 'הנחת משתמש חדש או קופון שמותנה בסכום קנייה מינימלי לא תמיד חלים על החשבון שלכם. הסתמכו רק על הנחה שמופיעה בפועל בסיכום הקופה.'),
                    ('קחו בחשבון רף מע״מ ומשלוח על מספר יחידות', 'בהזמנות מחו״ל לישראל שימו לב לסף הפטור ממע״מ ולכך שהוספת יחידה שנייה לעגלה עלולה להקפיץ את דמי המשלוח או לחצות את רף המס.'),
                    ('בדקו מספר מעקב מלא וזמן אספקה', 'משלוח עם מעקב רציף ונקודת איסוף מסודרת עדיף כמעט תמיד על דואר איטי ללא עדכוני סריקה בארץ.'),
                    ('אמתו תנאי החזרה והגנת קונה לפני התשלום', 'גם כששני מוכרים מציעים מחיר דומה, תנאי ההחזרה עשויים להיות שונים; באתר FLUXIXO לא מופיעים מחירים בזמן אמת, לכן בדקו תמיד את הסכום העדכני ב־AliExpress.'),
                ],
            ),
        },
    },
    {
        'slug': 'usb-c-buying-checklist',
        'preferred_product': 'import-0010',
        'related_products': ('import-0010', 'import-0051', 'import-0488', 'find-054-soldering-iron', 'find-006-phone-cooler'),
        'modified_dates': {'en': '2026-11-24'},
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
                    ('Как делится мощность между портами', 'У зарядных устройств с несколькими портами заявленная мощность обычно относится к одному занятому порту. При подключении второго устройства она делится, и ноутбук может заряжаться медленнее. В описании продавца ищите таблицу режимов: сколько ватт выдаёт каждый порт в одиночку и при одновременной работе.'),
                    ('Кабель для данных и видео', 'Кабели Type-C внешне одинаковы, но различаются скоростью передачи данных и поддержкой видеосигнала. Простой зарядный кабель может не вывести картинку на монитор и медленно копировать файлы. Если нужен не только заряд, ищите в характеристиках скорость передачи и явное упоминание вывода изображения.'),
                    ('Вилка и безопасность', 'Проверьте тип вилки под свои розетки и диапазон входного напряжения. Зарядное устройство без понятной маркировки и защиты от перегрева лучше обойти стороной, даже если цифры в заголовке выглядят привлекательно. Отзывы с фотографиями помогают понять, как блок ведёт себя при длительной нагрузке.'),
                ],
            ),
            'en': (
                'Before buying a USB-C charger: compatibility checklist | FLUXIXO',
                'Verify USB Power Delivery wattage per port, multi-port power sharing, 100W E-Marker cables, video support, and US plugs.',
                'Before buying a USB-C charger: check the whole connection',
                [
                    ('Separate charging, high-speed data, and video', 'Every USB Type-C plug shares the same oval shell, yet charging a phone at 20W, powering an ultrabook at 65W–100W, and driving a 4K external monitor over DisplayPort Alt Mode require completely different internal wiring and chips.'),
                    ('Read the single-port USB PD voltage table', 'Ignore combined wattage headlines like "120W total" until you inspect the per-port output chart. A laptop requiring 20V at 3.25A (65W USB PD) will charge slowly or refuse power if the charger caps each individual port at 30W.'),
                    ('Check how wattage splits when multiple ports are active', 'Multi-port GaN desktop stations dynamically renegotiate power whenever a second cable plugs in—often dropping the primary laptop port from 65W down to 45W plus 18W. Match the simultaneous output diagram to your daily desk setup.'),
                    ('Match the USB-C cable rating and length', 'Any charge above 60W (3A) requires a 100W or 240W USB-C cable with an internal E-Marker chip; pairing a 100W charger with a basic 60W cord caps output at 60W. Measure the full path from your wall outlet to your desk edge before picking 3 ft vs. 6.6 ft cords.'),
                    ('Verify data speed and HDMI/video pass-through', 'Most affordable braided charging cords only wire USB 2.0 pins (480 Mbps) and cannot carry video to a portable screen or USB-C hub. Look explicitly for 10 Gbps / 20 Gbps ratings and 4K60 video support when connecting hubs or monitors.'),
                    ('Confirm folding or fixed US Type A/B prongs', 'On international AliExpress listings, verify you selected the US plug option rated for 100–240V AC so heavy GaN bricks sit flush in American wall receptacles without wobbly travel adapters.'),
                ],
            ),
            'pt': (
                'Antes de comprar carregador USB-C: checklist completo | FLUXIXO',
                'Como conferir perfis USB PD por porta, divisão de watts, cabos 100W, vídeo e tomada NBR 14136 no Brasil.',
                'Antes de comprar carregador USB-C: confira carregador, cabo e tomada',
                [
                    ('Diferencie recarga, dados rápidos e saída de vídeo', 'O conector USB Type-C tem sempre o mesmo formato oval, mas carregar um celular, alimentar um notebook em 65W e transmitir imagem HDMI por um hub exigem protocolos distintos na fonte, no cabo e no aparelho.'),
                    ('Leia a tabela real de saída USB PD de cada porta', 'Não olhe apenas o número somado do título: confira na tabela técnica do anúncio se a porta principal entrega 20V e 65W ou 100W sozinha para sustentar seu notebook em uso pesado.'),
                    ('Entenda a divisão de potência no uso simultâneo', 'Em estações de mesa com três ou quatro saídas, conectar um segundo aparelho redistribui os watts (por exemplo, 45W + 20W) e causa uma breve reconexão. Veja o diagrama de portas combinadas antes de fechar o pedido.'),
                    ('Escolha um cabo compatível com a potência e a distância', 'Acima de 60W é indispensável usar cabo USB-C de 100W ou 240W com chip identificador interno, senão a recarga trava em 60W. Meça o caminho real da tomada até a bancada antes de escolher 1 m ou 2 m.'),
                    ('Atenção a cabos só de carga se você usa hub ou monitor', 'Cabos focados apenas em carregamento operam em USB 2.0 (480 Mbps) e não transmitem sinal de vídeo para monitores nem SSDs externos rápidos. Procure menção explícita a 10 Gbps e suporte a vídeo 4K.'),
                    ('Confirme entrada bivolt 100–240V e plugue brasileiro', 'Prefira carregadores bivolt com pinos compatíveis com a tomada brasileira NBR 14136 ou cabo de força removível, evitando adaptadores frouxos que esquentam na parede.'),
                ],
            ),
            'es': (
                'Antes de comprar un cargador USB-C: guía práctica | FLUXIXO',
                'Revisa tablas USB PD por puerto, reparto simultáneo, cables de 100W, video y clavija tipo A/B para México.',
                'Antes de comprar un cargador USB-C: revisa cargador, cable y clavija',
                [
                    ('Separa carga rápida, transferencia de archivos y video', 'Aunque todas las puntas USB Type-C lucen iguales, cargar tu celular, alimentar una laptop de 65W o sacar imagen hacia un monitor mediante un hub requiere especificaciones internas distintas.'),
                    ('Consulta la tabla USB PD de un solo puerto', 'Más allá del número total anunciado en grande, busca en la descripción cuántos volts y watts reales entrega el puerto principal por sí solo (como 20V a 3.25A para 65W en laptops).'),
                    ('Verifica cómo se reparten los watts al conectar varios equipos', 'En estaciones multipuerto, enchufar un segundo teléfono suele dividir la salida principal (por ejemplo, bajando de 65W a 45W + 18W). Revisa el esquema de uso simultáneo para evitar cargas lentas.'),
                    ('Empareja un cable certificado de 100W y mide el tramo', 'Para superar los 60W necesitas un cable USB-C de 100W o 240W con chip interno; un cable básico limitará cualquier cargador potente. Mide el recorrido desde el contacto hasta tu escritorio antes de pedir 1 m o 2 m.'),
                    ('Comprueba soporte de datos y video si usas hubs', 'La mayoría de los cables económicos de carga solo transfieren a 480 Mbps y no envían video a pantallas externas. Si conectas discos rápidos o monitores, exige especificación de 10 Gbps y salida de video.'),
                    ('Asegura clavija americana tipo A/B y rango 100–240V', 'En AliExpress selecciona siempre la variante US/MX con patas planas tipo A o B para que el cargador encaje firme en los contactos de México sin usar adaptadores sueltos.'),
                ],
            ),
            'fr': (
                'Avant d’acheter un chargeur USB-C : liste de contrôle | FLUXIXO',
                'Vérifiez la table USB PD par port, le partage multi-ports, le câble 100 W, la vidéo et la prise européenne 230V.',
                'Avant d’acheter un chargeur USB-C : vérifiez chargeur, câble et prise',
                [
                    ('Distinguez charge rapide, transfert rapide et flux vidéo', 'La prise USB Type-C a beau être identique partout, recharger un smartphone, alimenter un ordinateur portable en 65 W et envoyer un signal HDMI 4K reposent sur des contrôleurs et des câbles bien différents.'),
                    ('Lisez le tableau de sortie USB PD port par port', 'Ne vous arrêtez pas au total cumulé du titre : vérifiez sur le schéma technique du vendeur qu’au moins un port délivre réellement 20 V et 65 W ou 100 W en solo pour votre ordinateur.'),
                    ('Anticipez le partage de puissance en usage simultané', 'Sur un bloc multi-ports GaN, brancher un second appareil redistribue la puissance disponible (par exemple 45 W + 20 W). Contrôlez les combinaisons annoncées lorsque plusieurs appareils chargent ensemble.'),
                    ('Associez un câble 100 W à puce interne à la bonne longueur', 'Au-delà de 60 W, un câble USB-C certifié 100 W ou 240 W est indispensable pour ne pas brider le chargeur. Mesurez le trajet réel entre la prise murale 230V et le bureau avant de choisir 1 m ou 2 m.'),
                    ('Vérifiez le débit de données et le mode vidéo', 'Un cordon de charge standard plafonne souvent à l’USB 2.0 (480 Mbps) et ne transmet aucune image vers un écran externe. Pour un hub ou un SSD rapide, cherchez explicitement 10 Gbps et la compatibilité vidéo.'),
                    ('Choisissez impérativement la prise européenne', 'Cochez la déclinaison prise EU (Type C ou E/F, 100–240V) sur la fiche AliExpress afin que le chargeur tienne droit dans vos prises murales sans adaptateur branlant.'),
                ],
            ),
            'he': (
                'לפני רכישת מטען USB-C: רשימת בדיקה | FLUXIXO',
                'בדקו טבלת הספק USB PD לכל יציאה, חלוקת עומס, כבל 100W, העברת וידאו ותקע מתאים לישראל לפני הזמנה ב־AliExpress.',
                'לפני שקונים מטען USB-C: מה חשוב לבדוק',
                [
                    ('הבדילו בין טעינה, העברת קבצים מהירה ויציאת מסך', 'כל מחברי USB Type-C נראים זהים מבחוץ, אך טעינת טלפון, הפעלת מחשב נייד בהספק 65W–100W והוצאת תמונת 4K למסך דרך מפצל דורשים תמיכה שונה במטען, בכבל ובמכשיר.'),
                    ('קראו את טבלת ה־USB PD של כל יציאה בנפרד', 'אל תסתפקו במספר הכולל בכותרת כמו 120W: חפשו במפרט הטכני כמה וואט מפיקה היציאה הראשית לבדה (למשל 20V ו־65W) מול דרישת המחשב שלכם.'),
                    ('בדקו איך מתחלק ההספק כשמחברים כמה מכשירים יחד', 'בתחנות טעינה מרובות יציאות, חיבור טלפון נוסף מפצל את ההספק (למשל מ־65W ל־45W ועוד 18W) ולעיתים מאט טעינת מחשב נייד בזמן עבודה. השוו את תרשים החלוקה לצרכים בשולחן שלכם.'),
                    ('התאימו כבל 100W ומדדו את המרחק מהשקע', 'לטעינה מעל 60W חובה להשתמש בכבל USB-C התומך ב־100W או 240W עם שבב זיהוי פנימי, אחרת קצב הטעינה יוגבל ל־60W. מדדו מראש את המסלול מהשקע בקיר עד לשולחן.'),
                    ('שימו לב ליכולת העברת נתונים ווידאו', 'כבלי טעינה בסיסיים תומכים לרוב במהירות USB 2.0 איטית ואינם מעבירים אות תמונה למסך חיצוני. לעבודה עם כונן מהיר או מפצל HDMI חפשו ציון מפורש של 10 גיגה־ביט לשנייה ותמיכה בווידאו.'),
                    ('בחרו תקע אירופאי או ישראלי תואם 230V', 'בעמוד המוכר הקפידו לסמן גרסת EU המתאימה לשקעים בישראל (220–230V) כדי להימנע ממתאמים רופפים שמתחממים או נופלים מהקיר.'),
                ],
            ),
        },
    },
    {
        'slug': 'desk-cable-management',
        'preferred_product': 'import-0451',
        'related_products': ('import-0451', 'import-0010', 'import-0051', 'import-0499', 'find-063-cable-tester', 'find-059-label-printer'),
        'image': 'assets/journal/desk-cable-routing.png',
        'modified': '2026-11-24',
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
                    ('Подберите длину кабелей', 'Слишком длинный провод приходится сматывать, слишком короткий натягивается и выдёргивается из разъёма. Измерьте путь от устройства до розетки по той траектории, по которой кабель действительно пойдёт: вдоль ножки стола, под столешницей, вдоль стены. К полученной длине добавьте небольшой запас.'),
                    ('Разведите питание и сигнал', 'Сетевой фильтр удобнее закрепить под столешницей или на задней стенке тумбы, чтобы блоки питания не лежали на полу. Тонкие сигнальные кабели уложите отдельной линией: так проще заменить один провод, не разбирая всю связку. Не перегибайте кабели под острым углом у самого разъёма.'),
                    ('Подпишите концы проводов', 'Небольшие бирки или цветные стяжки на обоих концах кабеля экономят время, когда нужно отключить одно устройство. Многоразовые стяжки на липучке удобнее одноразовых пластиковых: связку легко раскрыть и добавить новый провод, ничего не срезая.'),
                ],
            ),
            'en': (
                'Tidy desk cables: measure first, buy fewer accessories | FLUXIXO',
                'Map fixed vs. daily-carry cords, measure desk edge thickness, keep power bricks cool, and label cables cleanly.',
                'Tidy desk cables: measure first, buy fewer accessories',
                [
                    ('Separate permanent desk gear from daily-carry cords', 'Monitor power leads, lamp bars, and Ethernet cables stay routed under the desk year-round, while laptop chargers and phone cords move every day. Group only fixed cables into under-desk trays so you never tug a bundle loose when packing your bag.'),
                    ('Measure tabletop thickness, apron rails, and wall clearance', 'Before ordering clamp-on cable trays or monitor light mounts, measure your desktop thickness in millimeters or inches, check whether a metal support rail runs right behind the rear edge, and confirm gap clearance against the wall.'),
                    ('Leave safe slack for sit-stand desks and monitor arms', 'Height-adjustable desks and swivel arms pull cables taut at full extension. Raise your desk to its highest preset while test-routing power cords so nothing yanks on USB-C or HDMI ports.'),
                    ('Ventilate power bricks and separate AC from signal lines', 'Mount your surge strip and GaN charging station where air circulates freely rather than stuffing warm bricks inside sealed boxes, and keep thick AC cords slightly apart from audio leads.'),
                    ('Match adhesive clips to surface finish and cord diameter', 'Acrylic pads bond well to smooth laminate, glass, or painted metal, but peel off raw particleboard undersides or textured wood. Check the clip slot diameter in millimeters against braided HDMI vs. slim USB-C cords.'),
                    ('Label both ends with reusable hook-and-loop ties', 'Pocket thermal labels wrapped near both plugs save guesswork behind a power strip, and soft hook-and-loop straps let you swap a single monitor cable later without cutting zip ties.'),
                ],
            ),
            'pt': (
                'Organizar cabos da mesa: meça antes de comprar | FLUXIXO',
                'Separe fios fixos dos portáteis, meça a espessura do tampo, ventile fontes e identifique cada ponta antes de pedir.',
                'Organizar cabos da mesa: meça antes de comprar',
                [
                    ('Separe fios permanentes dos cabos que saem na mochila', 'Cabos de monitor, luminária de tela e filtro de linha ficam fixos o ano todo, enquanto carregadores de celular e notebook entram e saem diariamente. Prenda na calha inferior apenas a fiação permanente.'),
                    ('Meça a espessura do tampo, travessas e recuo da parede', 'Antes de escolher suportes de garra ou bandejas suspensas, meça a espessura da mesa em milímetros, veja se há estrutura metálica logo abaixo da borda traseira e confira o espaço livre até a parede.'),
                    ('Garanta folga para mesas com regulagem e braços articulados', 'Em mesas com ajuste de altura ou suporte articulado de monitor, teste o alcance na posição mais alta para que nenhum conector USB-C ou HDMI fique esticado.'),
                    ('Mantenha fontes ventiladas longe do piso', 'Fixar o filtro de linha sob o tampo facilita varrer o chão e protege contra poeira, mas deixe circulação de ar ao redor das fontes de notebook e estações de carga.'),
                    ('Confira a superfície antes de usar clipes adesivos', 'Fitas acrílicas aderem bem em vidro, metal e MDF liso, porém soltam em madeira porosa ou parte inferior áspera. Cheque também o diâmetro interno do clipe para cabos HDMI trançados mais grossos.'),
                    ('Identifique as duas pontas com etiquetas e fitas de velcro', 'Etiquetas térmicas perto dos plugues evitam desligar o aparelho errado na régua, e abraçadeiras reutilizáveis de velcro permitem trocar um fio sem usar tesoura.'),
                ],
            ),
            'es': (
                'Ordena los cables del escritorio: mide antes de comprar | FLUXIXO',
                'Separa cables fijos y portátiles, mide el grosor del escritorio, ventila eliminadores y etiqueta cada punta con orden.',
                'Ordena los cables del escritorio: mide antes de comprar',
                [
                    ('Divide el cableado fijo de los cargadores diarios', 'Los cables del monitor, la barra LED y el regulador pueden quedar ocultos bajo la cubierta, mientras que el cargador de tu laptop o celular necesita quedar libre arriba sin desarmar todo el canal.'),
                    ('Mide el grosor del tablero, el marco inferior y la pared', 'Antes de pedir bandejas de prensa o sujetadores en AliExpress, mide en milímetros el espesor de tu escritorio, revisa si pasa un travesaño metálico por el borde trasero y deja holgura frente al muro.'),
                    ('Calcula margen real para brazos de monitor y sillas', 'Si usas soporte articulado o escritorio elevable, prueba el recorrido en el punto más alto para no forzar los puertos HDMI o USB Type-C al mover la pantalla.'),
                    ('Ventila eliminadores y sube el multicontacto del piso', 'Fijar el multicontacto bajo la mesa evita polvo y tropiezos, siempre que dejes circular el aire alrededor de los cargadores de laptop y separes los cables gruesos de corriente.'),
                    ('Verifica adhesivos y diámetro interior de los clips', 'Las bases adhesivas pegan firme sobre melamina lisa, vidrio o aluminio, pero se despegan en aglomerado crudo sin barnizar. Revisa cuántos milímetros admite cada ranura de clip.'),
                    ('Etiqueta ambos extremos y usa tiras reutilizables de velcro', 'Colocar una etiqueta térmica junto a cada clavija ahorra tiempo al desconectar un equipo, y las cintas de velcro permiten sumar o quitar un cable sin cortar cinchos plásticos.'),
                ],
            ),
            'fr': (
                'Ranger les câbles de bureau : mesurer avant d’acheter | FLUXIXO',
                'Séparez câbles fixes et nomades, mesurez l’épaisseur du plateau, aérez les blocs secteur et étiquetez vos prises.',
                'Ranger les câbles de bureau : mesurer avant d’acheter',
                [
                    ('Séparez le câblage fixe des chargeurs nomades', 'L’alimentation de l’écran, la barre LED et le câble réseau RJ45 restent en place sous le bureau, alors que le chargeur d’ordinateur portable ou de téléphone doit rester accessible sans ouvrir toute la goulotte.'),
                    ('Mesurez l’épaisseur du plateau, le cadre et le recul mural', 'Avant de commander un panier à pince, relevez en millimètres l’épaisseur exacte du plateau, vérifiez la présence éventuelle d’une traverse métallique sous le chant arrière et contrôlez l’écart au mur.'),
                    ('Prévoyez une boucle d’aisance pour bras articulé ou bureau assis-debout', 'Réglez le bureau ou le bras d’écran à son amplitude maximale lors de la pose afin qu’aucun cordon HDMI ou USB Type-C ne tire sur les connecteurs.'),
                    ('Laissez respirer les transformateurs et la multiprise', 'Suspendre la multiprise sous le plateau libère le sol de la poussière, à condition de ne pas enfermer les blocs secteur chauds dans un boîtier hermétique.'),
                    ('Adaptez les passe-câbles adhésifs au revêtement', 'Les patins adhésifs tiennent durablement sur le verre, le métal peint ou le mélaminé lisse, mais adhèrent mal sous un aggloméré brut. Contrôlez le diamètre d’ouverture en millimètres.'),
                    ('Repérez chaque extrémité avec des attaches auto-agrippantes', 'Une étiquette thermique près de chaque fiche évite de débrancher le mauvais appareil, et les bandes velcro réutilisables se rouvrent en une seconde sans pince coupante.'),
                ],
            ),
            'he': (
                'סדר בכבלי השולחן: מודדים לפני שקונים | FLUXIXO',
                'הפרידו בין כבלים קבועים לניידים, מדדו את עובי השולחן, שמרו על אוורור ספקי הכוח וסמנו כל קצה בצורה מסודרת.',
                'סדר בכבלי השולחן: מודדים לפני שקונים',
                [
                    ('הפרידו בין ציוד קבוע לכבלים שלוקחים בתיק', 'כבלי חשמל של מסך, תאורת מסך וכבל רשת RJ45 נשארים קבועים מתחת לפלטה, בעוד שמטען של מחשב נייד או טלפון צריך להישאר נגיש מלמעלה בלי לפרק את כל התעלה.'),
                    ('מדדו את עובי הפלטה, מסגרת המתכת והמרווח מהקיר', 'לפני שמזמינים מגש כבלים עם מלחציים ב־AliExpress, מדדו במילימטרים את עובי השולחן, בדקו אם קורת חיזוק חוסמת את השפה האחורית וודאו שיש מרווח מספק מהקיר.'),
                    ('השאירו רפיון בטוח לזרוע מסך ולשולחן מתכוונן', 'אם המסך יושב על זרוע או שהשולחן עולה לגובה עמידה, בדקו את אורך הכבלים במצב הגבוה ביותר כדי ששקעי USB-C ו־HDMI לא יימתחו ויינזקו.'),
                    ('הרימו את המפצל מהרצפה ושמרו על אוורור לספקים', 'הצמדת רב־שקע מתחת לשולחן מקלה על שטיפת הרצפה ומונעת הצטברות אבק, כל עוד משאירים זרימת אוויר חופשית סביב ספקי כוח שמתחממים בעבודה.'),
                    ('התאימו תופסני דבק למשטח ולקוטר הכבל', 'מדבקות אקריליות נצמדות היטב לפורמייקה חלקה, זכוכית ומתכת, אך נוטות להתנתק מעץ גולמי מחוספס בתחתית שולחן. בדקו גם את רוחב החריץ במילימטרים עבור כבלי HDMI עבים.'),
                    ('סמנו את שני קצוות הכבל והעדיפו רצועות סקוץ׳ רב־פעמיות', 'תווית קטנה ליד התקע חוסכת ניחושים מאחורי המפצל, ורצועות סקוץ׳ מאפשרות להוסיף או להחליף כבל בשנייה בלי לגזור אזיקוני פלסטיק.'),
                ],
            ),
        },
    },
    {
        'slug': 'wifi-repeater-buying-guide',
        'preferred_product': 'katord-wifi-repeater',
        'related_products': ('katord-wifi-repeater', 'find-063-cable-tester', 'find-009-bulb-camera', 'find-040-microscope', 'import-0488'),
        'published_dates': {
            'ru': '2026-11-13',
            'en': '2026-11-20',
            'pt': '2026-11-24',
            'es': '2026-11-24',
            'fr': '2026-11-24',
            'he': '2026-11-24',
        },
        'translations': {
            'ru': (
                'Как выбрать усилитель Wi-Fi для квартиры и дачи | FLUXIXO',
                'Два диапазона, пропускная способность, розетка на полпути и режим точки доступа: что проверить перед покупкой репитера Wi-Fi.',
                'Как выбрать усилитель Wi-Fi сигнала для квартиры и дачи',
                [
                    ('Сколько антенн и диапазонов нужно на практике', 'Простой усилитель только на 2.4 GHz цепляется за перегруженные соседские каналы и редко даёт стабильный поток для видеозвонков и смарт-телевизора. Двухдиапазонная модель с поддержкой 2.4 GHz и 5 GHz принимает сигнал от основного роутера на одной частоте и раздаёт дальше без сильной просадки. Сравнивайте не суммарную цифру на коробке вроде 1200 Mbps, а реальную поддержку 5 GHz вашим домашним роутером — иначе второй диапазон останется пустым.'),
                    ('Где ставить повторитель, чтобы он усиливал, а не тормозил', 'Репитер бесполезен в самом дальнем углу спальни, где телефон уже еле ловит одну полоску. Повторитель усиливает тот сигнал, который сумел поймать сам, поэтому для него нужна розетка примерно на полпути между роутером и слабой комнатой — в зоне уверенного приёма. Заранее проверьте толщину несущих бетонных стен и посмотрите, есть ли у прибора индикатор уровня сигнала на корпусе: по нему проще найти рабочую точку.'),
                    ('Порт RJ45 и режим точки доступа', 'Наличие сетевого разъёма RJ45 часто недооценивают, а зря: к нему можно подключить стационарный компьютер, приставку или рабочий ноутбук коротким патч-кордом, даже если у самого ПК слабый приёмник. Во многих моделях тот же порт работает и на вход — кабель из щитка превращает устройство в компактную точку доступа на втором этаже или в мансарде, без двойных потерь скорости по воздуху.'),
                    ('Вилка, нагрев и способ настройки', 'При заказе сетевой техники проверьте тип вилки — для российских розеток нужен стандарт EU без громоздкого переходника, который перевешивает корпус и болтается в вертикальной розетке. Также загляните в описание настройки: удобнее модели с быстрым сопряжением кнопкой WPS и простым веб-интерфейсом на понятном языке, а вентиляционные прорези по бокам спасают плату от троттлинга при круглосуточной работе.'),
                ],
            ),
            'en': (
                'How to Choose and Place a Wi-Fi Range Extender | FLUXIXO',
                'Find an outlet with a strong router signal, compare 2.4 and 5 GHz, and check Ethernet modes before buying a Wi-Fi range extender.',
                'How to choose and place a Wi-Fi range extender',
                [
                    (
                        'Check where the connection gets weak',
                        'Try the same device near the router and in the room where you want better Wi-Fi. '
                        'If the connection is poor in both places, check the router and internet connection first. '
                        'A plug-in extender is worth considering when the router works well nearby and a single room has weak reception. '
                        'If you can run Ethernet to that room, compare a wired access point before you buy.',
                    ),
                    (
                        'Match the bands your router and devices use',
                        'Check whether the router, extender and devices you use support 2.4 GHz and 5 GHz. '
                        'The 2.4 GHz band often reaches farther through walls. The 5 GHz band can offer more capacity at shorter distances. '
                        'Dual-band ratings can add the theoretical link rates of both bands. The speed a device actually gets depends on '
                        'the signal back to the router, interference and how the extender shares airtime between receiving and forwarding traffic.',
                    ),
                    (
                        'Start with an outlet between the router and the weak room',
                        'Try an outlet roughly halfway to the room, where the router signal is still strong. '
                        'Move one outlet closer to the router if a concrete wall or floor leaves the extender with a weak connection. '
                        'Use the signal indicator if the model has one. Once connected to the extender, try a call or stream in the room '
                        'you want to cover, then compare it with a second outlet if the connection still drops.',
                    ),
                    (
                        'Check what the Ethernet port supports',
                        'A port that connects a desktop or TV to the extender can be useful even when the extender itself connects to the router over Wi-Fi. '
                        'Access point mode is a separate feature. It lets a supported model take an Ethernet connection from the router and provide '
                        'Wi-Fi in the room, avoiding the extra wireless hop. If you plan to use that setup, check for explicit access point mode and the port speed.',
                    ),
                    (
                        'Check the plug and setup for the exact variant',
                        'Match the seller’s plug option to your outlet and check that the extender has clearance around it. '
                        'Look for setup instructions for the exact model, including the Wi-Fi security modes it supports and whether setup uses a browser or an app. '
                        'If you plan to use WPS, check that the router and extender both support it.',
                    ),
                    (
                        'KATORD 1200 Mbps as a listing example',
                        'The KATORD Wi-Fi range extender in our catalog is listed as a 1200 Mbps dual-band model with 2.4 GHz and 5 GHz support. '
                        'Use the listing rating to identify the model and use the checks above to judge whether it suits your room. '
                        'Confirm the plug, Ethernet mode and setup method for the variant you select.',
                    ),
                ],
            ),
            'pt': (
                'Como escolher e posicionar um repetidor Wi-Fi | FLUXIXO',
                'Compare redes 2,4 e 5 GHz, escolha a tomada no meio do caminho, confira porta RJ45 e padrão bivolt antes de pedir.',
                'Como escolher e posicionar um repetidor de sinal Wi-Fi em casa',
                [
                    ('Diferença prática entre 2,4 GHz e Dual Band 5 GHz', 'Repetidores simples que operam só em 2,4 GHz sofrem com interferência de redes vizinhas em prédios e entregam velocidade limitada para smart TVs e chamadas de vídeo. Um modelo Dual Band (como a classe AC1200 combinando 2,4 GHz e 5 GHz) atravessa melhor paredes em 2,4 GHz e entrega banda mais limpa em 5 GHz nos cômodos próximos.'),
                    ('Onde ligar na tomada: regra do meio do caminho', 'Nunca instale o repetidor dentro do quarto onde o celular já perdeu quase todo o sinal: ele só consegue retransmitir a qualidade de sinal que recebe do roteador principal. Escolha uma tomada no corredor, aproximadamente na metade do trajeto, antes de paredes grossas de alvenaria ou lajes, guiando-se pelo LED indicador de sinal no aparelho.'),
                    ('Porta de rede RJ45 e modo Ponto de Acesso', 'Um conector Ethernet RJ45 na base permite ligar um computador, videogame ou TV por cabo curto com muito mais estabilidade. Além disso, se você já tiver um cabo de rede passado até o fundo da casa, o modo ponto de acesso transforma o aparelho em um emissor Wi-Fi dedicado sem perda de velocidade por repetição sem fio.'),
                    ('Tensão bivolt, plugue compatível e ventilação', 'No AliExpress, confirme que a variação marcada é bivolt (100–240V) com pino redondo padrão EU/BR compatível com tomadas NBR 14136 de 10A sem adaptador frouxo, e deixe espaço livre ao redor das frestas laterais para dissipar o calor no uso contínuo.'),
                ],
            ),
            'es': (
                'Cómo elegir y ubicar un repetidor Wi-Fi en casa | FLUXIXO',
                'Compara doble banda 2.4 y 5 GHz, ubicación intermedia, puerto RJ45 y clavija americana antes de comprar en AliExpress.',
                'Cómo elegir y colocar un repetidor de señal Wi-Fi de doble banda',
                [
                    ('Por qué conviene doble banda (2.4 GHz y 5 GHz)', 'Un repetidor básico de una sola banda en 2.4 GHz se satura fácil entre módems vecinos y hornos de microondas. Un equipo de doble banda clase 1200 Mbps aprovecha 2.4 GHz para cruzar muros de concreto o tabique y reserva 5 GHz para videollamadas estables y streaming en alta definición.'),
                    ('Colócalo a mitad de camino, no en la zona sin señal', 'Si enchufas el repetidor hasta la recámara o patio donde tu celular apenas marca una raya, solo amplificará una conexión inestable. Ubícalo en un contacto intermedio donde la señal del módem principal todavía llegue fuerte, revisando el indicador LED de cobertura.'),
                    ('Puerto Ethernet RJ45 y modo punto de acceso', 'Contar con puerto RJ45 te permite conectar por cable una consola, PC de escritorio o pantalla inteligente cercana, o bien recibir un cable de red directo desde tu módem para operar como punto de acceso puro sin dividir el ancho de banda inalámbrico.'),
                    ('Clavija tipo A/B para México y ventilación lateral', 'Antes de pagar en AliExpress, selecciona explícitamente la variante de clavija plana tipo A (100–240V compatible con 110–127V en México) para que no cuelgue con adaptadores flojos, y evita taparlo detrás de muebles cerrados.'),
                ],
            ),
            'fr': (
                'Comment choisir et placer un répéteur Wi-Fi | FLUXIXO',
                'Double bande 2,4 et 5 GHz, prise à mi-chemin de la box, port RJ45 et fiche européenne 230V : les critères clés.',
                'Comment choisir et bien placer un répéteur Wi-Fi pour logement',
                [
                    ('Intérêt concret du bi-bande 2,4 GHz et 5 GHz', 'Un répéteur limité au 2,4 GHz subit de plein fouet l’encombrement des box voisines en immeuble. Un modèle bi-bande (classe AC1200) combine la portée du 2,4 GHz à travers les cloisons et le débit plus confortable du 5 GHz pour la visioconférence ou un téléviseur connecté.'),
                    ('La règle de la prise murale à mi-parcours', 'Brancher un répéteur directement dans la pièce où le téléphone ne capte déjà plus rien ne sert à rien : l’appareil ne relaye que le signal qu’il reçoit lui-même de votre box internet. Installez-le sur une prise située à mi-chemin, en amont d’un mur porteur épais, en vous aidant du voyant de réception.'),
                    ('Port Ethernet RJ45 et mode point d’accès filaire', 'Une prise RJ45 intégrée permet soit de relier en filaire un PC fixe ou un décodeur TV dépourvu de bon Wi-Fi, soit de brancher un câble Ethernet tiré depuis la box en mode point d’accès pour créer une couverture neuve à l’étage sans perte radio.'),
                    ('Prise européenne 230V, appairage WPS et aération', 'Sur la fiche AliExpress, sélectionnez la version prise EU 230V afin qu’elle s’insère fermement dans vos prises murales sans adaptateur, vérifiez la compatibilité WPS avec votre box et laissez les ouïes latérales dégagées.'),
                ],
            ),
            'he': (
                'איך לבחור ולמקם מגדיל טווח Wi-Fi לבית | FLUXIXO',
                'תדרי 2.4 ו־5 GHz, מיקום נכון מול קירות בטון וממ״ד, חיבור רשת RJ45 ותקע מתאים לישראל לפני הזמנת רפיטר ב־AliExpress.',
                'איך לבחור ולמקם מגדיל טווח (רפיטר) Wi-Fi לדירה ולבית',
                [
                    ('למה חשוב לבחור דגם דו־תדרי (2.4 GHz ו־5 GHz)', 'מגדיל טווח ישן הפועל רק בתדר 2.4 GHz סובל מעומס של עשרות רשתות שכנות בבניין משותף ומתקשה להחזיק שיחות וידאו וסטרימינג חלק. דגם דו־תדרי בדירוג 1200 Mbps משלב חדירה טובה יותר דרך קירות בתדר 2.4 GHz עם קיבולת מהירה בתדר 5 GHz לטווח קרוב.'),
                    ('כלל הזהב למיקום: באמצע הדרך ולפני קיר הממ״ד', 'הצבת הרפיטר בתוך הממ״ד הסגור או בקצה המרפסת שבה הטלפון בקושי קולט קו אחד לא תעזור — המכשיר חייב לקלוט אות חזק מהנתב הראשי כדי לשדר אותו הלאה. חברו אותו לשקע במסדרון בערך באמצע הדרך, מחוץ לדלת הפלדה וקירות הבטון המזוינים של הממ״ד, והיעזרו בנורית חיווי הקליטה.'),
                    ('שקע רשת RJ45 ומצב נקודת גישה קווית', 'יציאת RJ45 בתחתית המכשיר שימושית בשני כיוונים: אפשר לחבר אליה מחשב נייח או סטרימר בכבל קצר לקבלת חיבור יציב, ואם כבר מושחל כבל רשת בקיר מראוטר הסיבים — מצב נקודת גישה הופך את היחידה למשדר Wi-Fi מהיר בחדר בלי לאבד מהירות באוויר.'),
                    ('תקע תואם 230V לישראל, לחצן WPS ואוורור', 'בעמוד המוכר ב־AliExpress הקפידו לבחור גרסת תקע EU המתאימה לשקעים בישראל (220–230V) ללא מתאם רופף שנוטה מהקיר, ודאו שהשקע גלוי ומאוורר ולא חסום מאחורי ארון צמוד.'),
                ],
            ),
        },
    },
]

def all_articles():
    """List translated guides, multilingual SEO guides, and Russian-only guides."""
    multi = []
    if EXTRA_MULTILINGUAL_FILE.exists():
        for row in json.loads(EXTRA_MULTILINGUAL_FILE.read_text(encoding='utf-8')):
            translations = {}
            for lang, payload in row.get('translations', {}).items():
                title, desc, h1, sections = payload
                translations[lang] = (title, desc, h1, [tuple(pair) for pair in sections])
            multi.append({
                'slug': row['slug'],
                'preferred_product': row['preferred_product'],
                'related_products': tuple(row.get('related_products') or ()),
                'date': row.get('date'),
                'modified': row.get('modified'),
                'image': row.get('image'),
                'translations': translations,
            })
    extra = []
    if EXTRA_RU_FILE.exists():
        for row in json.loads(EXTRA_RU_FILE.read_text(encoding='utf-8')):
            trans = {'ru': (row['title'], row['description'], row['h1'], [tuple(pair) for pair in row['sections']])}
            for lang, payload in row.get('translations', {}).items():
                if lang != 'ru':
                    title, desc, h1, sections = payload
                    trans[lang] = (title, desc, h1, [tuple(pair) for pair in sections])
            extra.append({
                'slug': row['slug'],
                'preferred_product': row['preferred_product'],
                'related_products': tuple(row.get('related_products') or ()),
                'date': row.get('date'),
                'image': row.get('image'),
                'translations': trans,
            })
    return ARTICLES + multi + extra + comparison_guides.as_journal_articles()


def article_path(lang, slug):
    prefix = JOURNAL_UI[lang]['slug_prefix']
    return f'{prefix}{slug}/'


def index_path(lang):
    return JOURNAL_UI[lang]['slug_prefix']


def generate_journal_pages(origin, products, i18n_data, page_fn, write_fn, alternates_fn):
    """Render multilingual journal index and guide pages; returns generated route paths."""
    routes = []
    by_id = {p['id']: p for p in products}
    index_alternates = {lang: index_path(lang) for lang in JOURNAL_UI}

    for lang, ui in JOURNAL_UI.items():
        prefix_ru = '' if lang == 'ru' else f'/{lang}'
        catalog_href = '/catalog/' if lang == 'ru' else f'/{lang}/'
        home_href = '/catalog/' if lang == 'ru' else f'/{lang}/'
        cards_html = []
        for article in all_articles():
            if lang not in article['translations']:
                continue
            slug = article['slug']
            published = article.get('published_dates', {}).get(lang) or article.get('date') or ui['date']
            modified = article.get('modified_dates', {}).get(lang) or article.get('modified') or published
            meta_title, meta_desc, h1, sections = article['translations'][lang]
            rel_prod = by_id.get(article['preferred_product'])
            art_url = article_path(lang, slug)
            art_alternates = {l: article_path(l, slug) for l in JOURNAL_UI if l in article['translations']}
            routes.append(art_url)

            related_link = ''
            if rel_prod:
                prod_href = f'{prefix_ru}/products/{rel_prod["id"]}/'
                prod_name = (rel_prod['name'] if lang == 'ru'
                             else (i18n_data.get('products', {}).get(rel_prod['id'], {}).get(lang, {}) or {}).get('name', rel_prod['name']))
                colon = ' : ' if lang == 'fr' else ': '
                related_link = f'<a class="button secondary" href="{prod_href}">{e(ui["related_product_label"])}{colon}{e(prod_name)}</a>'

            if article.get('image'):
                img_path = thumb_rel = article['image']
            elif rel_prod:
                img_path = rel_prod['image']
                thumb_rel = 'assets/thumbs/' + img_path.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '-480.webp'
            else:
                # Keep the original example's image after retirement when it is still public.
                img_path = thumb_rel = f'assets/images/{article["preferred_product"]}.webp'
                if not (DIST / img_path).is_file():
                    img_path = thumb_rel = 'assets/journal/buying-checklist.png'

            sec_html = ''.join(f'<section><h2>{e(h2)}</h2><p>{e(body)}</p></section>' for h2, body in sections)
            cmp_html = (
                comparison_guides.render_comparison_table(article['comparison_world'], lang, products, i18n_data)
                if article.get('comparison_world') else ''
            )
            faq_html, faq_schema = comparison_guides.render_faq_and_schema(article.get('faq'), lang)
            rel_ids = []
            for pid in (article.get('preferred_product'), *(article.get('related_products') or ())):
                if isinstance(pid, str) and pid in by_id and pid not in rel_ids:
                    rel_ids.append(pid)
            rel_list_html = ''
            if len(rel_ids) >= 2:
                rel_items = []
                for pid in rel_ids:
                    rp = by_id[pid]
                    rp_name = (rp['name'] if lang == 'ru'
                               else (i18n_data.get('products', {}).get(pid, {}).get(lang, {}) or {}).get('name', rp['name']))
                    rel_items.append(f'<li><a href="{prefix_ru}/products/{pid}/">{e(rp_name)}</a></li>')
                rel_list_html = (f'<section class="journal-related"><h2>{e(JOURNAL_RELATED_HEADING[lang])}</h2>'
                                 f'<ul>{"".join(rel_items)}</ul></section>')
            crumbs = [(ui['home'], home_href), (ui['eyebrow'], index_path(lang)), (h1, art_url)]
            crumb_nav = (
                f'<nav class="breadcrumb"><a href="{home_href}">FLUXIXO</a>'
                f'<span class="breadcrumb-sep">/</span><a href="{index_path(lang)}">{e(ui["eyebrow"])}</a>'
                f'<span class="breadcrumb-sep">/</span><span>{e(h1)}</span></nav>'
            )
            art_graph = [
                {
                    '@type': 'Article',
                    'headline': h1,
                    'description': meta_desc,
                    'image': origin + '/' + img_path,
                    'datePublished': published,
                    'dateModified': modified,
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
            ]
            if faq_schema:
                art_graph.append(faq_schema)
            art_schema = {'@context': 'https://schema.org', '@graph': art_graph}
            art_body = (
                f'{crumb_nav}'
                f'<article class="about-page journal-article">'
                f'<p class="eyebrow">{e(ui["eyebrow"])}</p>'
                f'<h1>{e(h1)}</h1>'
                f'<div class="cta-row">{related_link}'
                f'<a class="button" href="{catalog_href}">{e(ui["catalog_cta"])}</a></div>'
                f'{sec_html}{cmp_html}{faq_html}{rel_list_html}'
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
