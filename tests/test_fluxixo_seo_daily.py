import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'fluxixo_site/tools'))
import seo_daily as seo  # noqa: E402

TODAY = date(2026, 11, 12)


class SeoDailyTest(unittest.TestCase):
    def test_sitemap_urls_collects_pages_and_excludes_sitemap_index_locations(self):
        root = 'https://www.fluxixo.shop/'
        russian_page = f'{root}catalog/'
        english_page = f'{root}en/journal/wifi-repeater-buying-guide/'
        namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        with tempfile.TemporaryDirectory() as folder:
            dist = Path(folder)
            (dist / 'sitemap.xml').write_text(
                f'<urlset xmlns="{namespace}"><url><loc>{root}</loc></url>'
                f'<url><loc>{russian_page}</loc></url></urlset>',
                encoding='utf-8',
            )
            (dist / 'sitemap-index.xml').write_text(
                f'<sitemapindex xmlns="{namespace}">'
                f'<sitemap><loc>{root}sitemap-ru.xml</loc></sitemap>'
                f'<sitemap><loc>{root}sitemap-en.xml</loc></sitemap></sitemapindex>',
                encoding='utf-8',
            )
            (dist / 'sitemap-en.xml').write_text(
                f'<urlset xmlns="{namespace}"><url><loc> {root} </loc></url>'
                f'<url><loc>{english_page}</loc></url></urlset>',
                encoding='utf-8',
            )
            with mock.patch.object(seo, 'DIST', dist):
                self.assertEqual([root, russian_page, english_page], seo.sitemap_urls())

    def test_totals_weight_position_by_impressions(self):
        rows = [{'clicks': 1, 'impressions': 100, 'position': 4.0}, {'clicks': 0, 'impressions': 300, 'position': 12.0}]
        self.assertEqual(seo.totals(rows), {'clicks': 1, 'impressions': 400, 'ctr': 0.25, 'position': 10.0, 'queries': 2})
        self.assertEqual(seo.totals([])['position'], None)

    def test_opportunities(self):
        rows = [{'query': 'shown not clicked', 'clicks': 0, 'impressions': 80, 'position': 5.0},
                {'query': 'almost top', 'clicks': 2, 'impressions': 20, 'position': 11.0},
                {'query': 'fine', 'clicks': 9, 'impressions': 40, 'position': 2.0}]
        found = seo.opportunities(rows)
        self.assertEqual([r['query'] for r in found['weak_ctr']], ['shown not clicked'])
        self.assertEqual([r['query'] for r in found['near_top']], ['almost top'])

    def test_state_round_trip_and_wrong_key(self):
        from cryptography.fernet import Fernet
        key, other = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.enc'
            with mock.patch.object(seo, 'STATE_FILE', path):
                state = seo.load_state(key)
                state['days']['2026-11-12'] = {'bing': {'clicks': 3}}
                path.write_bytes(seo.encrypt(key, state))
                self.assertEqual(seo.load_state(key)['days']['2026-11-12']['bing']['clicks'], 3)
                self.assertNotIn(b'clicks', path.read_bytes())
                with self.assertRaises(SystemExit):
                    seo.load_state(other)

    def test_bing_keeps_last_28_days_and_merges_weeks(self):
        # 2026-09-22 (outside the 28 days before 2026-11-12), 2026-10-26 and 2026-11-07 (inside).
        old, recent1, recent2 = '/Date(1790000000000)/', '/Date(1793000000000)/', '/Date(1794000000000-0700)/'
        replies = {
            'GetUserSites': [{'Url': 'https://www.fluxixo.shop/'}],
            'GetQueryStats': [{'Query': 'pill box', 'Clicks': 5, 'Impressions': 50, 'AvgImpressionPosition': 30, 'Date': old},
                              {'Query': 'pill box', 'Clicks': 1, 'Impressions': 10, 'AvgImpressionPosition': 8, 'Date': recent1},
                              {'Query': 'pill box', 'Clicks': 1, 'Impressions': 30, 'AvgImpressionPosition': 12, 'Date': recent2}],
            'GetPageStats': [], 'GetCrawlIssues': [], 'GetUrlSubmissionQuota': {'DailyQuota': 100, 'MonthlyQuota': 1900},
            'GetRelatedKeywords': [{'Query': 'pill organizer', 'Impressions': 9, 'BroadImpressions': 20}],
        }
        def fake(method, url, **_):
            return {'d': replies[url.split('/json/')[1].split('?')[0]]}
        state = {'keywords': {}}
        with mock.patch.object(seo, 'http', fake):
            result = seo.bing('k', state, TODAY, ['Pill organizer'])
        self.assertEqual(result['rows'], [{'query': 'pill box', 'clicks': 2, 'impressions': 40, 'position': 11.0}])
        self.assertEqual(state['keywords']['Pill organizer']['related'][0]['query'], 'pill organizer')

    def test_public_summary_has_no_query_text_or_yandex(self):
        results = {'bing': {'totals': seo.totals([{'query': 'secret query', 'clicks': 1, 'impressions': 9, 'position': 3}]),
                            'keyword_lookups_today': 2, 'indexnow_submitted': 3, 'rows': [{'query': 'secret query'}]}}
        text = seo.summary_text(TODAY, results, {'google': 'нет ключа'})
        self.assertNotIn('secret query', text)
        self.assertNotIn('Яндекс', text)
        self.assertIn('| Bing | 1 | 9 |', text)
        self.assertIn('IndexNow 3', text)


