"""Offline regressions for independent Russian Yandex notifications."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

import fluxixo_daily_rotate as daily


ORIGIN = 'https://www.fluxixo.shop'
RU_PATHS = ('/catalog/', '/products/import-0024/', '/products/auto-1005004679234788/')
OLD, NEW, LATER = 'a' * 64, 'b' * 64, 'c' * 64


class Response:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class YandexIndexNowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tools = self.root / 'tools'
        self.dist = self.root / 'dist'
        self.tools.mkdir()
        self.dist.mkdir()
        (self.tools / 'indexnow-key.txt').write_text('A' * 32, encoding='utf-8')
        self.state_path = self.tools / 'yandex-indexnow-state.json'
        self.fingerprints = {path: {'sha256': OLD} for path in (*RU_PATHS, '/en/')}
        self.write_json('search-build-state.json', self.fingerprints)
        self.write_json('indexnow-submitted.json', {ORIGIN + p: OLD for p in self.fingerprints})
        self.sitemap('sitemap.xml', list(self.fingerprints))
        self.sitemap('sitemap-ru.xml', list(RU_PATHS))
        self.calls = []
        self.yandex_status = 429
        self.on_yandex = None
        self.addCleanup(patch.stopall)
        patch.object(daily, 'SITE_ROOT', self.root).start()
        patch.object(daily, 'DIST', self.dist).start()
        patch.object(daily, 'RELEASE', self.root / 'release').start()
        patch.object(daily.urllib.request, 'urlopen', self.urlopen).start()
        patch('sys.stdout', io.StringIO()).start()

    def write_json(self, filename, value):
        (self.tools / filename).write_text(json.dumps(value), encoding='utf-8')

    def sitemap(self, filename, paths):
        tree = ET.Element('urlset')
        for path in paths:
            ET.SubElement(ET.SubElement(tree, 'url'), 'loc').text = (
                path if path.startswith('https:') else ORIGIN + path)
        ET.ElementTree(tree).write(self.dist / filename, encoding='unicode')

    def change(self, digest=NEW):
        self.fingerprints[RU_PATHS[0]]['sha256'] = digest
        self.fingerprints['/en/']['sha256'] = digest
        self.write_json('search-build-state.json', self.fingerprints)

    def urlopen(self, request, **_):
        self.calls.append((request.full_url, json.loads(request.data)))
        if request.full_url == 'https://api.indexnow.org/indexnow':
            return Response(200)
        self.assertEqual('https://yandex.com/indexnow', request.full_url)
        if self.on_yandex:
            self.on_yandex()
        if self.yandex_status not in (200, 202):
            raise HTTPError(request.full_url, self.yandex_status, 'temporary failure', None, None)
        return Response(self.yandex_status)

    def state(self):
        self.assertTrue(self.state_path.exists(), 'Independent Yandex queue must be persisted')
        return json.loads(self.state_path.read_text(encoding='utf-8'))

    def test_global_success_does_not_acknowledge_failed_yandex_versions(self):
        self.change()
        daily.submit_indexnow()
        state = self.state()
        self.assertEqual({ORIGIN + RU_PATHS[0]: NEW}, state['pending'])
        self.assertEqual({}, state['acknowledged'])
        global_ack = json.loads((self.tools / 'indexnow-submitted.json').read_text())
        self.assertEqual(NEW, global_ack[ORIGIN + RU_PATHS[0]])
        self.assertEqual(NEW, global_ack[ORIGIN + '/en/'])

    def test_yandex_receives_only_changed_ru_while_global_keeps_multilingual_payload(self):
        self.change()
        daily.submit_indexnow()
        global_payload, yandex_payload = [payload for _, payload in self.calls]
        self.assertEqual([ORIGIN + RU_PATHS[0], ORIGIN + '/en/'], global_payload['urlList'])
        self.assertEqual([ORIGIN + RU_PATHS[0]], yandex_payload['urlList'])

    def test_pending_retries_when_global_has_no_new_versions(self):
        self.change()
        daily.submit_indexnow()
        self.calls.clear()
        self.yandex_status = 200
        daily.submit_indexnow()
        self.assertEqual(['https://yandex.com/indexnow'], [url for url, _ in self.calls])
        self.assertEqual({}, self.state()['pending'])
        self.assertEqual({ORIGIN + RU_PATHS[0]: NEW}, self.state()['acknowledged'])

    def test_legacy_baseline_does_not_resend_the_three_unchanged_webmaster_urls(self):
        daily.submit_indexnow()
        state = self.state()
        self.assertEqual([], self.calls)
        self.assertEqual('legacy_shared', state['baseline_provenance'])
        self.assertEqual({ORIGIN + p: OLD for p in RU_PATHS}, state['legacy_shared'])
        self.assertEqual({}, state['acknowledged'])
        self.assertEqual({}, state['pending'])

    def test_newer_changed_version_replaces_failed_pending_version(self):
        self.change()
        daily.submit_indexnow()
        self.change(LATER)
        daily.submit_indexnow()
        self.assertEqual({ORIGIN + RU_PATHS[0]: LATER}, self.state()['pending'])
        self.assertEqual([ORIGIN + RU_PATHS[0]], self.calls[-1][1]['urlList'])

    def test_acceptance_acknowledges_only_the_payload_version(self):
        self.change()
        self.yandex_status = 202

        def newer_build_while_request_is_in_flight():
            self.change(LATER)
            from fluxixo_site.tools import yandex_indexnow
            yandex_indexnow.prepare(self.root, self.dist)

        self.on_yandex = newer_build_while_request_is_in_flight
        daily.submit_indexnow()
        state = self.state()
        self.assertEqual({ORIGIN + RU_PATHS[0]: NEW}, state['acknowledged'])
        self.assertEqual({ORIGIN + RU_PATHS[0]: LATER}, state['pending'])

    def test_foreign_and_non_ru_urls_are_rejected_before_any_request(self):
        for unsafe in ('https://other.example/catalog/', ORIGIN + '/en/',
                       ORIGIN + '/catalog/?page=2', ORIGIN + '/products/../catalog/'):
            with self.subTest(unsafe=unsafe):
                self.sitemap('sitemap-ru.xml', [unsafe])
                with self.assertRaises(ValueError):
                    daily.submit_indexnow()
                self.assertEqual([], self.calls)

    def test_pending_removed_route_is_not_submitted(self):
        self.change()
        daily.submit_indexnow()
        self.sitemap('sitemap-ru.xml', list(RU_PATHS[1:]))
        self.calls.clear()
        daily.submit_indexnow()
        self.assertEqual([], self.calls)
        self.assertEqual({}, self.state()['pending'])

    def test_build_persists_queue_before_release_is_built_for_commit(self):
        self.change()
        observed = []

        def build_step(command, **_):
            if str(command[1]).endswith('build_release.py'):
                observed.append(self.state()['pending'])

        with patch('sys.argv', ['fluxixo_daily_rotate.py', '--add', '0']), \
             patch.object(daily.subprocess, 'run', side_effect=build_step):
            daily.main()
        self.assertEqual([{ORIGIN + RU_PATHS[0]: NEW}], observed)
        self.assertEqual([], self.calls)

    def test_failed_deployment_leaves_prepared_queue_on_disk(self):
        self.change()
        with patch('sys.argv', ['fluxixo_daily_rotate.py', '--add', '0', '--deploy']), \
             patch.object(daily.subprocess, 'run'), \
             patch.object(daily, 'deploy_release', side_effect=RuntimeError('deployment failed')):
            with self.assertRaisesRegex(RuntimeError, 'deployment failed'):
                daily.main()
        self.assertEqual({ORIGIN + RU_PATHS[0]: NEW}, self.state()['pending'])
        self.assertEqual([], self.calls)


if __name__ == '__main__':
    unittest.main()
