"""Interface copy for the redesign. Voice: a friend who digs through AliExpress, in the words each market uses on the street
(Mexico "hallazgos", Brazil "achadinhos" and "garimpar", France "trouvailles/dénicher", Israel "מציאות", Russia "находки")."""


def ru_count(n):
    if n % 10 == 1 and n % 100 != 11:
        return f'{n} находка'
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f'{n} находки'
    return f'{n} находок'


UI = {
    'es': dict(tabs=('Inicio', 'Mundos', 'Catálogo', 'Buscar'), search='Buscar un hallazgo…', nothing='Nada por aquí. Prueba con otra palabra.', language='Idioma', app='Hallazgos de AliExpress',
               cta='¡Lo quiero!', more='Ver detalles', nav=('Drop', 'Mundos', 'Catálogo'),
               drop='Drop del día', drop_old='Último drop',
               hero_heading='Hallazgos útiles para el día a día', hero_cta='Ver todos los hallazgos', hero_frequency='Hasta tres hallazgos nuevos al día',
               drop_text='Ideas de AliExpress para tu casa, cocina y escritorio, con consejos sobre qué revisar antes de comprar.',
               hero_note='Podemos recibir una comisión por compras mediante enlaces de afiliado.', seller_cta='Ver en AliExpress',
               next_drop='Próximo drop', when=('hoy', 'mañana'), find_day='Hallazgo del día', seller='Foto real del vendedor',
               countdown_label='Próxima actualización', countdown_awaiting='Esperando actualización', countdown_schedule='Inicio previsto: cada día a las 15:30, hora de Israel',
               world='Mundo', enter='Ver todo', all=('Todos los', 'hallazgos'), filter_all='Todos',
               prev='Anterior', next='Siguiente', related=('Más de', 'este mundo'),
               home='Inicio', about='Acerca de', privacy='Privacidad',
               foot='Buscamos lo más raro y útil de AliExpress para que tú no tengas que hacerlo.',
               count='{n} hallazgos'.format, title='Hallazgos de AliExpress: gadgets y hogar | FLUXIXO',
               meta='Explora gadgets y artículos para el hogar de AliExpress, con descripciones breves, consejos antes de comprar y enlaces al vendedor.'),
    'pt': dict(tabs=('Início', 'Mundos', 'Catálogo', 'Buscar'), search='Buscar um achadinho…', nothing='Nada por aqui. Tente outra palavra.', language='Idioma', app='Achadinhos do AliExpress',
               cta='Quero esse!', more='Ver detalhes', nav=('Drop', 'Mundos', 'Catálogo'),
               drop='Drop do dia', drop_old='Último drop',
               hero_heading='Achados úteis para o dia a dia', hero_cta='Ver todos os achadinhos', hero_frequency='Até três novos achadinhos por dia',
               drop_text='Achados do AliExpress para casa, cozinha e escritório, com dicas do que conferir antes de comprar.',
               hero_note='Podemos receber uma comissão por compras pelos links de afiliado.', seller_cta='Ver no AliExpress',
               next_drop='Próximo drop', when=('hoje', 'amanhã'), find_day='Achadinho do dia', seller='Foto real do vendedor',
               countdown_label='Próxima atualização', countdown_awaiting='Aguardando atualização', countdown_schedule='Início previsto: todos os dias às 15h30, horário de Israel',
               world='Mundo', enter='Ver tudo', all=('Todos os', 'achadinhos'), filter_all='Todos',
               prev='Anterior', next='Próximo', related=('Mais', 'deste mundo'),
               home='Início', about='Sobre', privacy='Privacidade',
               foot='A gente garimpa o AliExpress para você não precisar.',
               count='{n} achadinhos'.format, title='Achadinhos do AliExpress: gadgets e casa | FLUXIXO',
               meta='Explore gadgets e itens para casa do AliExpress, com descrições curtas, dicas antes de comprar e links para o vendedor.'),
    'en': dict(tabs=('Home', 'Worlds', 'Catalog', 'Search'), search='Search the finds…', nothing='Nothing here. Try another word.', language='Language', app='AliExpress finds',
               cta='I want it', more='See details', nav=('Drop', 'Worlds', 'Catalog'),
               drop="Today's drop", drop_old='Latest drop',
               hero_heading='Useful finds for everyday life', hero_cta='Browse all finds', hero_frequency='Up to three new finds a day',
               drop_text='AliExpress finds for your home, kitchen and desk, with practical tips on what to check before you buy.',
               hero_note='We may earn a commission through affiliate links.', seller_cta='View on AliExpress',
               next_drop='Next drop', when=('today', 'tomorrow'), find_day='Find of the day', seller='Real seller photo',
               countdown_label='Next update', countdown_awaiting='Awaiting update', countdown_schedule='Planned start: daily at 15:30 Israel time',
               world='World', enter='See all', all=('All', 'finds'), filter_all='All',
               prev='Previous', next='Next', related=('More from', 'this world'),
               home='Home', about='About', privacy='Privacy',
               foot="We dig through AliExpress so you don't have to.",
               count='{n} finds'.format, title='AliExpress finds: gadgets and home essentials | FLUXIXO',
               meta='Explore gadgets and home essentials from AliExpress, with short descriptions, buying tips and links to the seller.'),
    'fr': dict(tabs=('Accueil', 'Univers', 'Catalogue', 'Chercher'), search='Chercher une trouvaille…', nothing='Rien ici. Essayez un autre mot.', language='Langue', app='Trouvailles AliExpress',
               cta='Je le veux !', more='Voir la fiche', nav=('Drop', 'Univers', 'Catalogue'),
               drop='Drop du jour', drop_old='Dernier drop',
               hero_heading='Des trouvailles utiles au quotidien', hero_cta='Voir toutes les trouvailles', hero_frequency='Jusqu’à trois nouvelles trouvailles par jour',
               drop_text='Des trouvailles AliExpress pour la maison, la cuisine et le bureau, avec les points à vérifier avant d’acheter.',
               hero_note='Nous pouvons recevoir une commission via les liens d’affiliation.', seller_cta='Voir sur AliExpress',
               next_drop='Prochain drop', when=('aujourd’hui', 'demain'), find_day='Trouvaille du jour', seller='Vraie photo du vendeur',
               countdown_label='Prochaine mise à jour', countdown_awaiting='Mise à jour en attente', countdown_schedule='Début prévu : chaque jour à 15 h 30, heure d’Israël',
               world='Univers', enter='Tout voir', all=('Les', 'trouvailles'), filter_all='Tout',
               prev='Précédent', next='Suivant', related=('Dans le', 'même univers'),
               home='Accueil', about='À propos', privacy='Confidentialité',
               foot='On fouille AliExpress pour vous éviter de le faire.',
               count='{n} trouvailles'.format, title='Trouvailles AliExpress : gadgets et maison | FLUXIXO',
               meta='Découvrez des gadgets et des objets pour la maison sur AliExpress, avec des descriptions courtes, des conseils et des liens vers le vendeur.'),
    'he': dict(tabs=('ראשי', 'עולמות', 'קטלוג', 'חיפוש'), search='חיפוש מציאה…', nothing='לא מצאנו כלום. נסו מילה אחרת.', language='שפה', app='מציאות מ־AliExpress',
               cta='רוצה את זה!', more='לפרטים', nav=('הדרופ', 'עולמות', 'קטלוג'),
               drop='הדרופ היומי', drop_old='הדרופ האחרון',
               hero_heading='מוצרים שימושיים ליום־יום', hero_cta='לכל המציאות', hero_frequency='עד שלוש מציאות חדשות ביום',
               drop_text='מוצרים מ־AliExpress לבית, למטבח ולפינת העבודה, עם טיפים למה כדאי לבדוק לפני שקונים.',
               hero_note='ייתכן שנקבל עמלה על רכישות דרך קישורי שותפים.', seller_cta='לצפייה ב־AliExpress',
               next_drop='הדרופ הבא', when=('היום', 'מחר'), find_day='המציאה של היום', seller='תמונה אמיתית מהמוכר',
               countdown_label='העדכון הבא', countdown_awaiting='ממתינים לעדכון', countdown_schedule='תחילת העדכון מתוכננת בכל יום בשעה 15:30, שעון ישראל',
               world='עולם', enter='לכל המוצרים', all=('כל', 'המציאות'), filter_all='הכול',
               prev='הקודם', next='הבא', related=('עוד', 'מהעולם הזה'),
               home='ראשי', about='אודות', privacy='פרטיות',
               foot='אנחנו חופרים ב־AliExpress כדי שאתם לא תצטרכו.',
               count='{n} מציאות'.format, title='מציאות מ־AliExpress: גאדג׳טים ומוצרים לבית | FLUXIXO',
               meta='גלו גאדג׳טים ומוצרים לבית מ־AliExpress, עם תיאורים קצרים, טיפים לפני הזמנה וקישורים למוכר.'),
    'ru': dict(tabs=('Главная', 'Миры', 'Каталог', 'Поиск'), search='Найти находку…', nothing='Ничего не нашлось. Попробуйте другое слово.', language='Язык', app='Находки с AliExpress',
               cta='Хочу такой!', more='Подробнее', nav=('Дроп', 'Миры', 'Каталог'),
               drop='Дроп дня', drop_old='Свежий дроп',
               hero_heading='Полезные находки на каждый день', hero_cta='Смотреть все находки', hero_frequency='До трёх новых находок в день',
               drop_text='Идеи с AliExpress для дома, кухни и рабочего места — с подсказками, что проверить перед покупкой.',
               hero_note='Партнёрские ссылки: мы можем получать комиссию.', seller_cta='На AliExpress',
               next_drop='Следующий дроп', when=('сегодня', 'завтра'), find_day='Находка дня', seller='Настоящее фото продавца',
               countdown_label='Следующее обновление', countdown_awaiting='Ожидаем обновление', countdown_schedule='Плановый старт: ежедневно в 15:30 по израильскому времени',
               world='Мир', enter='Смотреть все', all=('Все находки ·', ''), filter_all='Все',
               prev='Назад', next='Дальше', related=('Ещё из', 'этого мира'),
               home='Главная', about='О проекте', privacy='Конфиденциальность',
               foot='Копаемся в AliExpress, чтобы вам не пришлось.',
               count=lambda n: ru_count(n), title='Находки с AliExpress: гаджеты и вещи для дома | FLUXIXO',
               meta='Гаджеты и вещи для дома с AliExpress: короткие описания, подсказки перед покупкой и ссылки на продавца. Выбирайте находки в каталоге FLUXIXO.'),
}

