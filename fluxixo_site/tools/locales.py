"""Localized catalog and product pages share the showroom's translation data."""
from html import escape as e
from pathlib import PurePosixPath
import json
import re

LANGUAGES = {
    'ru': ('ru', 'ru_RU', 'Русский', 'Каталог', '3D-витрина', 'Посмотреть на AliExpress', 'Исходное фото продавца'),
    'en': ('en', 'en_US', 'English', 'Catalog', '3D Showroom', 'Open on AliExpress', 'Original seller photo'),
    'pt': ('pt-BR', 'pt_BR', 'Português (Brasil)', 'Catálogo', 'Vitrine 3D', 'Ver no AliExpress', 'Foto original do vendedor'),
    'es': ('es-MX', 'es_MX', 'Español (México)', 'Catálogo', 'Vitrina 3D', 'Ver en AliExpress', 'Foto original del vendedor'),
    'fr': ('fr', 'fr_FR', 'Français', 'Catalogue', 'Vitrine 3D', 'Voir sur AliExpress', 'Photo originale du vendeur'),
    'he': ('he-IL', 'he_IL', 'עברית', 'קטלוג', 'תצוגת 3D', 'למוצר ב־AliExpress', 'תמונת המוכר המקורית'),
}

SHORT_LABELS = {
    'en': 'EN · Eng',
    'ru': 'RU · Рус',
    'pt': 'PT · Bra',
    'es': 'ES · Méx',
    'fr': 'FR · Fra',
    'he': 'HE · עבר',
}

INTRO = {
    'en': 'Browse our curated collection of gadgets, home and kitchen tools, travel gear, and pet finds. Inspect studio cutouts, compare with seller photos, and open listings directly on AliExpress.',
    'pt': 'Conheça nossa seleção de eletrônicos, utensílios para casa e cozinha, itens de viagem e pets. Compare os visuais de estúdio com as fotos do vendedor e veja no AliExpress.',
    'es': 'Explora nuestra selección de tecnología, artículos para el hogar y la cocina, accesorios de viaje y mascotas. Compara las imágenes de estudio con las fotos del vendedor en AliExpress.',
    'fr': 'Découvrez notre sélection de gadgets, d’articles pour la maison et la cuisine, et d’accessoires de voyage. Comparez nos visuels studio aux photos des vendeurs sur AliExpress.',
    'he': 'גלו מבחר גאדג׳טים, כלים לבית ולמטבח, אביזרים לנסיעות ומוצרים לחיות מחמד. השוו בין תמונת הסטודיו לתמונת המוכר ופתחו את המוצר ב־AliExpress.',
}

DISCLOSURE = {
    'ru': 'По партнёрским ссылкам FLUXIXO может получить комиссию. Актуальную цену, модификацию и условия доставки уточняйте на странице продавца на AliExpress.',
    'en': 'We may earn a commission through affiliate links at no extra cost to you. Check the current price, option, and shipping details with the seller on AliExpress.',
    'pt': 'Podemos receber uma comissão por links de afiliados sem custo adicional. Confira o preço atual, a variação e o frete com o vendedor no AliExpress.',
    'es': 'Podemos recibir una comisión por enlaces de afiliados sin costo extra para ti. Consulta el precio actual, el modelo y el envío con el vendedor en AliExpress.',
    'fr': 'Nous pouvons percevoir une commission via les liens affiliés sans frais supplémentaires. Vérifiez le prix, le modèle et la livraison auprès du vendeur sur AliExpress.',
    'he': 'אנחנו עשויים לקבל עמלה מרכישות דרך קישורי שותפים ללא עלות נוספת עבורכם. בדקו את המחיר, הדגם וזמינות המשלוח אצל המוכר ב־AliExpress.',
}

RELATED_HEADING = {
    'ru': 'Похожие находки в коллекции',
    'en': 'More finds in this category',
    'pt': 'Mais achados nesta categoria',
    'es': 'Más hallazgos en esta categoría',
    'fr': 'Autres trouvailles dans cette catégorie',
    'he': 'מוצרים נוספים בקטגוריה זו',
}

STAGE_CAPTION = {
    'ru': 'Студийная визуализация FLUXIXO · проверьте комплектацию у продавца',
    'en': 'FLUXIXO studio visualization · verify options on the seller listing',
    'pt': 'Visualização de estúdio FLUXIXO · confira as opções no anúncio',
    'es': 'Visualización de estudio FLUXIXO · verifica las opciones con el vendedor',
    'fr': 'Visuel studio FLUXIXO · vérifiez les options sur la fiche vendeur',
    'he': 'הדמיית סטודיו של FLUXIXO · בדקו את הדגם והמפרט בעמוד המוכר',
}

BREADCRUMB_ARIA = {
    'ru': 'Навигационная цепочка',
    'en': 'Breadcrumb',
    'pt': 'Trilha de navegação',
    'es': 'Ruta de navegación',
    'fr': 'Fil d’Ariane',
    'he': 'ניווט',
}

