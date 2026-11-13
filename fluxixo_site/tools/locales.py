"""Localized catalog and product pages share the showroom's translation data."""
from html import escape as e
from pathlib import Path, PurePosixPath
import json
import re
import market_seo

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
    'en': 'Browse our curated collection of gadgets, home and kitchen tools, travel gear, and pet finds. Inspect studio visuals, compare with seller photos, and open listings directly on AliExpress.',
    'pt': 'Conheça nossa seleção de eletrônicos, utensílios para casa e cozinha, itens de viagem e pets. Compare as imagens de estúdio com as fotos do vendedor e veja no AliExpress.',
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
    'he': 'אנחנו עשויים לקבל עמלה מרכישות דרך קישורי שותפים, ללא תוספת תשלום מבחינתכם. בדקו את המחיר, הדגם ותנאי המשלוח אצל המוכר ב־AliExpress.',
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
    'he': 'הדמיית סטודיו של FLUXIXO · בדקו את הדגם והמפרט בעמוד המוצר',
}

BREADCRUMB_ARIA = {
    'ru': 'Навигационная цепочка',
    'en': 'Breadcrumb',
    'pt': 'Trilha de navegação',
    'es': 'Ruta de navegación',
    'fr': 'Fil d’Ariane',
    'he': 'נתיב ניווט',
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
    'he': 'ראו תמונות מקור, מחיר ותנאי משלוח ב־AliExpress.',
}

CATALOG_TITLE = {
    'ru': 'Находки с AliExpress: техника, дом и кухня | FLUXIXO',
    'en': 'AliExpress Finds: Gadgets, Home & Travel | FLUXIXO',
    'pt': 'Achadinhos AliExpress Brasil: gadgets e casa | FLUXIXO',
    'es': 'Hallazgos AliExpress México: gadgets y hogar | FLUXIXO',
    'fr': 'Trouvailles AliExpress : high-tech et maison | FLUXIXO',
    'he': 'מציאות מ־AliExpress: גאדג׳טים, בית וטיולים | FLUXIXO',
}

