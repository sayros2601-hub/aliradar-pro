"""Regression tests preventing seller-title placeholder fallbacks and cloned SEO templates."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site/tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_texts  # noqa: E402
import copy_originality  # noqa: E402
import market_seo  # noqa: E402
import verify_release  # noqa: E402
from fluxixo_ai import autonomous, curated_copy, discovery_curator  # noqa: E402


class CuratedCopyAndGateTests(unittest.TestCase):
    def test_every_curated_rare_query_has_clean_6_lang_copy(self):
        rare_keys = {entry['key'] for entry in discovery_curator.CURATED_RARE_QUERIES}
        self.assertEqual(rare_keys, set(curated_copy.CURATED_TASK_COPY))
        problems = []
        for entry in discovery_curator.CURATED_RARE_QUERIES:
            key = entry['key']
            cand = {
                'product_id': '1005010357329711',
                'title': entry['query'] + ' ' + ' '.join(g[0] for g in entry['groups']),
                'detail_url': 'https://www.aliexpress.com/item/1005010357329711.html',
                'affiliate_url': 'https://s.click.aliexpress.com/e/_sample',
                'image_url': 'https://ae01.alicdn.com/kf/sample.jpg',
                'task': entry,
            }
            record, translated = autonomous.build_record(cand)
            problems.extend(check_texts.lint_product_bundle(key, record, translated, reject_placeholders=True))
            bundle = {'ru': record, **translated}
            self.assertEqual([], copy_originality.check_source_title_mirroring(bundle, cand['title']))
        self.assertEqual([], problems)

    def test_soap_foamer_candidate_builds_without_raw_seller_title(self):
        task = next(q for q in discovery_curator.CURATED_RARE_QUERIES if q['key'] == 'rare_auto_soap_foamer')
        cand = {
            'product_id': '1005010357329711',
            'title': 'Automatic Foam Soap Dispenser Touchless USB Rechargeable With Infrared Sensor 320ml Capacity And Five Levels Of Foam Output',
            'detail_url': 'https://www.aliexpress.com/item/1005010357329711.html',
            'affiliate_url': 'https://s.click.aliexpress.com/e/_c3pExu55',
            'image_url': 'https://ae01.alicdn.com/kf/sample.jpg',
            'availableMarkets': ['RU', 'US', 'BR', 'MX', 'IL', 'FR'],
            'task': task,
        }
        record, translated = autonomous.build_record(cand)
        self.assertLessEqual(len(record['name']), 62)
        self.assertNotIn('Название приведено из карточки продавца', record['description'])
        for lang, loc in translated.items():
            self.assertLessEqual(len(loc['name']), 62)
            self.assertFalse(check_texts.has_placeholder_copy(loc['description']))
        record['imageQualityVerified'] = True
        ok, errs = discovery_curator.pre_deploy_catalog_gate(
            [record], [], require_markets=True, translations={record['id']: translated},
        )
        self.assertTrue(ok, errs)

    def test_pre_deploy_gate_blocks_placeholder_and_oversized_titles(self):
        broken = {
            'id': 'auto-999999',
            'name': 'X ' * 40,
            'headline': ['Находка', 'для дома.'],
            'description': 'Название приведено из карточки продавца. Перед покупкой проверьте характеристики.',
            'category': 'Дом',
            'sourceProductId': '999999',
            'sourceTitle': 'Long Raw English Title Dispenser',
            'availableMarkets': ['US'],
            'imageQualityVerified': True,
        }
        ok, errs = discovery_curator.pre_deploy_catalog_gate([broken], [], require_markets=True)
        self.assertFalse(ok)
        self.assertTrue(any('title_too_long' in e for e in errs))
        self.assertTrue(any('placeholder_copy_forbidden' in e for e in errs))


class AntiTemplateBoilerplateTests(unittest.TestCase):
    def test_default_product_pages_do_not_emit_cloned_checklist_or_default_faq(self):
        self.assertEqual('', market_seo.market_checklist_html('Техника', 'ru'))
        for lang in ('ru', 'en', 'pt', 'es', 'fr', 'he'):
            html_out, schema = market_seo.faq_section_and_schema('Умные часы', 'Техника', lang, overrides={})
            self.assertEqual('', html_out)
            self.assertIsNone(schema)

        # Custom per-route FAQ is still rendered cleanly when explicitly provided
        custom_html, custom_schema = market_seo.faq_section_and_schema(
            'Умные часы', 'Техника', 'ru',
            overrides={'faq': [{'q': 'Какая ширина крепления ремешка?', 'a': 'Проверьте ширину ушек корпуса на странице продавца перед заказом.'}]},
        )
        self.assertIn('product-faq', custom_html)
        self.assertEqual('FAQPage', custom_schema['@type'])

    def test_verify_release_rejects_cloned_sections_placeholders_and_high_jaccard(self):
        cloned_guide = (
            '<section class="market-guide"><div class="note-kicker">Памятка</div>'
            '<p>Проверяйте напряжение сети, вилку и комплектацию перед покупкой.</p></section>'
        )
        shared_tokens = ' '.join(f'sharedword{i}' for i in range(40))
        bad_pages = {}
        for idx in range(6):
            url = f'https://www.fluxixo.shop/products/item-{idx}/'
            body = (
                f'<main><h1>Товар {idx}</h1>'
                f'<p class="t">Уникальное описание товара номер {idx} для проверки.</p>'
                f'<p>{shared_tokens}</p>{cloned_guide}</main>'
            )
            bad_pages[url] = f'<html><body>{body}</body></html>'
        bad_pages['https://www.fluxixo.shop/en/products/item-0/'] = (
            '<html><body><main><h1>Touchless Dispenser</h1>'
            '<p class="t">The title comes from the seller listing. Check specs before purchase.</p>'
            '</main></body></html>'
        )
        bad_pages['https://www.fluxixo.shop/products/dup-a/'] = (
            '<html><body><main><h1>Дубликат A</h1><p class="t">Одинаковое описание для двух разных страниц.</p></main></body></html>'
        )
        bad_pages['https://www.fluxixo.shop/products/dup-b/'] = (
            '<html><body><main><h1>Дубликат B</h1><p class="t">Одинаковое описание для двух разных страниц.</p></main></body></html>'
        )

        errs = verify_release.validate_product_page_uniqueness(bad_pages)
        self.assertTrue(any('repeated <section class="market-guide">' in e for e in errs), errs)
        self.assertTrue(any('placeholder copy on product page' in e for e in errs), errs)
        self.assertTrue(any('duplicate product <p class="t">' in e for e in errs), errs)
        self.assertTrue(any('high template similarity in ru' in e for e in errs), errs)

    def test_verify_release_accepts_distinct_product_pages(self):
        vocabs = [
            'керамическая кружка эспрессо блюдце ручная глазурь утренний кофе столешница',
            'беспроводная игровая мышь оптический сенсор тефлоновые ножки киберспорт проводка',
            'силиконовый коврик выпечка духовка антипригарное покрытие кондитерский лист скалка',
            'алюминиевый штатив шаровая головка фотосъёмка путешествие панорама стабилизация',
            'увлажнитель воздуха ультразвуковой туман спальня таймер ночник тишина',
            'органайзер кабели рабочий стол магнитный держатель порядок провода фиксатор',
        ]
        good_pages = {
            f'https://www.fluxixo.shop/products/good-{i}/': (
                f'<html><head><style>.market-guide{{color:#fff}}.product-faq{{margin:0}}</style></head>'
                f'<body><main><h1>Продукт {i}</h1><p class="t">{v}</p></main></body></html>'
            )
            for i, v in enumerate(vocabs)
        }
        self.assertEqual([], verify_release.validate_product_page_uniqueness(good_pages))


if __name__ == '__main__':
    unittest.main()