# Longest suffix that still fits the 60-character title budget wins.
TITLE_SUFFIXES = {
    'ru': (' — купить на AliExpress | FLUXIXO', ' на AliExpress | FLUXIXO', ' | FLUXIXO'),
    'en': (' on AliExpress | FLUXIXO', ' | FLUXIXO'),
    'pt': (' no AliExpress Brasil | FLUXIXO', ' no AliExpress | FLUXIXO', ' | FLUXIXO'),
    'es': (' en AliExpress México | FLUXIXO', ' en AliExpress | FLUXIXO', ' | FLUXIXO'),
    'fr': (' sur AliExpress | FLUXIXO', ' | FLUXIXO'),
    'he': (' ב־AliExpress | FLUXIXO', ' | FLUXIXO'),
}

# Instructions only: the site holds no verified price, stock or delivery data.
DESCRIPTION_CTA = {
    'ru': 'Фото продавца, цена и доставка — на AliExpress.',
    'en': 'See seller photos, current price and shipping on AliExpress.',
    'pt': 'Veja fotos do vendedor, preço e frete para o Brasil no AliExpress.',
    'es': 'Consulta fotos del vendedor, precio y envío a México en AliExpress.',
    'fr': 'Photos du vendeur, prix et livraison sur AliExpress.',
    'he': 'תמונות המוכר, המחיר והמשלוח ב־AliExpress.',
}

CATALOG_TITLE = {
    'ru': 'Находки с AliExpress: техника, дом и кухня | FLUXIXO',
    'en': 'AliExpress Finds: Gadgets, Home & Travel | FLUXIXO',
    'pt': 'Achadinhos AliExpress Brasil: gadgets e casa | FLUXIXO',
    'es': 'Hallazgos AliExpress México: gadgets y hogar | FLUXIXO',
    'fr': 'Trouvailles AliExpress : high-tech et maison | FLUXIXO',
    'he': 'מציאות מ־AliExpress: גאדג׳טים ולבית | FLUXIXO',
}

CATALOG_DESCRIPTION = {
    'en': 'Curated AliExpress finds: gadgets, home, kitchen, travel and pet products with photos and direct links. Check price and shipping with the seller.',
    'pt': 'Achados do AliExpress para o Brasil: tecnologia, casa, cozinha, viagem e pets, com fotos e links diretos. Confira preço e frete com o vendedor.',
    'es': 'Hallazgos de AliExpress para México: tecnología, hogar, cocina, viajes y mascotas, con fotos y enlaces directos. Consulta precio y envío con el vendedor.',
    'fr': 'Trouvailles AliExpress : high-tech, maison, cuisine, voyage et animaux, avec photos et liens directs. Vérifiez prix et livraison auprès du vendeur.',
    'he': 'מציאות מ־AliExpress: גאדג׳טים, בית, מטבח, נסיעות וחיות מחמד, עם תמונות וקישורים ישירים. בדקו מחיר ומשלוח אצל המוכר.',
}

CATEGORY_TITLE = {
    'ru': '{cat}: находки с AliExpress | FLUXIXO',
    'en': '{cat} Finds on AliExpress | FLUXIXO',
    'pt': '{cat}: achadinhos no AliExpress | FLUXIXO',
    'es': '{cat}: hallazgos en AliExpress | FLUXIXO',
    'fr': '{cat} : trouvailles AliExpress | FLUXIXO',
    'he': '{cat}: מציאות מ־AliExpress | FLUXIXO',
}

CATEGORY_COUNT = {
    'ru': '{n} находок с фото и ссылками на AliExpress.',
    'en': '{n} finds with photos and AliExpress links.',
    'pt': '{n} achados com fotos e links para o AliExpress.',
    'es': '{n} hallazgos con fotos y enlaces a AliExpress.',
    'fr': '{n} trouvailles avec photos et liens AliExpress.',
    'he': '{n} מוצרים עם תמונות וקישורים ל־AliExpress.',
}

CATEGORY_ALIASES = {'Для питомцев': 'Питомцы'}

CATEGORY_SLUGS = {
    'Техника': {'ru': 'tehnika', 'en': 'tech', 'pt': 'tecnologia', 'es': 'tecnologia', 'fr': 'high-tech', 'he': 'tech'},
    'Дом': {'ru': 'dom', 'en': 'home', 'pt': 'casa', 'es': 'hogar', 'fr': 'maison', 'he': 'home'},
    'Кухня': {'ru': 'kuhnya', 'en': 'kitchen', 'pt': 'cozinha', 'es': 'cocina', 'fr': 'cuisine', 'he': 'kitchen'},
    'В дороге': {'ru': 'v-doroge', 'en': 'auto-travel', 'pt': 'automotivo-viagem', 'es': 'auto-viaje', 'fr': 'auto-mobilite', 'he': 'auto-travel'},
    'Инструменты': {'ru': 'instrumenty', 'en': 'tools', 'pt': 'ferramentas', 'es': 'herramientas', 'fr': 'outils', 'he': 'tools'},
    'Уход': {'ru': 'uhod', 'en': 'beauty-care', 'pt': 'cuidados-pessoais', 'es': 'cuidado-personal', 'fr': 'beaute-soin', 'he': 'beauty-care'},
    'Спорт': {'ru': 'sport', 'en': 'sports', 'pt': 'esporte', 'es': 'deporte', 'fr': 'sport', 'he': 'sports'},
    'На природе': {'ru': 'na-prirode', 'en': 'outdoors', 'pt': 'ar-livre', 'es': 'aire-libre', 'fr': 'plein-air', 'he': 'outdoors'},
    'Питомцы': {'ru': 'pitomcy', 'en': 'pets', 'pt': 'pets', 'es': 'mascotas', 'fr': 'animaux', 'he': 'pets'},
}

