"""A fixed editorial selection of existing products; no rotation state or generation."""

from pathlib import Path
import shutil

PINNED_PRODUCT_IDS = (
    'find-062-coffee-scale',
    'find-064-book-light',
    'find-063-cable-tester',
    'find-023-cat-laser',
    'find-060-tire-inflator',
    'find-039-pixel-display',
    'find-024-trekking-poles',
)

# Curated transparent replacements are kept in source, separate from catalog images.
FEATURED_IMAGE_OVERRIDES = {
    'find-063-cable-tester': '/assets/featured/find-063-cable-tester-clean-v1.png',
    'find-023-cat-laser': '/assets/featured/find-023-cat-laser-clean-v1.png',
}

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


def copy_featured_images(output_dir, source_dir=None):
    """Publish the two versioned source PNGs without touching catalog imagery."""
    source_dir = Path(source_dir) if source_dir is not None else Path(__file__).parent / 'static/featured'
    copies = [(source_dir / Path(url).name, Path(output_dir) / url.lstrip('/'))
              for url in FEATURED_IMAGE_OVERRIDES.values()]
    for source, _ in copies:
        if not source.is_file():
            raise FileNotFoundError(f'Missing curated carousel image: {source}')
        if source.stat().st_size == 0:
            raise ValueError(f'Empty curated carousel image: {source}')
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