CATEGORY_COPY_RU = {
    'Техника': 'Гаджеты, электроника и умные аксессуары для дома и работы.',
    'Дом': 'Полезные приборы, свет и мелочи, с которыми дома порядок.',
    'Кухня': 'Кухонные гаджеты, вакууматоры и аксессуары для напитков.',
    'В дороге': 'Автоаксессуары, гаджеты в поездку и всё, что пригодится в пути.',
    'Инструменты': 'Лазерные рулетки, паяльники, детекторы и компактный электроинструмент.',
    'Уход': 'Приборы для ухода за собой: стерилизаторы, стайлеры, массажёры.',
    'Спорт': 'Тренажёры, велоаксессуары и инвентарь для занятий дома.',
    'На природе': 'Снаряжение для кемпинга, рыбалки, походов и отдыха на воздухе.',
    'Питомцы': 'Автоматические игрушки, трекеры и аксессуары для кошек и собак.',
}

# The shared front page at '/' is English for every visitor and crawler. Russian product, category and guide
# URLs stay unchanged; '/catalog/' is the Russian entry page and '/en/' is the full English catalog.
ROOT_EN = dict(
    title='Useful AliExpress finds for everyday life | FLUXIXO',
    desc=('Explore AliExpress finds for home, kitchen and everyday life, with buying checklists and links to sellers. '
          'FLUXIXO may earn an affiliate commission.'),
    fresh=('Latest', 'finds'),
    all_btn='Full catalog · {n}',
    guides='Buying guides',
    about_h='What is FLUXIXO?',
    about=('FLUXIXO is an independent collection of useful and unusual AliExpress finds for your home, kitchen, desk '
           'and everyday life. We do not sell products: purchases take place on AliExpress, where the seller shows '
           'the current price, available options and shipping details.',
           'Each find includes a short description, product imagery and points to check before ordering, such as '
           'compatibility, dimensions, power requirements and what is included. Images are illustrative; check the '
           'seller’s listing before buying. We may earn a commission through affiliate links.'),
    how_h='How to use FLUXIXO',
    how=('Start with the latest finds at the top, browse the categories or open the full catalog to search by name. '
         'Our buying guides explain what to compare before ordering, including the final price, delivery and product '
         'specifications.'),
    langs_h='Explore FLUXIXO in other languages',
)

