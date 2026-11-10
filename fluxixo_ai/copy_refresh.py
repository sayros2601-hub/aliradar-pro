"""Prepare an offline, description-only update to an existing sourced card."""
from copy import deepcopy
import re

from .autonomous import LANGS, SEEDS, _matches
from .task_copy import task_description


class CopyRefreshError(ValueError):
    pass


def prepare_update(catalog, translations, product_id):
    """Return updated copies; never fetch, mutate inputs, or change identity/media."""
    if not isinstance(product_id, str) or not re.fullmatch(r'[1-9][0-9]{0,31}', product_id):
        raise CopyRefreshError('product_id_invalid')
    products = catalog.get('products') if isinstance(catalog, dict) else None
    if not isinstance(products, list):
        raise CopyRefreshError('catalog_invalid')
    matches = [p for p in products if isinstance(p, dict) and p.get('sourceProductId') == product_id]
    if len(matches) != 1 or matches[0].get('id') != 'auto-' + product_id:
        raise CopyRefreshError('product_identity_invalid')
    item = matches[0]
    seeds = [seed for seed in SEEDS if seed['key'] == item.get('sourceTask')]
    title = item.get('sourceTitle')
    if (len(seeds) != 1 or not isinstance(title, str) or not _matches(seeds[0], title)
            or ('category' in item and item['category'] != seeds[0]['category'])):
        raise CopyRefreshError('source_task_mismatch')
    product_translations = translations.get('products') if isinstance(translations, dict) else None
    localizations = product_translations.get(item['id']) if isinstance(product_translations, dict) else None
    if not isinstance(localizations, dict):
        raise CopyRefreshError('localizations_invalid')
    for lang in LANGS[1:]:
        value = localizations.get(lang)
        if (not isinstance(value, dict) or not isinstance(value.get('name'), str)
                or not value['name'] or not isinstance(value.get('headline'), list)
                or len(value['headline']) != 2):
            raise CopyRefreshError('localizations_invalid')
    descriptions = {lang: task_description(seeds[0]['key'], lang) for lang in LANGS}
    if not all(isinstance(value, str) and value for value in descriptions.values()):
        raise CopyRefreshError('description_invalid')
    updated_catalog, updated_translations = deepcopy(catalog), deepcopy(translations)
    updated_item = next(p for p in updated_catalog['products'] if isinstance(p, dict)
                        and p.get('sourceProductId') == product_id)
    updated_item['description'] = updated_item['details'] = descriptions['ru']
    for lang in LANGS[1:]:
        updated_translations['products'][item['id']][lang]['description'] = descriptions[lang]
    return {'catalog': updated_catalog, 'translations': updated_translations,
            'locales': list(LANGS), 'product_id': product_id, 'id': item['id']}