CATEGORY_COPY = {
    'Техника': {
        'en': 'Gadgets, electronics and smart accessories for home and work.',
        'pt': 'Eletrônicos, gadgets e acessórios inteligentes para casa e trabalho.',
        'es': 'Gadgets, electrónica y accesorios inteligentes para la casa y el trabajo.',
        'fr': 'Gadgets, électronique et accessoires connectés pour la maison et le travail.',
        'he': 'גאדג׳טים, אלקטרוניקה ואביזרים חכמים לבית ולעבודה.',
    },
    'Дом': {
        'en': 'Practical devices, lighting and useful finds for a tidy, comfortable home.',
        'pt': 'Aparelhos práticos, iluminação e achados úteis para organizar a casa.',
        'es': 'Aparatos prácticos, iluminación y hallazgos útiles para el orden del hogar.',
        'fr': 'Appareils pratiques, éclairage et trouvailles utiles pour une maison bien rangée.',
        'he': 'מכשירים שימושיים, תאורה ומציאות לבית מסודר ונעים.',
    },
    'Кухня': {
        'en': 'Cooking gadgets, vacuum sealers and drink accessories.',
        'pt': 'Utensílios de cozinha, seladoras a vácuo e acessórios para bebidas.',
        'es': 'Utensilios de cocina, selladoras al vacío y accesorios para bebidas.',
        'fr': 'Ustensiles de cuisine, machines sous vide et accessoires pour boissons.',
        'he': 'גאדג׳טים לבישול, מכונות ואקום ואביזרים למשקאות.',
    },
    'В дороге': {
        'en': 'Car accessories, travel gadgets and gear for the road.',
        'pt': 'Acessórios automotivos, gadgets de viagem e itens para a estrada.',
        'es': 'Accesorios para auto, gadgets de viaje y equipo para el camino.',
        'fr': 'Accessoires auto, gadgets de voyage et équipement pour la route.',
        'he': 'אביזרים לרכב, גאדג׳טים לנסיעות וציוד לדרך.',
    },
    'Инструменты': {
        'en': 'Laser measures, soldering irons, detectors and compact power tools.',
        'pt': 'Medidores a laser, ferros de solda, detectores e ferramentas compactas.',
        'es': 'Medidores láser, cautines, detectores y herramientas eléctricas compactas.',
        'fr': 'Télémètres laser, fers à souder, détecteurs et outils électriques compacts.',
        'he': 'מדי לייזר, מלחמים, גלאים וכלי עבודה חשמליים קומפקטיים.',
    },
    'Уход': {
        'en': 'Personal care devices, sanitizers, stylers and massagers.',
        'pt': 'Aparelhos de cuidados pessoais, esterilizadores, modeladores e massageadores.',
        'es': 'Aparatos de cuidado personal, esterilizadores, moldeadores y masajeadores.',
        'fr': 'Appareils de soin, stérilisateurs, coiffants et masseurs.',
        'he': 'מכשירי טיפוח, מחטאים, מעצבי שיער ומכשירי עיסוי.',
    },
    'Спорт': {
        'en': 'Exercise gear, bike accessories and equipment for home workouts.',
        'pt': 'Equipamentos de treino, acessórios para bicicleta e itens para treinar em casa.',
        'es': 'Equipo de ejercicio, accesorios para bici y artículos para entrenar en casa.',
        'fr': 'Matériel de fitness, accessoires vélo et équipement pour s’entraîner chez soi.',
        'he': 'ציוד כושר, אביזרים לאופניים ומוצרים לאימון בבית.',
    },
    'На природе': {
        'en': 'Gear for camping, fishing, hiking and outdoor days.',
        'pt': 'Equipamentos para camping, pesca, trilhas e atividades ao ar livre.',
        'es': 'Equipo para acampar, pescar, hacer senderismo y disfrutar al aire libre.',
        'fr': 'Équipement pour le camping, la pêche, la randonnée et le plein air.',
        'he': 'ציוד לקמפינג, דיג, טיולים ופעילות בחוץ.',
    },
    'Питомцы': {
        'en': 'Automatic toys, trackers and accessories for dogs and cats.',
        'pt': 'Brinquedos automáticos, rastreadores e acessórios para cães e gatos.',
        'es': 'Juguetes automáticos, rastreadores y accesorios para perros y gatos.',
        'fr': 'Jouets automatiques, traceurs et accessoires pour chiens et chats.',
        'he': 'צעצועים אוטומטיים, מכשירי מעקב ואביזרים לכלבים ולחתולים.',
    },
}

