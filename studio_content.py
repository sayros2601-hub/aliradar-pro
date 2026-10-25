"""Concise editorial labels; original listing titles and metadata remain intact."""
LABELS = {
 'en':dict(shop='View on AliExpress',details='Explore the object',quick='Quick view',collection='Find your everyday.',collection_sub='For your space, your work and everything in between.',search='What are you looking for?',price_note='Price and delivery depend on the variant and destination. Check the final total on AliExpress.',price_status='Current price at the seller',image_open='Enlarge photo',image_close='Close photo',image_zoom='Zoom photo',image_note='The listing photograph',object_label='THE OBJECT / DEALVAULT',about='About this find',before='Before you buy',related='Your next discovery',back='All discoveries',full_title='Original listing name'),
 'ru':dict(shop='На AliExpress',details='Рассмотреть находку',quick='Быстрый просмотр',collection='Найдите своё.',collection_sub='Для дома, работы и всего, что между ними.',search='Что хотите найти?',price_note='Цена и доставка зависят от варианта товара и страны. Проверьте итог на AliExpress.',price_status='Актуальная цена — у продавца',image_open='Увеличить фото',image_close='Закрыть фото',image_zoom='Масштаб фотографии',image_note='Фотография из предложения продавца',object_label='НАХОДКА / DEALVAULT',about='Об этой находке',before='Перед покупкой',related='Следующее открытие',back='Все находки',full_title='Название у продавца'),
 'he':dict(shop='ל-AliExpress',details='גלו את הפריט',quick='מבט מהיר',collection='מצאו את שלכם.',collection_sub='לבית, לעבודה ולכל מה שביניהם.',search='מה תרצו למצוא?',price_note='המחיר והמשלוח תלויים בדגם וביעד. בדקו את הסכום הסופי ב-AliExpress.',price_status='מחיר עדכני אצל המוכר',image_open='הגדלת התמונה',image_close='סגירת התמונה',image_zoom='זום לתמונה',image_note='תמונת המוצר של המוכר',object_label='הפריט / DEALVAULT',about='על הפריט',before='לפני הרכישה',related='הגילוי הבא שלכם',back='כל הפריטים',full_title='השם אצל המוכר'),
 'es':dict(shop='Ver en AliExpress',details='Explorar el objeto',quick='Vista rápida',collection='Encuentra lo tuyo.',collection_sub='Para tu espacio, tu trabajo y todo lo demás.',search='¿Qué quieres encontrar?',price_note='El precio y el envío dependen de la variante y del destino. Comprueba el total en AliExpress.',price_status='Precio actual en el vendedor',image_open='Ampliar foto',image_close='Cerrar foto',image_zoom='Zoom de la foto',image_note='Fotografía del anuncio',object_label='EL OBJETO / DEALVAULT',about='Sobre este hallazgo',before='Antes de comprar',related='Tu próximo descubrimiento',back='Todos los hallazgos',full_title='Nombre del anuncio')
}
_TITLES = {
 'mini-pocket-wireless-thermal-printer': ['Pocket thermal printer','Карманный термопринтер','מדפסת תרמית לכיס','Impresora térmica de bolsillo'],
 'magnetic-levitating-3d-moon-lamp': ['The floating moon lamp','Парящая луна','מנורת ירח מרחפת','Lámpara de luna flotante'],
 'smart-touch-coffee-mug-warmer': ['A warmer for your favourite cup','Подогреватель для любимой чашки','מחמם לספל האהוב','Calentador para tu taza favorita'],
 'electric-makeup-brush-cleaner-dryer': ['Electric makeup brush cleaner','Электроочиститель кистей','מנקה חשמלי למברשות איפור','Limpiador eléctrico de brochas'],
 'foldable-3in1-magnetic-wireless-charger': ['Foldable 3-in-1 charging station','Складная зарядная станция 3-в-1','עמדת טעינה מתקפלת 3 ב-1','Estación de carga plegable 3 en 1'],
 'ultra-quiet-smart-pet-water-fountain': ['A drinking fountain for pets','Поилка-фонтан для питомцев','מזרקת שתייה לחיות מחמד','Fuente de agua para mascotas'],
 'cordless-handheld-car-vacuum-cleaner': ['Cordless handheld vacuum','Компактный беспроводной пылесос','שואב אבק ידני אלחוטי','Aspiradora de mano inalámbrica']
}
def display_titles(product):
    values=_TITLES.get(product['id'])
    return dict(zip(('en','ru','he','es'),values)) if values else product['title_i18n']

def display_title(product,lang):
    return display_titles(product).get(lang,product['title_i18n'].get(lang,''))