CATALOG_DESCRIPTION = {
    'en': 'Curated AliExpress finds: gadgets, home, kitchen, travel and pet products with photos and direct links. Check price and shipping with the seller.',
    'pt': 'Achados do AliExpress para o Brasil: tecnologia, casa, cozinha, viagem e pets, com fotos e links diretos. Confira preço e frete com o vendedor.',
    'es': 'Hallazgos de AliExpress para México: tecnología, hogar, cocina, viajes y mascotas, con fotos y enlaces directos. Consulta precio y envío con el vendedor.',
    'fr': 'Trouvailles AliExpress : high-tech, maison, cuisine, voyage et animaux, avec photos et liens directs. Vérifiez prix et livraison auprès du vendeur.',
    'he': 'מציאות מ־AliExpress: גאדג׳טים, בית, מטבח, רכב, נסיעות וחיות מחמד, עם תמונות וקישורים ישירים. בדקו מחיר ותנאי משלוח אצל המוכר.',
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
        'pt': 'Itens práticos, iluminação e achados úteis para organizar a casa.',
        'es': 'Aparatos prácticos, iluminación y hallazgos útiles para el orden del hogar.',
        'fr': 'Appareils pratiques, éclairage et trouvailles utiles pour une maison bien rangée.',
        'he': 'גאדג׳טים שימושיים, תאורה ופתרונות סדר לבית.',
    },
    'Кухня': {
        'en': 'Cooking gadgets, vacuum sealers and drink accessories.',
        'pt': 'Utensílios de cozinha, seladoras a vácuo e acessórios para bebidas.',
        'es': 'Utensilios de cocina, selladoras al vacío y accesorios para bebidas.',
        'fr': 'Ustensiles de cuisine, machines sous vide et accessoires pour boissons.',
        'he': 'גאדג׳טים למטבח, איטום בוואקום ואביזרים למשקאות ולקפה.',
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
        'he': 'מכשירי טיפוח, חיטוי UV, מעצבי שיער ומכשירי עיסוי.',
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
            ('images', 'Как готовятся карточки', 'Студийные изображения мы выделяем с помощью ИИ из фотографий продавца: только сам товар, без фона и надписей. Все фото и комплектацию продавца смотрите на AliExpress. Мы не тестируем каждый товар лично и не публикуем цены и рейтинги: они часто меняются, актуальные условия смотрите у продавца.'),
            ('affiliate', 'Партнёрские ссылки', 'Ссылки на AliExpress партнёрские. Если вы совершите покупку, FLUXIXO может получить комиссию; цена для вас при этом не меняется.'),
            ('privacy', 'Конфиденциальность', 'На сайте нет регистрации, форм и рекламных cookie. Посещаемость считается через Cloudflare Web Analytics в обезличенном агрегированном виде, без cookie. На русскоязычных страницах дополнительно работает Яндекс Метрика: она ставит собственные cookie и записывает обезличенные действия на странице (клики, прокрутку), эти данные обрабатывает Яндекс по своей политике конфиденциальности. Сам сайт сохраняет в памяти вашего браузера только выбранный язык и настройку анимации. После перехода на AliExpress действует политика конфиденциальности AliExpress.'),
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
            ('images', 'How listings are prepared', 'Studio images are isolated with AI from seller photos: just the product, without background or text. See all seller photos and the exact set on AliExpress. We do not personally test each product and do not publish prices or ratings because they change often; check current terms with the seller.'),
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
            ('images', 'Como preparamos os produtos', 'As imagens de estúdio são isoladas com IA a partir das fotos do vendedor: só o produto, sem fundo nem textos. Veja todas as fotos e o que vem na caixa no AliExpress. Não testamos pessoalmente cada produto e não publicamos preços ou avaliações, pois mudam com frequência; confira as condições atuais com o vendedor.'),
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
            ('images', 'Cómo preparamos las fichas', 'Las imágenes de estudio se aíslan con IA a partir de las fotos del vendedor: solo el producto, sin fondo ni textos. Consulta todas las fotos y lo que incluye en AliExpress. No probamos personalmente cada producto ni publicamos precios o calificaciones, porque cambian con frecuencia; consulta las condiciones actuales con el vendedor.'),
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
            ('images', 'Comment les fiches sont préparées', 'Les visuels studio sont détourés par IA à partir des photos du vendeur : seulement le produit, sans fond ni texte. Toutes les photos et le contenu exact sont sur AliExpress. Nous ne testons pas personnellement chaque produit et ne publions ni prix ni notes, car ils changent souvent ; vérifiez les conditions actuelles auprès du vendeur.'),
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
            ('what', 'מה זה FLUXIXO', 'FLUXIXO מציגה מבחר עצמאי של מוצרים שימושיים המוצעים ב־AliExpress. איננו חנות ואיננו מייצגים את AliExpress: ההזמנה, התשלום, המשלוח וההחזרות מתבצעים ב־AliExpress מול המוכר שבחרתם.'),
            ('images', 'איך מכינים את דפי המוצרים', 'תמונות הסטודיו מעובדות בעזרת בינה מלאכותית מתוך תמונות המוכר — רק המוצר נטו, בלי רקע ובלי כיתובים. את כל התמונות ותכולת הערכה בדקו ב־AliExpress. איננו בודקים כל מוצר בעצמנו ואיננו מפרסמים מחירים או דירוגים כי הם משתנים לעיתים קרובות; בדקו את התנאים העדכניים אצל המוכר.'),
            ('affiliate', 'קישורי שותפים', 'הקישורים ל־AliExpress הם קישורי שותפים. אם תבצעו רכישה, FLUXIXO עשויה לקבל עמלה ללא תוספת תשלום עבורכם.'),
            ('privacy', 'פרטיות', 'באתר אין הרשמה, טפסים או עוגיות פרסום. נתוני הגלישה נאספים באופן אנונימי ומרוכז באמצעות Cloudflare Web Analytics, ללא עוגיות. הדפדפן שלכם שומר רק את השפה ואת העדפת האנימציה. לאחר המעבר ל־AliExpress חלה מדיניות הפרטיות של AliExpress.'),
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
    cands = [f'/{e(path)} {IMAGE_SIZES[path][0]}w' for path in (thumb(image), thumb(image, 800)) if path in IMAGE_SIZES]
    srcset = f' srcset="{", ".join(cands)}" sizes="(max-width:640px) 92vw, 300px"' if cands else ''
    return (f'<img src="/{e(thumb(image))}"{srcset} alt="{e(alt)}" {priority} decoding="async" width="{width}" height="{height}" '
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


def resolve_image_size(dist, image_rel):
    """Resolve true image dimensions from cache or disk so subprocess builds never stall on default bounds."""
    if image_rel in IMAGE_SIZES:
        return IMAGE_SIZES[image_rel]
    if dist:
        target = Path(dist) / image_rel
        if target.exists():
            try:
                from PIL import Image
                with Image.open(target) as im:
                    IMAGE_SIZES[image_rel] = im.size
                    return im.size
            except (OSError, ImportError):
                pass
    return DEFAULT_IMAGE_SIZE


def editorial_image_alt(product_name, category_label, lang, *, role='hero', view_index=1, total_views=1):
    """Unique, check_texts-safe alt copy per slot without repeating bare strings across images."""
    name = ' '.join(str(product_name or '').split())
    cat = ' '.join(str(category_label or '').split())
    templates = {
        'ru': {
            'hero': f'{name} — студийное фото FLUXIXO, {cat}' if cat else f'{name} — студийное фото FLUXIXO',
            'view': (
                f'{name} — ракурс {view_index} из {total_views}, FLUXIXO'
                if total_views > 1
                else (f'{name} — ракурс {view_index}, FLUXIXO' if view_index > 1 else f'{name} — дополнительный ракурс FLUXIXO')
            ),
            'card': f'{name} — {cat}, карточка FLUXIXO' if cat else f'{name} — карточка FLUXIXO',
            'spotlight': f'{name} — находка дня FLUXIXO',
            'rope': f'{name} — свежая находка FLUXIXO',
            'mini': f'{name} — миниатюра, {cat}' if cat else f'{name} — миниатюра FLUXIXO',
            'original': f'{name} — исходное фото продавца для сравнения',
        },
        'en': {
            'hero': f'{name} — FLUXIXO studio visual, {cat}' if cat else f'{name} — FLUXIXO studio visual',
            'view': f'{name} — studio angle {view_index} of {total_views}' if total_views > 1 else f'{name} — studio angle {view_index}',
            'card': f'{name} — {cat} preview on FLUXIXO' if cat else f'{name} — studio preview',
            'spotlight': f'{name} — featured {cat} find on FLUXIXO' if cat else f'{name} — featured FLUXIXO find',
            'rope': f'{name} — latest FLUXIXO showcase find',
            'mini': f'{name} — {cat} thumbnail' if cat else f'{name} — thumbnail',
            'original': f'{name} — original seller listing photo',
        },
        'pt': {
            'hero': f'{name} — imagem de estúdio FLUXIXO, {cat}' if cat else f'{name} — imagem de estúdio FLUXIXO',
            'view': f'{name} — ângulo {view_index} de {total_views} no estúdio' if total_views > 1 else f'{name} — ângulo {view_index} no estúdio',
            'card': f'{name} — prévia de {cat} na FLUXIXO' if cat else f'{name} — prévia de estúdio',
            'spotlight': f'{name} — destaque de {cat} na FLUXIXO' if cat else f'{name} — destaque FLUXIXO',
            'rope': f'{name} — achado recente FLUXIXO',
            'mini': f'{name} — miniatura de {cat}' if cat else f'{name} — miniatura',
            'original': f'{name} — foto original do vendedor para comparação',
        },
        'es': {
            'hero': f'{name} — imagen de estudio FLUXIXO, {cat}' if cat else f'{name} — imagen de estudio FLUXIXO',
            'view': f'{name} — vista {view_index} de {total_views} en estudio' if total_views > 1 else f'{name} — vista {view_index} en estudio',
            'card': f'{name} — vista de {cat} en FLUXIXO' if cat else f'{name} — vista de estudio',
            'spotlight': f'{name} — hallazgo destacado de {cat}' if cat else f'{name} — hallazgo destacado',
            'rope': f'{name} — hallazgo reciente en FLUXIXO',
            'mini': f'{name} — miniatura de {cat}' if cat else f'{name} — miniatura',
            'original': f'{name} — foto original del vendedor para comparar',
        },
        'fr': {
            'hero': f'{name} — visuel studio FLUXIXO, {cat}' if cat else f'{name} — visuel studio FLUXIXO',
            'view': f'{name} — angle {view_index} sur {total_views} en studio' if total_views > 1 else f'{name} — angle {view_index} en studio',
            'card': f'{name} — aperçu {cat} sur FLUXIXO' if cat else f'{name} — aperçu studio',
            'spotlight': f'{name} — sélection du jour {cat}' if cat else f'{name} — sélection du jour',
            'rope': f'{name} — nouveauté sélectionnée sur FLUXIXO',
            'mini': f'{name} — vignette {cat}' if cat else f'{name} — vignette',
            'original': f'{name} — photo originale du vendeur pour comparaison',
        },
        'he': {
            'hero': f'{name} — תמונת סטודיו FLUXIXO, {cat}' if cat else f'{name} — תמונת סטודיו FLUXIXO',
            'view': (
                f'{name} — זווית {view_index} מתוך {total_views}, FLUXIXO'
                if total_views > 1
                else (f'{name} — זווית {view_index} בתצוגת FLUXIXO' if view_index > 1 else f'{name} — זווית נוספת בתצוגת FLUXIXO')
            ),
            'card': f'{name} — {cat}, תצוגה מקדימה ב־FLUXIXO' if cat else f'{name} — תצוגה מקדימה ב־FLUXIXO',
            'spotlight': f'{name} — המוצר הבולט של היום ב־FLUXIXO',
            'rope': f'{name} — מציאה חדשה ב־FLUXIXO',
            'mini': f'{name} — תקריב, {cat}' if cat else f'{name} — תקריב ב־FLUXIXO',
            'original': f'{name} — תמונת המוכר המקורית להשוואה',
        },
    }
    table = templates.get(lang, templates['en'])
    return table.get(role, table['hero'])


def editorial_image_caption(product_name, category_label, lang, *, role='hero', view_index=1, total_views=1):
    """Per-product caption for Schema.org ImageObject instead of static boilerplate."""
    alt = editorial_image_alt(product_name, category_label, lang, role=role, view_index=view_index, total_views=total_views)
    suffix = {
        'ru': 'проверьте комплектацию у продавца',
        'en': 'verify variant options on the seller listing',
        'pt': 'confira a variação no anúncio do vendedor',
        'es': 'revisa las opciones en la ficha del vendedor',
        'fr': 'vérifiez les options sur la fiche vendeur',
        'he': 'בדקו את הדגם והערכה בעמוד המוצר',
    }.get(lang, 'verify variant options on the seller listing')
    return f'{alt} · {suffix}'


def build_image_object(origin, image_rel, *, name, caption, size, thumb_rel=None, representative=True):
    """Compliant Schema.org ImageObject without Product/Offer or partial Image License triggers."""
    obj = {
        '@type': 'ImageObject',
        '@id': f'{origin}/{image_rel}#image',
        'url': f'{origin}/{image_rel}',
        'contentUrl': f'{origin}/{image_rel}',
        'name': name,
        'caption': caption,
        'encodingFormat': 'image/webp',
        'width': size[0],
        'height': size[1],
        'representativeOfPage': representative,
    }
    if thumb_rel:
        obj['thumbnailUrl'] = f'{origin}/{thumb_rel}'
    return obj


def item_page_schema(origin, path, title, description, image, language, caption, crumbs,
                     *, extra_images=None, image_name=None, dist_root=None):
    width, height = resolve_image_size(dist_root, image)
    thumb_rel = thumb(image) if dist_root and (Path(dist_root) / thumb(image)).exists() else None
    primary = build_image_object(
        origin, image,
        name=image_name or caption or title,
        caption=caption,
        size=(width, height),
        thumb_rel=thumb_rel,
        representative=True,
    )
    item_node = {
        '@type': 'ItemPage',
        '@id': origin + path,
        'url': origin + path,
        'name': title,
        'description': description,
        'inLanguage': LANGUAGES[language][0],
        'isPartOf': {'@type': 'WebSite', 'name': 'FLUXIXO', 'url': origin + '/'},
        'primaryImageOfPage': primary,
    }
    if extra_images:
        media = []
        for idx, rel in enumerate(extra_images, 2):
            if rel and rel != image:
                sz = resolve_image_size(dist_root, rel)
                media.append(build_image_object(
                    origin, rel,
                    name=f'{image_name or title} ({idx})',
                    caption=f'{caption} ({idx})',
                    size=sz,
                    representative=False,
                ))
        if media:
            item_node['associatedMedia'] = media
    return {
        '@context': 'https://schema.org',
        '@graph': [
            item_node,
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
    return market_seo.full_alternates(origin, paths)


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
    overrides = market_seo.load_overrides()
    dist_dir = Path(__file__).resolve().parents[1] / 'dist'
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
                f'<img src="/{e(product["original"])}" alt="{e(editorial_image_alt(name, cat, language, role="original"))}" loading="lazy" width="460" height="420">'
                f'<p>{e(ui["sourceNote"])}</p></details>'
                if product.get('original') else ''
            )
            ov = market_seo.route_override(overrides, path)
            title = ov.get('title') or fit_title(name, language)
            description = ov.get('description') or fit_description(desc, language)
            chk_html = market_seo.market_checklist_html(key, language)
            faq_html, faq_schema = market_seo.faq_section_and_schema(name, key, language, ov)
            vid_html, vid_schema = market_seo.video_block_and_schema(origin, dist_dir, product, name, description, language, product['image'])
            # Rotating peer selection across the category ensures every product gets contextual internal links
            same_cat = [other for other in products if other['id'] != product['id'] and other['category'] == product['category']]
            rel_cards = []
            for r in market_seo.rotating_related(products, product, same_cat, limit=4):
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
                f'<figure class="arcade-stage-card">{hero_image(product["image"], editorial_image_alt(name, cat, language, role="hero"))}<div class="stage-podium-bar" aria-hidden="true"></div>'
                f'<figcaption>{e(editorial_image_caption(name, cat, language))}</figcaption></figure>'
                f'<section><p class="eyebrow">{cat_label}</p><h1>{e(name)}</h1>'
                f'<p class="product-headline-sub">{e(headline)}</p><p>{e(desc)}</p>'
                f'<div class="cta-row">{buy}<a class="button secondary" href="{studio}">{e(showroom)}</a></div>'
                f'<p class="affiliate-disclosure">{e(ui["affiliateNote"])}</p>'
                f'{dl_block}</section></div>{vid_html}{chk_html}{faq_html}{original}{related_block}</article>{language_links(paths)}{sticky_cta(buy)}'
            )
            crumbs = [('FLUXIXO', '/'), (catalog_label, catalog)]
            if cat_href:
                crumbs.append((cat, cat_href))
            crumbs.append((name, path))
            schema = item_page_schema(
                origin, path, title, description, product['image'], language,
                editorial_image_caption(name, cat, language), crumbs,
                extra_images=product.get('views'), image_name=name, dist_root=dist_dir,
            )
            if faq_schema:
                schema['@graph'].append(faq_schema)
            if vid_schema:
                schema['@graph'].append(vid_schema)
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
            ov = market_seo.route_override(overrides, path)
            cat_title = ov.get('title') or CATEGORY_TITLE[language].format(cat=cat)
            cat_desc = ov.get('description') or intro
            cat_crumbs = [('FLUXIXO', '/'), (catalog_label, catalog), (cat, path)]
            listing = market_seo.collection_schema(origin, path, cat_title, cat_desc, LANGUAGES[language][0], [(row[4], row[1]) for row in rows], cat_crumbs)
            hub = (
                f'<nav class="breadcrumb" aria-label="{e(BREADCRUMB_ARIA[language])}"><a href="/?lang={language}">FLUXIXO</a><span class="breadcrumb-sep">/</span><a href="{catalog}">{e(catalog_label)}</a><span class="breadcrumb-sep">/</span><span>{e(cat)}</span></nav>'
                f'<p class="eyebrow">{e(ui["brandLine"])}</p><h1>{e(cat)} ({len(rows)})</h1><p>{e(intro)}</p>{cat_bar}<ul class="grid">{cards(rows)}</ul>{language_links(category_paths(key))}'
            )
            write(path.strip('/')+'/index.html', page(cat_title, cat_desc, path, hub, listing, rows[0][0]['image'],
                  language=language, alternate_paths=category_paths(key)))
            routes.append(path)

        ov_cat = market_seo.route_override(overrides, catalog)
        cat_hub_title = ov_cat.get('title') or CATALOG_TITLE[language]
        cat_hub_desc = ov_cat.get('description') or CATALOG_DESCRIPTION[language]
        hub_crumbs = [('FLUXIXO', '/'), (catalog_label, catalog)]
        hub_schema = market_seo.collection_schema(origin, catalog, cat_hub_title, cat_hub_desc, LANGUAGES[language][0], [(row[4], row[1]) for row in listed], hub_crumbs)
        journal_href = f'/{language}/journal/'
        journal_label = {'en': 'Buying Guides', 'pt': 'Guias de Compra', 'es': 'Guías de Compra', 'fr': 'Guides d’Achat', 'he': 'מדריכי קנייה'}[language]
        cat_nav_bar = cat_bar.replace('</div>', f'<a class="button" href="{journal_href}">{e(journal_label)}</a></div>', 1)
        body = f'<p class="eyebrow">{e(ui["brandLine"])}</p><h1>{e(catalog_label)} FLUXIXO ({len(listed)})</h1><p>{e(INTRO[language])}</p>{cat_nav_bar}<ul class="grid">{cards(listed)}</ul>{links}'
        write(catalog.strip('/')+'/index.html', page(cat_hub_title, cat_hub_desc, catalog, body, schema=hub_schema, image=image,
              language=language, alternate_paths=catalogs))
        routes.append(catalog)
    return routes