ABOUT = {
    'ru': {
        'nav': 'О проекте',
        'title': 'О проекте и конфиденциальность | FLUXIXO',
        'desc': 'Что такое FLUXIXO, как устроены партнёрские ссылки на AliExpress и какие данные использует сайт.',
        'h1': 'О проекте FLUXIXO',
        'sections': [
            ('what', 'Что такое FLUXIXO', 'FLUXIXO — независимая подборка полезных товаров с AliExpress. Мы не магазин и не представляем AliExpress: заказ, оплата, доставка и возврат оформляются на AliExpress у выбранного продавца.'),
            ('images', 'Как готовятся карточки', 'Студийные изображения созданы с помощью ИИ на основе фотографий продавца, поэтому на странице товара можно открыть исходное фото и сравнить. Мы не тестируем каждый товар лично и не публикуем цены и рейтинги: они часто меняются, актуальные условия смотрите у продавца.'),
            ('affiliate', 'Партнёрские ссылки', 'Ссылки на AliExpress партнёрские. Если вы совершите покупку, FLUXIXO может получить комиссию; цена для вас при этом не меняется.'),
            ('privacy', 'Конфиденциальность', 'На сайте нет регистрации, форм и рекламных cookie. Посещаемость считается через Cloudflare Web Analytics в обобщённом виде, без cookie. В памяти вашего браузера сохраняются только выбранный язык и настройка анимации. После перехода на AliExpress действует политика конфиденциальности AliExpress.'),
            ('orders', 'Вопросы по заказам', 'По вопросам заказа, доставки и возврата обращайтесь к продавцу через свой аккаунт AliExpress. FLUXIXO не обрабатывает заказы и платежи.'),
        ],
    },
    'en': {
        'nav': 'About',
        'title': 'About & Privacy | FLUXIXO',
        'desc': 'What FLUXIXO is, how its AliExpress affiliate links work, and what data the site uses.',
        'h1': 'About FLUXIXO',
        'sections': [
            ('what', 'What FLUXIXO is', 'FLUXIXO is an independent selection of useful products listed on AliExpress. We are not a store and do not represent AliExpress: orders, payment, delivery and returns are handled on AliExpress by the seller you choose.'),
            ('images', 'How listings are prepared', 'Studio images are created with AI from seller photos, so every product page lets you open the original photo and compare. We do not personally test each product and do not publish prices or ratings because they change often; check current terms with the seller.'),
            ('affiliate', 'Affiliate links', 'Links to AliExpress are affiliate links. If you make a purchase, FLUXIXO may earn a commission at no extra cost to you.'),
            ('privacy', 'Privacy', 'The site has no sign-up, no forms and no advertising cookies. Visits are counted in aggregate with Cloudflare Web Analytics, without cookies. Your browser stores only your language and motion preference. Once you open AliExpress, the AliExpress privacy policy applies.'),
            ('orders', 'Order questions', 'For orders, delivery and returns, contact the seller through your AliExpress account. FLUXIXO does not process orders or payments.'),
        ],
    },
    'pt': {
        'nav': 'Sobre',
        'title': 'Sobre e privacidade | FLUXIXO',
        'desc': 'O que é a FLUXIXO, como funcionam os links de afiliados do AliExpress e quais dados o site usa.',
        'h1': 'Sobre a FLUXIXO',
        'sections': [
            ('what', 'O que é a FLUXIXO', 'A FLUXIXO é uma seleção independente de produtos úteis anunciados no AliExpress. Não somos uma loja e não representamos o AliExpress: pedido, pagamento, entrega e devolução são feitos no AliExpress com o vendedor escolhido.'),
            ('images', 'Como preparamos os produtos', 'As imagens de estúdio são criadas com IA a partir das fotos do vendedor, por isso cada página permite abrir a foto original e comparar. Não testamos pessoalmente cada produto e não publicamos preços ou avaliações, pois mudam com frequência; confira as condições atuais com o vendedor.'),
            ('affiliate', 'Links de afiliados', 'Os links para o AliExpress são de afiliados. Se você fizer uma compra, a FLUXIXO pode receber uma comissão sem custo adicional para você.'),
            ('privacy', 'Privacidade', 'O site não tem cadastro, formulários nem cookies de publicidade. As visitas são contadas de forma agregada com o Cloudflare Web Analytics, sem cookies. Seu navegador guarda apenas o idioma e a preferência de animação. Ao abrir o AliExpress, vale a política de privacidade do AliExpress.'),
            ('orders', 'Dúvidas sobre pedidos', 'Para pedidos, entrega e devolução, fale com o vendedor pela sua conta do AliExpress. A FLUXIXO não processa pedidos nem pagamentos.'),
        ],
    },
    'es': {
        'nav': 'Acerca de',
        'title': 'Acerca de y privacidad | FLUXIXO',
        'desc': 'Qué es FLUXIXO, cómo funcionan sus enlaces de afiliados de AliExpress y qué datos usa el sitio.',
        'h1': 'Acerca de FLUXIXO',
        'sections': [
            ('what', 'Qué es FLUXIXO', 'FLUXIXO es una selección independiente de productos útiles publicados en AliExpress. No somos una tienda ni representamos a AliExpress: el pedido, el pago, la entrega y las devoluciones se realizan en AliExpress con el vendedor que elijas.'),
            ('images', 'Cómo preparamos las fichas', 'Las imágenes de estudio se crean con IA a partir de las fotos del vendedor, por eso en cada producto puedes abrir la foto original y comparar. No probamos personalmente cada producto ni publicamos precios o calificaciones, porque cambian con frecuencia; consulta las condiciones actuales con el vendedor.'),
            ('affiliate', 'Enlaces de afiliados', 'Los enlaces a AliExpress son de afiliados. Si realizas una compra, FLUXIXO puede recibir una comisión sin costo extra para ti.'),
            ('privacy', 'Privacidad', 'El sitio no tiene registro, formularios ni cookies publicitarias. Las visitas se cuentan de forma agregada con Cloudflare Web Analytics, sin cookies. Tu navegador guarda solo el idioma y la preferencia de animación. Al abrir AliExpress, se aplica la política de privacidad de AliExpress.'),
            ('orders', 'Dudas sobre pedidos', 'Para pedidos, entregas y devoluciones, contacta al vendedor desde tu cuenta de AliExpress. FLUXIXO no procesa pedidos ni pagos.'),
        ],
    },
    'fr': {
        'nav': 'À propos',
        'title': 'À propos et confidentialité | FLUXIXO',
        'desc': 'Ce qu’est FLUXIXO, le fonctionnement de ses liens affiliés AliExpress et les données utilisées par le site.',
        'h1': 'À propos de FLUXIXO',
        'sections': [
            ('what', 'Qu’est-ce que FLUXIXO', 'FLUXIXO est une sélection indépendante de produits utiles proposés sur AliExpress. Nous ne sommes pas une boutique et ne représentons pas AliExpress : commande, paiement, livraison et retours se font sur AliExpress auprès du vendeur choisi.'),
            ('images', 'Comment les fiches sont préparées', 'Les visuels studio sont créés par IA à partir des photos du vendeur : chaque fiche permet donc d’ouvrir la photo d’origine pour comparer. Nous ne testons pas personnellement chaque produit et ne publions ni prix ni notes, car ils changent souvent ; vérifiez les conditions actuelles auprès du vendeur.'),
            ('affiliate', 'Liens affiliés', 'Les liens vers AliExpress sont des liens affiliés. Si vous effectuez un achat, FLUXIXO peut percevoir une commission sans frais supplémentaires pour vous.'),
            ('privacy', 'Confidentialité', 'Le site n’a ni inscription, ni formulaire, ni cookie publicitaire. Les visites sont comptées de façon agrégée avec Cloudflare Web Analytics, sans cookie. Votre navigateur enregistre uniquement la langue et la préférence d’animation. Une fois sur AliExpress, la politique de confidentialité d’AliExpress s’applique.'),
            ('orders', 'Questions sur les commandes', 'Pour les commandes, la livraison et les retours, contactez le vendeur depuis votre compte AliExpress. FLUXIXO ne traite ni commandes ni paiements.'),
        ],
    },
    'he': {
        'nav': 'אודות',
        'title': 'אודות ופרטיות | FLUXIXO',
        'desc': 'מה זה FLUXIXO, איך עובדים קישורי השותפים ל־AliExpress ובאילו נתונים האתר משתמש.',
        'h1': 'אודות FLUXIXO',
        'sections': [
            ('what', 'מה זה FLUXIXO', 'FLUXIXO היא מבחר עצמאי של מוצרים שימושיים המוצעים ב־AliExpress. איננו חנות ואיננו מייצגים את AliExpress: ההזמנה, התשלום, המשלוח וההחזרות מתבצעים ב־AliExpress מול המוכר שבחרתם.'),
            ('images', 'איך מכינים את דפי המוצרים', 'תמונות הסטודיו נוצרות בעזרת בינה מלאכותית מתמונות המוכר, ולכן בכל דף מוצר אפשר לפתוח את התמונה המקורית ולהשוות. איננו בודקים כל מוצר בעצמנו ואיננו מפרסמים מחירים או דירוגים כי הם משתנים לעתים קרובות; בדקו את התנאים העדכניים אצל המוכר.'),
            ('affiliate', 'קישורי שותפים', 'הקישורים ל־AliExpress הם קישורי שותפים. אם תבצעו רכישה, FLUXIXO עשויה לקבל עמלה ללא עלות נוספת עבורכם.'),
            ('privacy', 'פרטיות', 'באתר אין הרשמה, טפסים או עוגיות פרסום. הביקורים נספרים באופן מצטבר באמצעות Cloudflare Web Analytics, ללא עוגיות. הדפדפן שלכם שומר רק את השפה ואת העדפת האנימציה. לאחר המעבר ל־AliExpress חלה מדיניות הפרטיות של AliExpress.'),
            ('orders', 'שאלות על הזמנות', 'בנושאי הזמנות, משלוחים והחזרות פנו למוכר דרך חשבון ה־AliExpress שלכם. FLUXIXO אינה מטפלת בהזמנות או בתשלומים.'),
        ],
    },
}

