"""A fixed editorial selection of existing products; no rotation state or generation."""

PINNED_PRODUCT_IDS = (
    'find-062-coffee-scale',
    'find-064-book-light',
    'find-063-cable-tester',
    'find-023-cat-laser',
    'find-060-tire-inflator',
    'find-039-pixel-display',
    'find-024-trekking-poles',
)

CAROUSEL_COPY = {
    'ru': dict(title='Избранные находки', carousel='карусель', slide='слайд',
               prev='Предыдущий товар', next='Следующий товар',
               controls='Управление каруселью', count='{current} из {total}'),
    'en': dict(title='Selected finds', carousel='carousel', slide='slide',
               prev='Previous product', next='Next product',
               controls='Slideshow controls', count='{current} of {total}'),
    'es': dict(title='Hallazgos seleccionados', carousel='carrusel', slide='diapositiva',
               prev='Producto anterior', next='Siguiente producto',
               controls='Controles del carrusel', count='{current} de {total}'),
    'pt': dict(title='Achados selecionados', carousel='carrossel', slide='slide',
               prev='Produto anterior', next='Próximo produto',
               controls='Controles do carrossel', count='{current} de {total}'),
    'fr': dict(title='Notre sélection', carousel='carrousel', slide='diapositive',
               prev='Produit précédent', next='Produit suivant',
               controls='Commandes du carrousel', count='{current} sur {total}'),
    'he': dict(title='מוצרים נבחרים', carousel='קרוסלה', slide='שקופית',
               prev='המוצר הקודם', next='המוצר הבא',
               controls='פקדי הקרוסלה', count='{current} מתוך {total}'),
}


def select_featured_products(products):
    """Keep the pinned order, independent of catalog order, market priority or date.

    The caller supplies localized catalog records. A removed product or missing
    translation fails before rendering rather than creating a broken card or
    silently changing the user's fixed selection.
    """
    by_id = {product['id']: product for product in products}
    missing = [pid for pid in PINNED_PRODUCT_IDS if pid not in by_id]
    if missing:
        raise ValueError('Pinned carousel products unavailable in this locale: ' + ', '.join(missing))
    return [by_id[pid] for pid in PINNED_PRODUCT_IDS]
