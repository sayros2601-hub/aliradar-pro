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
               drop='Drop del día', drop_old='Último drop', h1=('3 hallazgos nuevos.', 'Cada día.'),
               drop_text='Buscamos lo más raro y útil de AliExpress para que tú no pierdas el tiempo. Cada día colgamos tres novedades.',
               next_drop='Próximo drop', when=('hoy', 'mañana'), find_day='Hallazgo del día', seller='Foto real del vendedor',
               countdown_label='Próxima actualización', countdown_awaiting='Esperando actualización', countdown_schedule='Inicio previsto: cada día a las 19:00, hora de Israel',
               world='Mundo', enter='Ver todo', all=('Todos los', 'hallazgos'), filter_all='Todos',
               prev='Anterior', next='Siguiente', related=('Más de', 'este mundo'),
               home='Inicio', about='Acerca de', privacy='Privacidad',
               foot='Buscamos lo más raro y útil de AliExpress para que tú no tengas que hacerlo.',
               count='{n} hallazgos'.format, title='FLUXIXO · Drop diario de hallazgos de AliExpress',
               meta='Cada día 3 hallazgos nuevos de AliExpress para México: gadgets, hogar, cocina, auto y más, con fotos y enlaces directos.'),
    'pt': dict(tabs=('Início', 'Mundos', 'Catálogo', 'Buscar'), search='Buscar um achadinho…', nothing='Nada por aqui. Tente outra palavra.', language='Idioma', app='Achadinhos do AliExpress',
               cta='Quero esse!', more='Ver detalhes', nav=('Drop', 'Mundos', 'Catálogo'),
               drop='Drop do dia', drop_old='Último drop', h1=('3 achadinhos novos.', 'Todo dia.'),
               drop_text='A gente garimpa o que tem de mais curioso e útil no AliExpress. Todo dia entram três novidades no varal.',
               next_drop='Próximo drop', when=('hoje', 'amanhã'), find_day='Achadinho do dia', seller='Foto real do vendedor',
               countdown_label='Próxima atualização', countdown_awaiting='Aguardando atualização', countdown_schedule='Início previsto: todos os dias às 19h, horário de Israel',
               world='Mundo', enter='Ver tudo', all=('Todos os', 'achadinhos'), filter_all='Todos',
               prev='Anterior', next='Próximo', related=('Mais', 'deste mundo'),
               home='Início', about='Sobre', privacy='Privacidade',
               foot='A gente garimpa o AliExpress para você não precisar.',
               count='{n} achadinhos'.format, title='FLUXIXO · Drop diário de achadinhos do AliExpress',
               meta='Todo dia 3 achadinhos novos do AliExpress para o Brasil: gadgets, casa, cozinha, carro e mais, com fotos e links diretos.'),
    'en': dict(tabs=('Home', 'Worlds', 'Catalog', 'Search'), search='Search the finds…', nothing='Nothing here. Try another word.', language='Language', app='AliExpress finds',
               cta='I want it', more='See details', nav=('Drop', 'Worlds', 'Catalog'),
               drop="Today's drop", drop_old='Latest drop', h1=('3 new finds.', 'Every day.'),
               drop_text='We dig through AliExpress for the odd and the useful. Three new finds go up on the line every day.',
               next_drop='Next drop', when=('today', 'tomorrow'), find_day='Find of the day', seller='Real seller photo',
               countdown_label='Next update', countdown_awaiting='Awaiting update', countdown_schedule='Planned start: daily at 19:00 Israel time',
               world='World', enter='See all', all=('All', 'finds'), filter_all='All',
               prev='Previous', next='Next', related=('More from', 'this world'),
               home='Home', about='About', privacy='Privacy',
               foot="We dig through AliExpress so you don't have to.",
               count='{n} finds'.format, title='FLUXIXO · A daily drop of AliExpress finds',
               meta='Three new AliExpress finds every day: gadgets, home, kitchen, car gear and more, with photos and direct links.'),
    'fr': dict(tabs=('Accueil', 'Univers', 'Catalogue', 'Chercher'), search='Chercher une trouvaille…', nothing='Rien ici. Essayez un autre mot.', language='Langue', app='Trouvailles AliExpress',
               cta='Je le veux !', more='Voir la fiche', nav=('Drop', 'Univers', 'Catalogue'),
               drop='Drop du jour', drop_old='Dernier drop', h1=('3 nouvelles trouvailles.', 'Chaque jour.'),
               drop_text='On déniche sur AliExpress des objets malins et insolites. Chaque jour, trois nouveautés sont accrochées au fil.',
               next_drop='Prochain drop', when=('aujourd’hui', 'demain'), find_day='Trouvaille du jour', seller='Vraie photo du vendeur',
               countdown_label='Prochaine mise à jour', countdown_awaiting='Mise à jour en attente', countdown_schedule='Début prévu : chaque jour à 19 h, heure d’Israël',
               world='Univers', enter='Tout voir', all=('Les', 'trouvailles'), filter_all='Tout',
               prev='Précédent', next='Suivant', related=('Dans le', 'même univers'),
               home='Accueil', about='À propos', privacy='Confidentialité',
               foot='On fouille AliExpress pour vous éviter de le faire.',
               count='{n} trouvailles'.format, title='FLUXIXO · Le drop quotidien de trouvailles AliExpress',
               meta='Chaque jour 3 nouvelles trouvailles AliExpress : high-tech, maison, cuisine, auto et plus, avec photos et liens directs.'),
    'he': dict(tabs=('ראשי', 'עולמות', 'קטלוג', 'חיפוש'), search='חיפוש מציאה…', nothing='לא מצאנו כלום. נסו מילה אחרת.', language='שפה', app='מציאות מ־AliExpress',
               cta='רוצה את זה!', more='לפרטים', nav=('הדרופ', 'עולמות', 'קטלוג'),
               drop='הדרופ היומי', drop_old='הדרופ האחרון', h1=('3 מציאות חדשות.', 'כל יום.'),
               drop_text='אנחנו חופרים ב־AliExpress ושולפים משם את הדברים הכי שווים והכי מוזרים. כל יום נתלות על החבל שלוש מציאות חדשות.',
               next_drop='הדרופ הבא', when=('היום', 'מחר'), find_day='המציאה של היום', seller='תמונה אמיתית מהמוכר',
               countdown_label='העדכון הבא', countdown_awaiting='ממתינים לעדכון', countdown_schedule='תחילת העדכון מתוכננת בכל יום בשעה 19:00, שעון ישראל',
               world='עולם', enter='לכל המוצרים', all=('כל', 'המציאות'), filter_all='הכול',
               prev='הקודם', next='הבא', related=('עוד', 'מהעולם הזה'),
               home='ראשי', about='אודות', privacy='פרטיות',
               foot='אנחנו חופרים ב־AliExpress כדי שאתם לא תצטרכו.',
               count='{n} מציאות'.format, title='FLUXIXO · דרופ יומי של מציאות מ־AliExpress',
               meta='כל יום 3 מציאות חדשות מ־AliExpress: גאדג׳טים, בית, מטבח, רכב ועוד, עם תמונות וקישורים ישירים.'),
    'ru': dict(tabs=('Главная', 'Миры', 'Каталог', 'Поиск'), search='Найти находку…', nothing='Ничего не нашлось. Попробуйте другое слово.', language='Язык', app='Находки с AliExpress',
               cta='Хочу такой!', more='Подробнее', nav=('Дроп', 'Миры', 'Каталог'),
               drop='Дроп дня', drop_old='Свежий дроп', h1=('3 новые находки.', 'Каждый день.'),
               drop_text='Копаемся в AliExpress и вытаскиваем оттуда странное и полезное. Каждый день вешаем на верёвку три новинки.',
               next_drop='Следующий дроп', when=('сегодня', 'завтра'), find_day='Находка дня', seller='Настоящее фото продавца',
               countdown_label='Следующее обновление', countdown_awaiting='Ожидаем обновление', countdown_schedule='Плановый старт: ежедневно в 19:00 по времени Израиля',
               world='Мир', enter='Смотреть все', all=('Все находки ·', ''), filter_all='Все',
               prev='Назад', next='Дальше', related=('Ещё из', 'этого мира'),
               home='Главная', about='О проекте', privacy='Конфиденциальность',
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

# The home page at '/' is Russian: it is the page Yandex treats as the main page of the site, and the Russian
# section lives at the root (/products/, /categories/, /journal/). The other languages keep their own homes.
ROOT_RU = dict(
    title='FLUXIXO — находки с AliExpress: три новинки каждый день',
    desc=('FLUXIXO каждый день показывает три новые находки с AliExpress: техника, дом, кухня, авто и инструменты. '
          'Понятные описания на русском, студийные фото и прямые ссылки.'),
    h1=('Находки с AliExpress.', 'Три новые каждый день.'),
    fresh=('Свежие', 'находки'),
    all_btn='Весь каталог · {n}',
    guides='Памятки перед покупкой',
    about_h='Что такое FLUXIXO',
    about=('FLUXIXO — независимая витрина необычных и полезных вещей с AliExpress. Каждый день мы добавляем три новые '
           'находки: гаджеты, товары для дома и кухни, автоаксессуары, инструменты, вещи для спорта, ухода и питомцев. '
           'Сами мы ничего не продаём: кнопка в карточке ведёт на страницу продавца на AliExpress, где видны '
           'актуальная цена, варианты и условия доставки.',
           'У каждой находки есть короткое описание на русском, студийное изображение без фона и список того, что стоит '
           'проверить перед заказом: совместимость, размеры, питание и комплектацию. Так проще понять, подойдёт ли вещь '
           'именно вам, ещё до перехода к продавцу.'),
    how_h='Как пользоваться сайтом',
    how=('Начните с дропа дня вверху страницы, загляните в миры — так мы называем рубрики — или откройте весь каталог '
         'с поиском по названию. В разделе «Памятки» лежат короткие инструкции: как сравнить итоговую цену с доставкой, '
         'как выбрать усилитель Wi-Fi и автомобильный компрессор и что проверить перед любым заказом.'),
    langs_h='FLUXIXO на других языках',
)

# Headings of the extra buyer-advice block on Russian product pages (texts: tools/ru_long_copy.json).
MORE_RU = dict(who='Кому пригодится', check='Что проверить перед заказом')

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