# Editorial source notes kept in the catalog data; never shown to visitors.
INTERNAL_FACT_LABELS = {'Подборка'}

# Filled by the build from the real files, so srcset and structured data state true dimensions.
IMAGE_SIZES = {}
DEFAULT_IMAGE_SIZE = (1254, 1254)


def public_facts(product):
    return [fact for fact in product.get('facts', []) if fact.get('label') not in INTERNAL_FACT_LABELS]


def thumb(image, width=480):
    return f'assets/thumbs/{PurePosixPath(image).stem}-{width}.webp'


def transition_name(image):
    # Shared by a product's card and its page hero so the browser can morph one into the other.
    return 'p-' + re.sub(r'[^a-z0-9-]', '-', PurePosixPath(image).stem.lower())


def card_image(image, alt, index=99, width=400, height=300):
    priority = 'fetchpriority="high"' if index == 0 else ('loading="eager"' if index < 3 else 'loading="lazy"')
    return (f'<img src="/{e(thumb(image))}" alt="{e(alt)}" {priority} decoding="async" width="{width}" height="{height}" '
            f'style="view-transition-name:{transition_name(image)}">')


def sticky_cta(link):
    return f'<div class="sticky-cta">{link}</div>' if link.startswith('<a ') else ''


def hero_image(image, alt):
    width, height = IMAGE_SIZES.get(image, DEFAULT_IMAGE_SIZE)
    candidates = ', '.join(f'/{e(path)} {IMAGE_SIZES[path][0]}w'
                           for path in (thumb(image), thumb(image, 800), image) if path in IMAGE_SIZES)
    return (f'<img class="hero-image" src="/{e(image)}" srcset="{candidates}" '
            f'sizes="(max-width:900px) 86vw, 560px" alt="{e(alt)}" width="{width}" height="{height}" '
            f'fetchpriority="high" decoding="async" style="view-transition-name:{transition_name(image)}">')


