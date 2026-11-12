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

    def test_public_summary_has_no_query_text(self):
        results = {'bing': {'totals': seo.totals([{'query': 'secret query', 'clicks': 1, 'impressions': 9, 'position': 3}]),
                            'keyword_lookups_today': 2, 'rows': [{'query': 'secret query'}]}}
        text = seo.summary_text(TODAY, results, {'google': 'нет ключа', 'yandex': 'нет токена'})
        self.assertNotIn('secret query', text)
        self.assertIn('| Bing | 1 | 9 |', text)

    def test_ru_pages_only_for_yandex_recrawl(self):
        self.assertTrue(seo.ru_url('https://www.fluxixo.shop/products/x/'))
        self.assertFalse(seo.ru_url('https://www.fluxixo.shop/en/products/x/'))
        self.assertFalse(seo.ru_url('https://www.fluxixo.shop/'))


if __name__ == '__main__':
    unittest.main()