# Headings of the extra buyer-advice block on Russian product pages (texts: tools/ru_long_copy.json).
MORE_RU = dict(who='Кому пригодится', check='Что проверить перед заказом')
MORE_HEADINGS = {
    'ru': dict(who='Кому и для каких задач подойдёт', skip='Ограничения и кому не подойдёт', compare='Сравнение с альтернативами', check='Что проверить в карточке перед заказом'),
    'en': dict(who='Where it fits best', skip='Trade-offs and when to skip', compare='How it compares to alternatives', check='What to check before ordering'),
    'pt': dict(who='Para quem faz mais sentido', skip='Limitações e quando evitar', compare='Comparação com alternativas', check='O que conferir antes de comprar'),
    'es': dict(who='Para quién funciona mejor', skip='Limitaciones y cuándo evitarlo', compare='Comparación frente a alternativas', check='Qué revisar antes de pedir'),
    'fr': dict(who='Pour quels usages', skip='Limites et cas à éviter', compare='Face aux alternatives', check='Points à vérifier avant de commander'),
    'he': dict(who='למי זה מתאים במיוחד', skip='מגבלות ומתי כדאי לוותר', compare='השוואה לחלופות נפוצות', check='מה לבדוק בעמוד המוצר לפני ההזמנה'),
}