def fit_title(name, language, limit=60):
    suffixes = TITLE_SUFFIXES[language]
    for suffix in suffixes:
        if len(name) + len(suffix) <= limit:
            return name + suffix
    return name + suffixes[-1]


def fit_description(text, language, limit=158):
    text = text.strip()
    if not text.endswith(('.', '!', '?', '…')):
        text += '.'
    full = f'{text} {DESCRIPTION_CTA[language]}'
    if len(full) <= limit:
        return full
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(' ', 1)[0].rstrip(' ,;:—-') + '…'


def item_page_schema(origin, path, title, description, image, language, caption, crumbs):
    width, height = IMAGE_SIZES.get(image, DEFAULT_IMAGE_SIZE)
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'ItemPage',
                '@id': origin + path,
                'url': origin + path,
                'name': title,
                'description': description,
                'inLanguage': LANGUAGES[language][0],
                'isPartOf': {'@type': 'WebSite', 'name': 'FLUXIXO', 'url': origin + '/'},
                'primaryImageOfPage': {
                    '@type': 'ImageObject',
                    'url': origin + '/' + image,
                    'contentUrl': origin + '/' + image,
                    'width': width,
                    'height': height,
                    'caption': caption,
                },
            },
            {
                '@type': 'BreadcrumbList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': index + 1, 'name': name, 'item': origin + target}
                    for index, (name, target) in enumerate(crumbs)
                ],
            },
        ],
    }


def category_key(name):
    key = CATEGORY_ALIASES.get(name, name)
    return key if key in CATEGORY_SLUGS else None


def category_path(key, language):
    slug = CATEGORY_SLUGS[key][language]
    return f'/categories/{slug}/' if language == 'ru' else f'/{language}/categories/{slug}/'


def category_paths(key):
    return {language: category_path(key, language) for language in LANGUAGES}


def about_path(language):
    return '/about/' if language == 'ru' else f'/{language}/about/'


def catalog_path(language):
    return '/catalog/' if language == 'ru' else f'/{language}/'


def product_path(product, language):
    prefix = '' if language == 'ru' else f'/{language}'
    return f"{prefix}/products/{product['id']}/"


def alternates(origin, paths):
    tags = [
        f'<link rel="alternate" hreflang="{LANGUAGES[language][0]}" href="{origin}{path}">'
        for language, path in paths.items()
    ]
    # Spanish and Portuguese speakers outside Mexico and Brazil get these pages instead of the English fallback.
    tags += [f'<link rel="alternate" hreflang="{language}" href="{origin}{paths[language]}">'
             for language in ('es', 'pt') if language in paths]
    if 'en' in paths:
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{origin}{paths["en"]}">')
    return '\n'.join(tags)


def language_links(paths):
    return '<nav class="locale-links" aria-label="Language">' + ''.join(
        f'<a class="button secondary" href="{path}" lang="{LANGUAGES[language][0]}" dir="auto">{LANGUAGES[language][2]}</a>'
        for language, path in paths.items()
    ) + '</nav>'


