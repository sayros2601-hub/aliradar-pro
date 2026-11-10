"""Interface copy for the redesign. Voice: a friend who digs through AliExpress, in the words each market uses on the street
(Mexico "hallazgos", Brazil "achadinhos" and "garimpar", France "trouvailles/dénicher", Israel "מציאות", Russia "находки")."""


def ru_count(n):
    if n % 10 == 1 and n % 100 != 11:
        return f'{n} находка'
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f'{n} находки'
    return f'{n} находок'


UI = {
    'es': dict(cta='¡Lo quiero!', more='Ver detalles', nav=('Drop', 'Mundos', 'Catálogo'),
               drop='Drop del día', h1=('3 hallazgos nuevos.', 'Cada día.'),
               drop_text='Buscamos lo más raro y útil de AliExpress para que tú no pierdas el tiempo. Cada día colgamos tres novedades.',
               next_drop='Próximo drop', when=('hoy', 'mañana'), find_day='Hallazgo del día', seller='Foto real del vendedor',
               world='Mundo', enter='Ver todo', all=('Todos los', 'hallazgos'), filter_all='Todos',
               prev='Anterior', next='Siguiente', related=('Más de', 'este mundo'),
               home='Inicio', about='Acerca de', privacy='Privacidad', note='El precio, el modelo y el envío los ves al momento en AliExpress.',
               foot='Buscamos lo más raro y útil de AliExpress para que tú no tengas que hacerlo.',
               count='{n} hallazgos'.format, title='FLUXIXO · Drop diario de hallazgos de AliExpress',
               meta='Cada día 3 hallazgos nuevos de AliExpress para México: gadgets, hogar, cocina, auto y más, con fotos y enlaces directos.'),
    'pt': dict(cta='Quero esse!', more='Ver detalhes', nav=('Drop', 'Mundos', 'Catálogo'),
               drop='Drop do dia', h1=('3 achadinhos novos.', 'Todo dia.'),
               drop_text='A gente garimpa o que tem de mais curioso e útil no AliExpress. Todo dia entram três novidades no varal.',
               next_drop='Próximo drop', when=('hoje', 'amanhã'), find_day='Achadinho do dia', seller='Foto real do vendedor',
               world='Mundo', enter='Ver tudo', all=('Todos os', 'achadinhos'), filter_all='Todos',
               prev='Anterior', next='Próximo', related=('Mais', 'deste mundo'),
               home='Início', about='Sobre', privacy='Privacidade', note='Preço, modelo e frete você confere na hora no AliExpress.',
               foot='A gente garimpa o AliExpress para você não precisar.',
               count='{n} achadinhos'.format, title='FLUXIXO · Drop diário de achadinhos do AliExpress',
               meta='Todo dia 3 achadinhos novos do AliExpress para o Brasil: gadgets, casa, cozinha, carro e mais, com fotos e links diretos.'),
    'en': dict(cta='I want it', more='See details', nav=('Drop', 'Worlds', 'Catalog'),
               drop="Today's drop", h1=('3 new finds.', 'Every day.'),
               drop_text='We dig through AliExpress for the odd and the useful. Three new finds go up on the line every day.',
               next_drop='Next drop', when=('today', 'tomorrow'), find_day='Find of the day', seller='Real seller photo',
               world='World', enter='See all', all=('All', 'finds'), filter_all='All',
               prev='Previous', next='Next', related=('More from', 'this world'),
               home='Home', about='About', privacy='Privacy', note='Check the current price, option and shipping on AliExpress.',
               foot="We dig through AliExpress so you don't have to.",
               count='{n} finds'.format, title='FLUXIXO · A daily drop of AliExpress finds',
               meta='Three new AliExpress finds every day: gadgets, home, kitchen, car gear and more, with photos and direct links.'),
    'fr': dict(cta='Je le veux !', more='Voir la fiche', nav=('Drop', 'Univers', 'Catalogue'),
               drop='Drop du jour', h1=('3 nouvelles trouvailles.', 'Chaque jour.'),
               drop_text='On déniche sur AliExpress des objets malins et insolites. Chaque jour, trois nouveautés sont accrochées au fil.',
               next_drop='Prochain drop', when=('aujourd’hui', 'demain'), find_day='Trouvaille du jour', seller='Vraie photo du vendeur',
               world='Univers', enter='Tout voir', all=('Les', 'trouvailles'), filter_all='Tout',
               prev='Précédent', next='Suivant', related=('Dans le', 'même univers'),
               home='Accueil', about='À propos', privacy='Confidentialité', note='Prix, modèle et livraison à vérifier sur AliExpress.',
               foot='On fouille AliExpress pour vous éviter de le faire.',
               count='{n} trouvailles'.format, title='FLUXIXO · Le drop quotidien de trouvailles AliExpress',
               meta='Chaque jour 3 nouvelles trouvailles AliExpress : high-tech, maison, cuisine, auto et plus, avec photos et liens directs.'),
    'he': dict(cta='רוצה את זה!', more='לפרטים', nav=('הדרופ', 'עולמות', 'קטלוג'),
               drop='הדרופ היומי', h1=('3 מציאות חדשות.', 'כל יום.'),
               drop_text='אנחנו חופרים ב־AliExpress ושולפים משם את הדברים הכי שווים והכי מוזרים. כל יום נתלות על החבל שלוש מציאות חדשות.',
               next_drop='הדרופ הבא', when=('היום', 'מחר'), find_day='המציאה של היום', seller='תמונה אמיתית מהמוכר',
               world='עולם', enter='לכל המוצרים', all=('כל', 'המציאות'), filter_all='הכול',
               prev='הקודם', next='הבא', related=('עוד', 'מהעולם הזה'),
               home='ראשי', about='אודות', privacy='פרטיות', note='את המחיר, הדגם והמשלוח בודקים בעמוד המוצר ב־AliExpress.',
               foot='אנחנו חופרים ב־AliExpress כדי שאתם לא תצטרכו.',
               count='{n} מציאות'.format, title='FLUXIXO · דרופ יומי של מציאות מ־AliExpress',
               meta='כל יום 3 מציאות חדשות מ־AliExpress: גאדג׳טים, בית, מטבח, רכב ועוד, עם תמונות וקישורים ישירים.'),
    'ru': dict(cta='Хочу такой!', more='Подробнее', nav=('Дроп', 'Миры', 'Каталог'),
               drop='Дроп дня', h1=('3 новые находки.', 'Каждый день.'),
               drop_text='Копаемся в AliExpress и вытаскиваем оттуда странное и полезное. Каждый день вешаем на верёвку три новинки.',
               next_drop='Следующий дроп', when=('сегодня', 'завтра'), find_day='Находка дня', seller='Настоящее фото продавца',
               world='Мир', enter='Смотреть все', all=('Все находки ·', ''), filter_all='Все',
               prev='Назад', next='Дальше', related=('Ещё из', 'этого мира'),
               home='Главная', about='О проекте', privacy='Конфиденциальность', note='Цену, модель и доставку смотрите на AliExpress.',
               foot='Копаемся в AliExpress, чтобы вам не пришлось.',
               count=lambda n: ru_count(n), title='FLUXIXO · Каждый день новые находки с AliExpress',
               meta='Каждый день 3 новые находки с AliExpress: техника, дом, кухня, авто и не только. Фото и прямые ссылки.'),
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
