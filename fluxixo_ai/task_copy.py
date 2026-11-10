"""Brief, task-specific copy; product details must come from the seller."""

LANGS = ('ru', 'en', 'pt', 'es', 'fr', 'he')


def _translations(*sentences):
    return dict(zip(LANGS, sentences, strict=True))


TASK_COPY = {
    'inspection_mirror': _translations(
        'Зеркало для осмотра труднодоступных мест. Уточните размер зеркала и параметры выбранного варианта у продавца.',
        'A mirror for inspecting hard-to-see areas. Check the mirror size and the selected version with the seller.',
        'Espelho para inspecionar áreas difíceis de ver. Confira o tamanho do espelho e a versão escolhida com o vendedor.',
        'Espejo para inspeccionar zonas difíciles de ver. Consulta el tamaño del espejo y la variante elegida con el vendedor.',
        'Miroir pour inspecter les zones difficiles à voir. Vérifiez sa taille et la variante choisie auprès du vendeur.',
        'מראה לבדיקת מקומות שקשה לראות. יש לבדוק עם המוכר את גודל המראה ואת פרטי הדגם שנבחר.',
    ),
    'magnetic_pickup': _translations(
        'Для извлечения предметов, притягивающихся магнитом. Сверьте размеры и заявленную грузоподъёмность у продавца.',
        'For picking up objects attracted to a magnet. Check the size and stated lifting capacity with the seller.',
        'Para recolher objetos atraídos por ímã. Confira as dimensões e a capacidade de carga informada pelo vendedor.',
        'Para recoger objetos atraídos por un imán. Consulta las dimensiones y la capacidad de carga indicada por el vendedor.',
        'Pour ramasser les objets attirés par un aimant. Vérifiez les dimensions et la capacité de levage indiquées par le vendeur.',
        'לאיסוף פריטים הנמשכים למגנט. יש לבדוק עם המוכר את המידות ואת כושר ההרמה המוצהר.',
    ),
    'screw_extractor': _translations(
        'Экстрактор для извлечения повреждённых винтов. Проверьте диаметры, совместимость с инструментом и комплектацию у продавца.',
        'A screw extractor for removing damaged screws. Check the diameters, tool compatibility and included pieces with the seller.',
        'Extrator para remover parafusos danificados. Confira os diâmetros, a compatibilidade com a ferramenta e os itens incluídos.',
        'Extractor para retirar tornillos dañados. Comprueba los diámetros, la compatibilidad con la herramienta y el contenido.',
        'Extracteur pour retirer des vis abîmées. Vérifiez les diamètres, la compatibilité avec votre outil et le contenu auprès du vendeur.',
        'חולץ להוצאת ברגים פגומים. יש לבדוק עם המוכר קטרים, התאמה לכלי ואת תכולת המוצר.',
    ),
    'sewing_seam_guide': _translations(
        'Направитель помогает вести ткань вдоль линии шва. Сверьте совместимость со швейной машиной и способ крепления у продавца.',
        'A guide for keeping fabric aligned with the seam while sewing. Check machine compatibility and attachment with the seller.',
        'Guia para orientar o tecido ao longo da costura. Confira a compatibilidade com a máquina e a forma de fixação.',
        'Guía para orientar la tela a lo largo de la costura. Comprueba la compatibilidad con la máquina y la forma de fijación.',
        'Guide pour diriger le tissu le long de la couture. Vérifiez la compatibilité avec la machine et le mode de fixation.',
        'מכוון להובלת הבד לאורך קו התפר. יש לבדוק עם המוכר התאמה למכונת התפירה ואת אופן החיבור.',
    ),
    'watch_hand_tool': _translations(
        'Инструмент для установки стрелок часов. Сверьте размеры насадок, совместимость с часами и комплектацию у продавца.',
        'A tool for setting watch hands. Check tip sizes, watch compatibility and included pieces with the seller.',
        'Ferramenta para colocar ponteiros de relógio. Confira as medidas das pontas, a compatibilidade e os itens incluídos.',
        'Herramienta para colocar las agujas del reloj. Consulta las medidas de las puntas, la compatibilidad y el contenido.',
        'Outil pour poser les aiguilles d’une montre. Vérifiez la taille des embouts, la compatibilité et le contenu auprès du vendeur.',
        'כלי להתקנת מחוגי שעון. יש לבדוק עם המוכר את מידות הקצוות, ההתאמה לשעון ותכולת המוצר.',
    ),
    'irrigation_punch': _translations(
        'Пробойник для отверстий в трубке полива. Уточните совместимый диаметр трубки и размер отверстия у продавца.',
        'A punch for making holes in irrigation tubing. Check the compatible tubing diameter and hole size with the seller.',
        'Perfurador para fazer furos em tubos de irrigação. Confira o diâmetro de tubo compatível e o tamanho do furo.',
        'Perforador para hacer agujeros en tubos de riego. Consulta el diámetro de tubo compatible y el tamaño del agujero.',
        'Perforateur pour faire des trous dans un tuyau d’irrigation. Vérifiez le diamètre de tuyau compatible et la taille du trou.',
        'מחורר ליצירת חורים בצינור השקיה. יש לבדוק עם המוכר את קוטר הצינור המתאים ואת גודל החור.',
    ),
    'reed_trimmer': _translations(
        'Триммер для подрезки трости саксофона. Сверьте совместимость с размером и типом ваших тростей у продавца.',
        'A trimmer for saxophone reeds. Check compatibility with the size and type of your reeds with the seller.',
        'Cortador para aparar palhetas de saxofone. Confira com o vendedor a compatibilidade com o tamanho e o tipo das palhetas.',
        'Cortador para recortar cañas de saxofón. Consulta con el vendedor la compatibilidad con el tamaño y el tipo de tus cañas.',
        'Coupe-anche pour tailler les anches de saxophone. Vérifiez auprès du vendeur la compatibilité avec leur taille et leur type.',
        'קוצץ לחיתוך עלים לסקסופון. יש לבדוק עם המוכר התאמה לגודל ולסוג העלים שברשותכם.',
    ),
    'aquarium_tweezers': _translations(
        'Пинцет для работы с небольшими предметами в аквариуме. Сверьте длину и форму концов у продавца.',
        'Tweezers for handling small objects in an aquarium. Check the length and tip shape with the seller.',
        'Pinça para manusear pequenos objetos no aquário. Confira o comprimento e o formato das pontas com o vendedor.',
        'Pinzas para manipular objetos pequeños en el acuario. Consulta la longitud y la forma de las puntas con el vendedor.',
        'Pince pour manipuler de petits objets dans un aquarium. Vérifiez sa longueur et la forme des pointes auprès du vendeur.',
        'פינצטה לטיפול בפריטים קטנים באקווריום. יש לבדוק עם המוכר את האורך ואת צורת הקצוות.',
    ),
    'keyboard_switch_opener': _translations(
        'Инструмент для открытия переключателей клавиатуры. Перед покупкой проверьте совместимость с типом ваших переключателей.',
        'A tool for opening keyboard switches. Before buying, check compatibility with your switch type.',
        'Ferramenta para abrir switches de teclado. Antes de comprar, confira a compatibilidade com o tipo de switch usado.',
        'Herramienta para abrir interruptores de teclado. Antes de comprar, comprueba la compatibilidad con tu tipo de interruptor.',
        'Outil pour ouvrir les switches de clavier. Avant l’achat, vérifiez sa compatibilité avec votre type de switch.',
        'כלי לפתיחת מתגי מקלדת. לפני הקנייה יש לבדוק התאמה לסוג המתגים שברשותכם.',
    ),
    'bearing_puller': _translations(
        'Съёмник для извлечения подшипников. Сверьте допустимые размеры и совместимость с вашей деталью у продавца.',
        'A puller for removing bearings. Check the supported sizes and compatibility with your part with the seller.',
        'Extrator para remover rolamentos. Confira com o vendedor as medidas compatíveis e a adequação à sua peça.',
        'Extractor para retirar rodamientos. Consulta con el vendedor las medidas admitidas y la compatibilidad con tu pieza.',
        'Extracteur pour retirer des roulements. Vérifiez les dimensions compatibles et l’adaptation à votre pièce auprès du vendeur.',
        'חולץ להוצאת מסבים. יש לבדוק עם המוכר את טווח המידות ואת ההתאמה לחלק שברשותכם.',
    ),
    'cable_fish_tape': _translations(
        'Протяжка помогает провести кабель через канал. Уточните длину, диаметр и выбранный вариант у продавца.',
        'Fish tape helps guide cable through a conduit. Check its length, diameter and selected version with the seller.',
        'Passa-fio para guiar cabos por conduítes. Confira o comprimento, o diâmetro e a versão escolhida com o vendedor.',
        'Pasacables para guiar cables por un conducto. Consulta la longitud, el diámetro y la variante elegida con el vendedor.',
        'Tire-fil pour guider un câble dans une gaine. Vérifiez sa longueur, son diamètre et la variante choisie auprès du vendeur.',
        'סרט להשחלת כבל דרך תעלה. יש לבדוק עם המוכר את האורך, הקוטר ופרטי הדגם שנבחר.',
    ),
    'button_hook': _translations(
        'Крючок помогает застёгивать пуговицы. Сверьте размер крючка и его пригодность для ваших пуговиц у продавца.',
        'A button hook helps with fastening buttons. Check the hook size and suitability for your buttons with the seller.',
        'Gancho para ajudar a abotoar roupas. Confira com o vendedor o tamanho do gancho e a adequação aos seus botões.',
        'Gancho para ayudar a abrochar botones. Consulta con el vendedor el tamaño del gancho y si sirve para tus botones.',
        'Crochet pour aider à boutonner un vêtement. Vérifiez sa taille et son adaptation à vos boutons auprès du vendeur.',
        'וו המסייע בכפתור בגדים. יש לבדוק עם המוכר את גודל הוו ואת התאמתו לכפתורים שלכם.',
    ),
    'bead_spinner': _translations(
        'Спиннер для набора бисера на нить. Уточните, входит ли игла, и проверьте совместимый размер бисера у продавца.',
        'A bead spinner for threading beads. Ask whether a needle is included and check the compatible bead size with the seller.',
        'Enfiador giratório para colocar miçangas no fio. Pergunte se inclui agulha e confira o tamanho de miçanga compatível.',
        'Ensartador giratorio para poner cuentas en un hilo. Pregunta si incluye aguja y comprueba el tamaño de cuenta compatible.',
        'Enfile-perles rotatif pour enfiler des perles. Demandez si une aiguille est incluse et vérifiez la taille de perles compatible.',
        'מכשיר מסתובב להשחלת חרוזים על חוט. יש לברר אם מחט כלולה ולבדוק עם המוכר את גודל החרוזים המתאים.',
    ),
    'fly_tying_vise': _translations(
        'Тиски удерживают крючок при вязании рыболовной мушки. Сверьте диапазон размеров крючков и способ крепления у продавца.',
        'A vise holds a hook while tying a fishing fly. Check the supported hook sizes and mounting method with the seller.',
        'Morsa para segurar o anzol ao atar uma mosca de pesca. Confira os tamanhos de anzol aceitos e a forma de fixação.',
        'Torno para sujetar el anzuelo al atar una mosca de pesca. Consulta los tamaños de anzuelo admitidos y la forma de fijación.',
        'Étau pour tenir l’hameçon lors du montage d’une mouche de pêche. Vérifiez les tailles d’hameçons et le mode de fixation.',
        'מלחציים לאחיזת קרס בזמן קשירת זבוב לדיג. יש לבדוק עם המוכר את טווח גדלי הקרסים ואת אופן הקיבוע.',
    ),
}


def task_description(task_key, lang):
    """Return the checked task's copy; never invent a fallback translation."""
    try:
        return TASK_COPY[task_key][lang]
    except (KeyError, TypeError) as exc:
        raise ValueError('task_copy_missing') from exc