class BingAndYandexParityTests(unittest.TestCase):
    def test_bing_submits_missing_feeds_fixes_page_key_and_submits_url_batch(self):
        from datetime import date
        import seo_daily as seo

        calls = []
        state = seo.load_state(None)
        today = date(2026, 11, 13)
        urls = [
            'https://www.fluxixo.shop/',
            'https://www.fluxixo.shop/en/',
            'https://www.fluxixo.shop/products/katord-wifi-repeater/',
        ]

        def fake_http(method, url, *, headers=None, body=None, timeout=40):
            calls.append((method, url, body))
            if 'GetUserSites' in url:
                return {'d': [{'Url': 'https://www.fluxixo.shop/'}]}
            if 'GetQueryStats' in url:
                return {'d': []}
            if 'GetPageStats' in url:
                return {'d': [{'Url': 'https://www.fluxixo.shop/products/katord-wifi-repeater/',
                               'Clicks': 2, 'Impressions': 40, 'AvgImpressionPosition': 9.0,
                               'Date': '/Date(1794430808000)/'}]}
            if 'GetCrawlIssues' in url:
                return {'d': []}
            if 'GetUrlSubmissionQuota' in url:
                return {'d': {'DailyQuota': 2, 'MonthlyQuota': 100}}
            if 'GetFeeds' in url:
                return {'d': [{'Url': 'https://www.fluxixo.shop/sitemap-ru.xml',
                               'LastCrawled': '/Date(1794500000000)/', 'FileSize': 12000},
                              {'Url': 'https://www.fluxixo.shop/sitemap.xml',
                               'LastCrawled': '/Date(1794500000000)/', 'FileSize': 0}]}
            if 'GetRelatedKeywords' in url:
                return {'d': []}
            return {'d': None}

        orig_http = seo.http
        seo.http = fake_http
        try:
            res = seo.bing('k', state, today, ['WiFi Repeater'], urls=urls, dry_run=False)
            self.assertEqual('https://www.fluxixo.shop/products/katord-wifi-repeater/', res['pages'][0]['page'])
            self.assertIn('sitemap-index.xml', res['feeds_submitted'])
            self.assertIn('rss.xml', res['feeds_submitted'])
            self.assertIn('sitemap.xml', res['feeds_submitted'])
            self.assertNotIn('sitemap-ru.xml', res['feeds_submitted'])
            self.assertEqual(2, len(res['urls_submitted']))
            self.assertEqual({'https://www.fluxixo.shop/', 'https://www.fluxixo.shop/en/'}, set(res['urls_submitted']))
            res_again = seo.bing('k', state, today, ['WiFi Repeater'], urls=urls, dry_run=False)
            self.assertEqual(['https://www.fluxixo.shop/products/katord-wifi-repeater/'], res_again['urls_submitted'])
        finally:
            seo.http = orig_http

    def test_bing_indexnow_submits_only_changed_urls_to_bing(self):
        import json
        import tempfile
        from pathlib import Path
        import seo_daily as seo

        with tempfile.TemporaryDirectory() as tmp:
            site_dir = Path(tmp)
            tools = site_dir / 'tools'
            tools.mkdir()
            key = 'a' * 32
            (tools / 'indexnow-key.txt').write_text(key, encoding='utf-8')
            (tools / 'search-build-state.json').write_text(json.dumps({
                '/': {'sha256': '11' * 32},
                '/en/': {'sha256': '22' * 32},
            }), encoding='utf-8')
            (tools / 'indexnow-submitted.json').write_text(json.dumps({
                'https://www.fluxixo.shop/': '11' * 32,
            }), encoding='utf-8')

            posted = []

            def fake_http(method, url, *, headers=None, body=None, timeout=40):
                posted.append((method, url, body))
                return {}

            orig_http = seo.http
            seo.http = fake_http
            try:
                res = seo.bing_indexnow(
                    ['https://www.fluxixo.shop/', 'https://www.fluxixo.shop/en/'],
                    dry_run=False,
                    site_dir=site_dir,
                )
            finally:
                seo.http = orig_http

            self.assertEqual(1, res['submitted'])
            self.assertEqual(None, res['error'])
            self.assertEqual(1, len(posted))
            self.assertEqual('https://www.bing.com/indexnow', posted[0][1])
            self.assertEqual(['https://www.fluxixo.shop/en/'], posted[0][2]['urlList'])
            saved = json.loads((tools / 'indexnow-submitted.json').read_text(encoding='utf-8'))
            self.assertEqual('22' * 32, saved['https://www.fluxixo.shop/en/'])


if __name__ == '__main__':
    unittest.main()