# A longer note under each Russian category: what the world holds and what to check before ordering.
CATEGORY_LONG_RU = {
    'Техника': ('В этом мире — электроника на каждый день: наушники и колонки, зарядные станции и хабы, мыши, микрофоны, '
                'камеры, карманные принтеры и другие гаджеты. Перед заказом техники с AliExpress сверяйте разъёмы и '
                'стандарты связи со своими устройствами, тип вилки и напряжение, а для беспроводных вещей — ёмкость '
                'аккумулятора и способ зарядки. Если гаджет работает через приложение, уточните у продавца, '
                'поддерживает ли оно ваш смартфон и русский язык.'),
    'Дом': ('Здесь вещи, которые делают быт проще: свет для чтения и сна, приборы для уборки и ухода за одеждой, '
            'автополив для растений, метеостанции и небольшие полезные устройства. Для товаров в дом главное — размеры '
            'и питание: измерьте место, куда встанет прибор, проверьте тип вилки или кабеля и уточните, что входит в '
            'комплект. У вещей с аккумулятором полезно заранее узнать время работы и способ зарядки.'),
    'Кухня': ('Кухонные находки: мельницы и весы, термометры, вакууматоры, приборы для кофе и напитков, блинницы, '
              'ланч-боксы с подогревом и мелочи для хлеба и заготовок. Всё, что включается в розетку, проверяйте на '
              'напряжение 220 В и подходящую вилку. Для того, что касается еды, смотрите материал — нержавеющая сталь, '
              'стекло, пищевой силикон — и то, как прибор разбирается для мытья. Объём и диаметр сверяйте со своей посудой.'),
    'В дороге': ('Автомобильные и дорожные находки: компрессоры и пусковые устройства, держатели, диагностические '
                 'сканеры, подсветка салона, пылесосы, а ещё вещи для мотоцикла, самоката и поездок налегке. Перед '
                 'заказом сверяйте питание — прикуриватель 12 В, USB или собственный аккумулятор — и совместимость с '
                 'вашей машиной: разъём диагностики, размер дефлекторов, расстояние между стойками подголовника. Для '
                 'зимних вещей с подогревом важны размер и время работы.'),
    'Инструменты': ('Компактный инструмент для дома и мастерской: дальномеры, паяльники, детекторы проводки, тестеры '
                    'кабеля, мини-пилы, экстракторы и узкие приспособления для точных работ. У инструмента с AliExpress '
                    'внимательно смотрите вариант комплектации: аккумулятор и зарядное устройство часто продаются '
                    'отдельно от самого инструмента. Сверяйте диаметры, диапазоны и допустимую толщину материала со '
                    'своей задачей, а для измерительных приборов — заявленную точность и способ калибровки.'),
    'Уход': ('Приборы для ухода за собой дома и в поездке: стайлеры, аппараты для маникюра, пилки для стоп, '
             'стерилизаторы, тепловые пояса и простые аксессуары для отдыха глаз. Для таких вещей важнее всего '
             'безопасность: уточняйте пределы нагрева и автоотключение, влагозащиту корпуса и тип зарядки. Сменные '
             'насадки и ролики — расходный материал, поэтому заранее посмотрите, сколько их в наборе и продаются ли '
             'они отдельно.'),
    'Спорт': ('Небольшой инвентарь для тренировок и велосипеда: скакалки со счётчиком, пояса для отработки удара, '
              'фонари, велокомпьютеры и приспособления для мячей. Перед заказом проверяйте регулировку под рост и '
              'размер, тип крепления к рулю или раме и питание — батарейка или зарядка от USB. Если устройство ведёт '
              'статистику через приложение, уточните у продавца совместимость со своим смартфоном.'),
    'На природе': ('Вещи для дачи, рыбалки и походов: треккинговые палки, сигнализаторы поклёвки, приспособления для '
                   'капельного полива и другое лёгкое снаряжение. Для уличных товаров смотрите материал и вес, длину в '
                   'сложенном виде и то, продаётся ли вещь поштучно или парой. Диаметры трубок, удилищ и фитингов лучше '
                   'измерить заранее: от совпадения размеров зависит, будет ли деталь держаться плотно.'),
    'Питомцы': ('Аксессуары для кошек и собак: автоматические игрушки, трекеры на ошейник, одежда для прогулок, '
                'диспенсеры пакетов и расходные материалы для лотков. Одежду выбирайте по меркам питомца, а не по '
                'названию размера: обхват груди, длина спины и шея. У трекеров уточняйте, как именно определяется '
                'местоположение, а у расходников — точную модель устройства, для которого они подходят.'),
}

