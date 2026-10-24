import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock
from dealvault_core import DOMAIN, write_json
from search_integrations import build_search_integrations
from submit_indexnow import plan, submit


class SearchMapsTests(unittest.TestCase):
    def test_language_maps_preserve_all_canonical_urls_and_public_bing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            urls = [DOMAIN+'/', DOMAIN+'/ru/', DOMAIN+'/he/deals/sample', DOMAIN+'/es/contact']
            sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
            for url in urls:
                ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = url
            ET.ElementTree(sitemap).write(root/'sitemap.xml')
            key = 'A'*32
            self.assertEqual(build_search_integrations(root, {'bing_site_verification':key}), 4)
            redirects = (root/'_redirects').read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(redirects), 7)
            for prefix in ('', '/ru', '/he', '/es'):
                self.assertIn(f'{prefix}/deal/:slug {prefix}/deals/:slug 301', redirects)
            self.assertIn('/sitemap /sitemap.xml 301', redirects)
            self.assertEqual(ET.parse(root/'BingSiteAuth.xml').findtext('./user'), key)
            combined = []
            for name in ('en','ru','he','es'):
                combined.extend(x.text for x in ET.parse(root/f'sitemap-{name}.xml').findall('.//{*}loc'))
            self.assertCountEqual(combined, urls)

    def test_foreign_sitemap_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'sitemap.xml').write_text('<urlset><url><loc>https://other.example/</loc></url></urlset>')
            with self.assertRaisesRegex(ValueError, 'foreign'):
                build_search_integrations(root, {})


class SearchNotificationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_json(self.root/'build-info.json', {'catalog_sha256':'new'})
        self.product = {'url':DOMAIN+'/deals/sample', 'title':'Reference find'}
        write_json(self.root/'feed.json', {'items':[self.product]})
        (self.root/'sitemap.xml').write_text(f'<urlset><url><loc>{DOMAIN}/deals/sample</loc></url></urlset>')
        self.previous = {'available':True, 'build':{'catalog_sha256':'old'}, 'feed':{'items':[]}}

    def test_unchanged_release_sends_nothing(self):
        self.previous['build']['catalog_sha256'] = 'new'
        urls = plan(self.previous, self.root)
        sender = Mock()
        self.assertEqual(submit(urls, sender)['status'], 'unchanged')
        sender.assert_not_called()

    def test_new_and_retired_products_notify_all_languages(self):
        self.previous['feed']['items'] = [{'url':DOMAIN+'/deals/retired', 'title':'Previous find'}]
        urls = plan(self.previous, self.root)
        self.assertEqual(len(urls), 12)
        self.assertIn(DOMAIN+'/he/deals/sample', urls)
        self.assertIn(DOMAIN+'/ru/deals/retired', urls)
        self.assertIn(DOMAIN+'/', urls)

    def test_html_only_release_is_not_silently_skipped(self):
        self.previous['build']={'catalog_sha256':'new','html_sha256':'old-layout'}
        write_json(self.root/'build-info.json',{'catalog_sha256':'new','html_sha256':'new-layout'})
        self.assertEqual(plan(self.previous,self.root),[DOMAIN+'/deals/sample'])
        self.previous['build']['html_sha256']='new-layout'
        self.assertEqual(plan(self.previous,self.root),[])

    def test_missing_observation_cannot_silently_trigger_bulk_send(self):
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            plan({'available':False}, self.root)

    def test_foreign_feed_and_submission_urls_never_reach_provider(self):
        self.previous['feed']['items'] = [{'url':'https://other.example/deals/sample'}]
        with self.assertRaisesRegex(ValueError, 'Invalid product URL'):
            plan(self.previous, self.root)
        sender = Mock()
        with self.assertRaisesRegex(ValueError, 'Foreign'):
            submit(['https://other.example/'], sender)
        sender.assert_not_called()

    def test_localized_only_change_falls_back_to_current_canonical_pages(self):
        self.previous['feed']['items'] = [copy.deepcopy(self.product)]
        self.assertEqual(plan(self.previous, self.root), [DOMAIN+'/deals/sample'])


if __name__ == '__main__':
    unittest.main()
