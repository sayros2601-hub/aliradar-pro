"""Prepare an additive catalog batch without publishing or writing site files.

The caller supplies the currently locked Git HEAD, validated identity-migration
evidence and a media preparation callback. This module does not call AliExpress,
GitHub, Cloudflare or a model and never marks a candidate committed/published.
Unknown historical product identity blocks preparation until reconciled.
"""
from __future__ import annotations

from copy import deepcopy
import re
from urllib.parse import urlsplit

from .store import LANGUAGES, PRODUCT_ID

CATEGORIES = frozenset(('Техника', 'Дом', 'Кухня', 'В дороге', 'Инструменты',
                        'Уход', 'Спорт', 'На природе', 'Питомцы'))
EVIDENCE_HASH = re.compile(r'^[0-9a-f]{64}$')
LEGACY_METHODS = frozenset(('verified_redirect', 'verified_api'))
THEMES = frozenset(('blue', 'coral', 'sand', 'lavender', 'rose'))
SOURCE_COPY = {
    'ru': ('Название продавца', 'Название приведено из карточки продавца. Перед покупкой проверьте характеристики, вариант и условия по ссылке.'),
    'en': ('Seller title', 'The title comes from the seller listing. Check specifications, the selected option and terms before buying.'),
    'pt': ('Título do vendedor', 'O título vem do anúncio do vendedor. Confira as características, a opção escolhida e as condições antes de comprar.'),
    'es': ('Título del vendedor', 'El título procede del anuncio del vendedor. Revisa las características, la opción elegida y las condiciones antes de comprar.'),
    'fr': ('Titre du vendeur', 'Le titre provient de l’annonce du vendeur. Vérifiez les caractéristiques, la variante et les conditions avant l’achat.'),
    'he': ('כותרת המוכר', 'הכותרת לקוחה מדף המוכר. לפני הקנייה יש לבדוק את המפרט, האפשרות שנבחרה והתנאים.'),
}


class PublisherError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _detail(product_id, value):
    return value == f'https://www.aliexpress.com/item/{product_id}.html'


def _legacy_identities(catalog, identity_index):
    if not isinstance(catalog, dict) or not isinstance(catalog.get('products'), list):
        raise PublisherError('catalog_invalid')
    if not isinstance(identity_index, dict):
        raise PublisherError('historical_identity_incomplete')
    known = set()
    ids = set()
    for item in catalog['products']:
        if not isinstance(item, dict):
            raise PublisherError('catalog_invalid')
        internal_id = item.get('id')
        if not isinstance(internal_id, str) or not internal_id or internal_id in ids:
            raise PublisherError('catalog_invalid')
        ids.add(internal_id)
        market_id = item.get('sourceProductId')
        if market_id is not None:
            if not isinstance(market_id, str) or not PRODUCT_ID.fullmatch(market_id):
                raise PublisherError('catalog_identity_invalid')
        else:
            identity = identity_index.get(internal_id)
            if not isinstance(identity, dict):
                raise PublisherError('historical_identity_incomplete')
            market_id = identity.get('product_id')
            if (not isinstance(market_id, str) or not PRODUCT_ID.fullmatch(market_id)
                    or not _detail(market_id, identity.get('resolved_detail_url'))
                    or identity.get('source_affiliate_url') != item.get('affiliateUrl')
                    or not isinstance(item.get('affiliateUrl'), str) or not item['affiliateUrl']
                    or identity.get('method') not in LEGACY_METHODS
                    or not isinstance(identity.get('evidence_sha256'), str)
                    or not EVIDENCE_HASH.fullmatch(identity['evidence_sha256'])):
                raise PublisherError('historical_identity_invalid')
        known.add(market_id)
    return known, ids


def _affiliate(value):
    if not isinstance(value, str) or len(value) > 4096:
        raise PublisherError('affiliate_url_invalid')
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == 'https' and parts.hostname == 's.click.aliexpress.com'
                 and parts.username is None and parts.password is None and parts.port is None
                 and not parts.fragment and not any(c in value for c in ('\\', '\r', '\n', '\t'))
                 and parts.path.startswith('/e/') and len(parts.path) > 3)
    except ValueError:
        valid = False
    if not valid:
        raise PublisherError('affiliate_url_invalid')
    return value


def _validate_candidate(candidate, ids):
    product_id = candidate['product_id']
    internal_id = 'ai-' + product_id
    if internal_id in ids:
        raise PublisherError('internal_id_conflict')
    if candidate.get('category') not in CATEGORIES:
        raise PublisherError('category_invalid')
    _affiliate(candidate.get('affiliate_url'))
    theme = candidate.get('theme', 'lavender')
    if theme not in THEMES:
        raise PublisherError('theme_invalid')
    return internal_id