# "What to check before ordering" notes for category pages in the other languages (the Russian ones are above).
# Only the outdoor category had too little text of its own in these languages.
CATEGORY_LONG = {
    'На природе': {
        'en': ('Gear for the garden, fishing and hiking trips: trekking poles, bite alarms, drip irrigation kits and other '
               'light equipment. For outdoor items, check the material and weight, the folded length, and whether the '
               'listing is for one piece or a pair. Measure the diameter of your hoses, rods or fittings before ordering: '
               'a part only holds tight when those sizes match. If an item runs on a battery, look at how it charges and '
               'whether the cable is in the box.'),
        'pt': ('Equipamentos para jardim, pesca e trilhas: bastões de caminhada, alarmes de mordida, kits de irrigação por '
               'gotejamento e outros itens leves. Em produtos para uso ao ar livre, confira o material e o peso, o '
               'comprimento dobrado e se o anúncio vende uma unidade ou um par. Meça antes o diâmetro de mangueiras, varas '
               'ou conexões: a peça só fica firme quando essas medidas coincidem. Se o item funciona com bateria, veja como '
               'ela é carregada e se o cabo vem na caixa.'),
        'es': ('Equipo para el jardín, la pesca y las caminatas: bastones de senderismo, alarmas de picada, kits de riego por '
               'goteo y otros artículos ligeros. En los productos para exteriores revisa el material y el peso, la longitud '
               'plegada y si el anuncio vende una pieza o un par. Mide antes el diámetro de mangueras, cañas o conectores: '
               'la pieza solo queda firme cuando esas medidas coinciden. Si el artículo usa batería, fíjate en cómo se carga '
               'y si el cable viene en la caja.'),
        'fr': ('Du matériel pour le jardin, la pêche et la randonnée : bâtons de marche, détecteurs de touche, kits '
               'd’arrosage goutte à goutte et autres équipements légers. Pour un article d’extérieur, vérifiez la matière '
               'et le poids, la longueur repliée et si l’annonce vend une pièce ou une paire. Mesurez à l’avance le '
               'diamètre de vos tuyaux, cannes ou raccords : une pièce ne tient bien que si ces cotes correspondent. Si '
               'l’article fonctionne sur batterie, regardez comment il se recharge et si le câble est fourni.'),
        'he': ('ציוד לגינה, לדיג ולטיולים: מקלות הליכה, מתריעי נגיסה, ערכות השקיה בטפטוף ופריטים קלים נוספים. במוצרים '
               'לשטח כדאי לבדוק את החומר והמשקל, את האורך במצב מקופל ואם המודעה מוכרת יחידה אחת או זוג. מדדו מראש את '
               'הקוטר של צינורות, חכות או מחברים: רק כשהמידות תואמות החלק יחזיק היטב. אם הפריט עובד על סוללה, בדקו איך '
               'היא נטענת ואם הכבל כלול באריזה.'),
    },
}
CATEGORY_LONG_HEADING = {
    'ru': '{name}: что проверить перед заказом',
    'en': '{name}: what to check before ordering',
    'pt': '{name}: o que verificar antes de comprar',
    'es': '{name}: qué revisar antes de pedir',
    'fr': '{name} : ce qu’il faut vérifier avant de commander',
    'he': '{name}: מה לבדוק לפני ההזמנה',
}

# The full English catalog at /en/. The English front page at '/' carries the drop, the carousel and the
# category bands, so /en/ opens straight with the complete list instead of repeating them.
CATALOG_EN = {
    'h1': 'The full FLUXIXO catalog',
    'intro': ('Every find on FLUXIXO in one list. Search by name or filter by category; each card opens a short '
              'product page with photos and a link to the seller on AliExpress.'),
}

# Product pages link to the buying guides written about them (journal_pages: preferred_product).
GUIDES_HEADING = {
    'ru': 'Памятки по теме',
    'en': 'Buying guides for this item',
    'pt': 'Guias de compra para este item',
    'es': 'Guías de compra para este artículo',
    'fr': 'Guides d’achat pour cet article',
    'he': 'מדריכי קנייה למוצר הזה',
}
# The Russian pre-order checklist fits every electronic or tool item, not just its preferred product.
RU_CHECKLIST_GUIDE = 'pre-order-checklist-aliexpress'
RU_CHECKLIST_WORLDS = ('Техника', 'Инструменты', 'В дороге')