def header_lang_select(current_lang, alternate_paths=None):
    paths = alternate_paths or {lang: catalog_path(lang) for lang in LANGUAGES}
    options = []
    for lang in ('en', 'ru', 'pt', 'es', 'fr', 'he'):
        target = paths.get(lang, catalog_path(lang))
        sel = ' selected' if lang == current_lang else ''
        options.append(f'<option value="{e(target)}" data-lang="{lang}"{sel}>{e(SHORT_LABELS[lang])}</option>')
    return f'<select class="lang-select" aria-label="Language">{"".join(options)}</select>'


def translations(data, product):
    return {language: value for language, value in data['products'].get(product['id'], {}).items()
            if language in LANGUAGES and language != 'ru' and all(value.get(key) for key in ('name', 'headline', 'description'))}


def translate_fact(data, text, language):
    if language == 'ru' or not text:
        return text
    return data.get('facts', {}).get(text, {}).get(language) or data.get('cats', {}).get(text, {}).get(language) or text


def sync_showroom(dist, data):
    file = dist/'js/i18n.js'
    script = file.read_text(encoding='utf-8')
    for constant, key in [('UI', 'ui'), ('CATS', 'cats'), ('FACTS', 'facts'), ('PRODUCTS', 'products')]:
        if key not in data:
            continue
        pattern = rf'(  const {constant} = )\{{.*?\n\}};'
        script, count = re.subn(pattern, lambda m: m[1] + json.dumps(data[key], ensure_ascii=False, indent=2) + ';',
                                script, count=1, flags=re.S)
        if count != 1:
            raise ValueError(f'Missing {constant} dictionary in i18n.js')
    file.write_text(script, encoding='utf-8', newline='\n')


def generate_about(page, write):
    paths = {language: about_path(language) for language in LANGUAGES}
    for language, path in paths.items():
        copy = ABOUT[language]
        sections = ''.join(
            f'<section id="{anchor}"><h2>{e(heading)}</h2><p>{e(text)}</p></section>'
            for anchor, heading, text in copy['sections']
        )
        body = f'<article class="about-page"><h1>{e(copy["h1"])}</h1>{sections}</article>{language_links(paths)}'
        write(path.strip('/') + '/index.html', page(copy['title'], copy['desc'], path, body, language=language, alternate_paths=paths))
    return list(paths.values())


