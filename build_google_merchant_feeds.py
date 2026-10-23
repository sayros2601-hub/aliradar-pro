"""Withdraw unsupported merchant offers; affiliate discovery remains in RSS.
Ordinary Merchant Center requires direct checkout; DealVault has none.
https://support.google.com/merchants/answer/12756116
"""
from pathlib import Path
import xml.etree.ElementTree as ET
from dealvault_core import BASE_DIR, DOMAIN


def build_google_feed(lang='en', currency='USD', country='US', output=None):
    if lang not in ('en', 'es'):
        raise ValueError('Unsupported merchant feed language')
    root = Path(output or BASE_DIR / 'dist')
    root.mkdir(parents=True, exist_ok=True)
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in (
        ('title', 'DealVault — merchant offers withdrawn'),
        ('link', DOMAIN + ('/' if lang == 'en' else '/es/')),
        ('description', 'No merchant offers: DealVault is an affiliate discovery catalog. '
         'Direct checkout and verified merchant eligibility are not established. '
         'Reference prices are not current seller offers.'),
    ):
        ET.SubElement(channel, key).text = value
    path = root / ('google_feed.xml' if lang == 'en' else f'google_feed_{lang}.xml')
    ET.ElementTree(rss).write(path, encoding='utf-8', xml_declaration=True)
    return path


def main():
    build_google_feed()
    build_google_feed(lang='es', currency='EUR', country='ES')
    print('[Merchant] Empty withdrawal feeds saved. No unsupported offers exported.')


if __name__ == '__main__':
    main()