def source_content(candidate):
    """Safe six-locale copy based only on the exact seller title.

    A title returned by AliExpress may itself contain seller claims and is not
    independent verification. It remains unchanged across locales when a
    verified same-item localized API title is unavailable. Client-supplied
    copy and reasoning are deliberately excluded from published facts.
    """
    title = candidate.get('title') if isinstance(candidate, dict) else None
    if not isinstance(title, str) or not title.strip() or len(title) > 1000:
        raise PublisherError('source_title_invalid')
    return {locale: {'name': title, 'headline': [SOURCE_COPY[locale][0]],
                     'description': SOURCE_COPY[locale][1]} for locale in LANGUAGES}


def _record(candidate, internal_id, media):
    if (not isinstance(media, dict)
            or media.get('image') != f'assets/images/{internal_id}.webp'
            or media.get('original') != f'assets/originals/{internal_id}.webp'):
        raise PublisherError('media_invalid')
    content = source_content(candidate)['ru']
    return {
        'id': internal_id, **content, 'category': candidate['category'],
        'image': media['image'], 'original': media['original'],
        'imageNote': 'Подготовленное изображение на основе фото продавца; исходное изображение доступно для сравнения.',
        'affiliateUrl': _affiliate(candidate['affiliate_url']), 'sourceUrl': candidate['detail_url'],
        'sourceProductId': candidate['product_id'], 'sourceDetailUrl': candidate['detail_url'],
        'sourceTitle': candidate['title'], 'demo': False, 'theme': candidate.get('theme', 'lavender'),
        'scale': 0.85, 'rotation': 0, 'details': content['description'], 'facts': [],
    }


def prepare_batch(*, store, day, owner, catalog, translations, prepare_media,
                  identity_index, lease_seconds=300, now=None):
    """Reserve and prepare at most three additions; return new in-memory objects.

    The current catalog and translations are not modified. The callback receives
    (candidate, deterministic internal id), returns required site-relative image
    paths, and is responsible for any *staging* of media outside the live site.
    It must not publish. A callback failure terminally fails all still-reserved
    claims and consumes their quota conservatively. Already matched historical
    IDs are skipped and marked failed rather than inserted twice.

    The identity index is trusted input produced by a separately verified
    migration, not proof generated by this function. Every older catalog item
    without sourceProductId must be covered. Writer orchestration must verify
    current HEAD, hold its shared lock, and reconcile stale leases before use.
    """
    known, internal_ids = _legacy_identities(catalog, identity_index)
    if (not isinstance(translations, dict) or not isinstance(translations.get('products'), dict)
            or not callable(prepare_media)):
        raise PublisherError('translations_or_media_invalid')
    new_catalog = deepcopy(catalog)
    new_translations = deepcopy(translations)
    claims = store.claim(day, owner, 3, lease_seconds=lease_seconds, now=now)
    reserved = list(claims)
    accepted = []
    duplicates = []
    try:
        to_prepare = []
        for claim in claims:
            candidate = claim['candidate']
            if candidate['product_id'] in known:
                store.fail(claim['claim_id'], owner, 'duplicate_existing', now=now)
                reserved.remove(claim)
                duplicates.append(claim['product_id'])
                continue
            internal_id = _validate_candidate(candidate, internal_ids)
            known.add(candidate['product_id'])
            internal_ids.add(internal_id)
            to_prepare.append((claim, internal_id))
        new_products = []
        for claim, internal_id in to_prepare:
            candidate = claim['candidate']
            media = prepare_media(deepcopy(candidate), internal_id)
            product = _record(candidate, internal_id, media)
            new_products.append(product)
            grounded = source_content(candidate)
            new_translations['products'][internal_id] = {
                locale: grounded[locale] for locale in LANGUAGES if locale != 'ru'
            }
            accepted.append({key: claim[key] for key in ('request_id', 'product_id', 'claim_id', 'state')})
        new_catalog['products'] = new_products + new_catalog['products']
    except Exception:
        # An error can occur after the callback produced staging files. Those
        # files are never published by this module; caller owns staging cleanup.
        for claim in reserved:
            try:
                store.fail(claim['claim_id'], owner, 'batch_preparation_failed', now=now)
            except Exception:
                # Keep the original failure generic and never leak source text.
                pass
        raise PublisherError('batch_preparation_failed') from None
    return {'catalog': new_catalog, 'translations': new_translations, 'claims': accepted,
            'report': {'existing_count': len(catalog['products']), 'incoming_count': len(accepted),
                       'duplicates_skipped': duplicates, 'historical_identity': 'provided_and_required',
                       'published': False}}