def generate(origin, data, products, page, write, image):
    catalogs = {language: catalog_path(language) for language in LANGUAGES}
    routes = []
    for language, (_, _, _, catalog_label, showroom, ali, seller_photo) in LANGUAGES.items():
        if language == 'ru':
            continue
        catalog = catalogs[language]
        ui = data['ui'][language]
        links = language_links(catalogs)
        listed = []
        for product in products:
            translated = translations(data, product).get(language)
            if not translated:
                continue
            paths = {key: product_path(product, key) for key in ('ru', *translations(data, product))}
            path = paths[language]
            routes.append(path)
            name, desc = translated['name'], translated['description']
            headline = ' '.join(translated.get('headline', []))
            cat = data['cats'].get(product['category'], {}).get(language, product['category'])
            key = category_key(product['category'])
            studio = f"/?lang={language}#{product['id']}"
            listed.append((product, name, desc, cat, path, key))
            buy = (f'<a class="button" href="{e(product["affiliateUrl"])}" target="_blank" rel="sponsored noopener"><span>{e(ali)}</span><span aria-hidden="true">↗</span></a>'
                   if product['affiliateUrl'] and not product.get('pendingLink') else f'<p class="muted">{e(ui["ctaPending"])}</p>')
            facts_html = ''.join(
                f'<dt>{e(translate_fact(data, f["label"], language))}</dt><dd>{e(translate_fact(data, f["value"], language))}</dd>'
                for f in public_facts(product)
            )
            dl_block = f'<dl class="specs-grid">{facts_html}</dl>' if facts_html else ''
            original = (
                f'<details class="source-details"><summary>{e(seller_photo)}</summary>'
                f'<img src="/{e(product["original"])}" alt="{e(name)}" loading="lazy" width="460" height="420">'
                f'<p>{e(ui["sourceNote"])}</p></details>'
                if product.get('original') else ''
            )
            # Related products in the same category (localized)
            same_cat = [other for other in products if other['id'] != product['id'] and other['category'] == product['category']]
            if len(same_cat) < 4:
                others = [other for other in products if other['id'] != product['id'] and other not in same_cat]
                same_cat.extend(others[:4 - len(same_cat)])
            rel_cards = []
            for r in same_cat[:4]:
                r_tr = translations(data, r).get(language, {})
                r_name = r_tr.get('name', r['name'])
                r_desc = r_tr.get('description', r['description'])
                r_cat = data['cats'].get(r['category'], {}).get(language, r['category'])
                r_path = product_path(r, language)
                rel_cards.append(
                    f'<li><a class="card" href="{r_path}">'
                    f'<div class="card-visual">{card_image(r["image"], r_name, width=300, height=225)}</div>'
                    f'<p class="eyebrow">{e(r_cat)}</p><h3>{e(r_name)}</h3><p>{e(r_desc)}</p></a></li>'
                )
            related_block = f'<section class="related"><h2>{e(RELATED_HEADING[language])}</h2><ul class="grid">{"".join(rel_cards)}</ul></section>'

            cat_href = category_path(key, language) if key else None
            cat_crumb = (f'<span class="breadcrumb-sep">/</span><a href="{cat_href}">{e(cat)}</a>' if cat_href else '')
            cat_label = f'<a href="{cat_href}">{e(cat)}</a>' if cat_href else e(cat)
            body = (
                f'<nav class="breadcrumb" aria-label="{e(BREADCRUMB_ARIA[language])}"><a href="/?lang={language}">FLUXIXO</a><span class="breadcrumb-sep">/</span><a href="{catalog}">{e(catalog_label)}</a>{cat_crumb}</nav>'
                f'<article><div class="product">'
                f'<figure class="arcade-stage-card">{hero_image(product["image"], name)}<div class="stage-podium-bar" aria-hidden="true"></div>'
                f'<figcaption>{e(STAGE_CAPTION[language])}</figcaption></figure>'
                f'<section><p class="eyebrow">{cat_label}</p><h1>{e(name)}</h1>'
                f'<p class="product-headline-sub">{e(headline)}</p><p>{e(desc)}</p>'
                f'<div class="cta-row">{buy}<a class="button secondary" href="{studio}">{e(showroom)}</a></div>'
                f'<p class="affiliate-disclosure">{e(ui["affiliateNote"])}</p>'
                f'{dl_block}</section></div>{original}{related_block}</article>{language_links(paths)}{sticky_cta(buy)}'
            )
            title = fit_title(name, language)
            description = fit_description(desc, language)
            crumbs = [('FLUXIXO', '/'), (catalog_label, catalog)]
            if cat_href:
                crumbs.append((cat, cat_href))
            crumbs.append((name, path))
            schema = item_page_schema(origin, path, title, description, product['image'], language, f'{name} — {desc}', crumbs)
            write(path.strip('/')+'/index.html', page(title, description, path, body, schema,
                  product['image'], language=language, alternate_paths=paths, studio_url=studio, theme=product.get('theme')))
        if not listed:
            continue

        def cards(rows, heading='h2'):
            return ''.join(
                f'<li><a class="card" href="{path}">'
                f'<div class="card-visual">{card_image(product["image"], name, index)}</div>'
                f'<p class="eyebrow">{e(cat)}</p><{heading}>{e(name)}</{heading}><p>{e(desc)}</p></a></li>'
                for index, (product, name, desc, cat, path, _) in enumerate(rows)
            )

        groups = {}
        for row in listed:
            if row[5]:
                groups.setdefault(row[5], []).append(row)
        cat_bar = '<div class="cat-links">' + ''.join(
            f'<a class="button secondary" href="{category_path(key, language)}">{e(data["cats"].get(key, {}).get(language, key))} ({len(rows)})</a>'
            for key, rows in groups.items()
        ) + '</div>'

        for key, rows in groups.items():
            cat = data['cats'].get(key, {}).get(language, key)
            path = category_path(key, language)
            count = CATEGORY_COUNT[language].format(n=len(rows))
            intro = f'{CATEGORY_COPY[key][language]} {count}'
            listing = {
                '@context': 'https://schema.org',
                '@type': 'ItemList',
                'name': f'{cat} — FLUXIXO',
                'numberOfItems': len(rows),
                'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': origin + row[4], 'name': row[1]} for i, row in enumerate(rows)],
            }
            hub = (
                f'<nav class="breadcrumb" aria-label="{e(BREADCRUMB_ARIA[language])}"><a href="/?lang={language}">FLUXIXO</a><span class="breadcrumb-sep">/</span><a href="{catalog}">{e(catalog_label)}</a><span class="breadcrumb-sep">/</span><span>{e(cat)}</span></nav>'
                f'<p class="eyebrow">{e(ui["brandLine"])}</p><h1>{e(cat)} ({len(rows)})</h1><p>{e(intro)}</p>{cat_bar}<ul class="grid">{cards(rows)}</ul>{language_links(category_paths(key))}'
            )
            write(path.strip('/')+'/index.html', page(CATEGORY_TITLE[language].format(cat=cat), intro, path, hub, listing, rows[0][0]['image'],
                  language=language, alternate_paths=category_paths(key)))
            routes.append(path)

        body = f'<p class="eyebrow">{e(ui["brandLine"])}</p><h1>{e(catalog_label)} FLUXIXO ({len(listed)})</h1><p>{e(INTRO[language])}</p>{cat_bar}<ul class="grid">{cards(listed)}</ul>{links}'
        write(catalog.strip('/')+'/index.html', page(CATALOG_TITLE[language], CATALOG_DESCRIPTION[language], catalog, body, image=image,
              language=language, alternate_paths=catalogs))
        routes.append(catalog)
    return routes
