"""Automatically syndicate FLUXIXO RSS feed and all 501 multilingual URLs to IndexNow, WebSub/PubSubHubbub, and open RSS directories without requiring user accounts."""
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ORIGIN = "https://www.fluxixo.shop"
HOST = "www.fluxixo.shop"
KEY = (Path(__file__).resolve().parent / "indexnow-key.txt").read_text(encoding="utf-8").strip()
KEY_LOCATION = f"{ORIGIN}/{KEY}.txt"
RSS_URL = f"{ORIGIN}/rss.xml"
SITEMAP_URL = f"{ORIGIN}/sitemap.xml"

def syndicate_all():
    results = {"indexnow": [], "websub_and_rss_pings": []}

    req = urllib.request.Request(SITEMAP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        sm_xml = r.read().decode("utf-8")

    root = ET.fromstring(sm_xml)
    urls = [el.text.strip() for el in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if el.text]
    for extra in [RSS_URL, SITEMAP_URL, f"{ORIGIN}/google_feed.xml", f"{ORIGIN}/pinterest-feed.csv", f"{ORIGIN}/social-feed.json"]:
        if extra not in urls:
            urls.append(extra)

    payload = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls
    }).encode("utf-8")

    for name, ep in [
        ("IndexNow Global Hub (Bing/DuckDuckGo/Yahoo)", "https://api.indexnow.org/indexnow"),
        ("Microsoft Bing Direct", "https://www.bing.com/indexnow"),
        ("Yandex Direct", "https://yandex.com/indexnow"),
        ("Seznam Direct", "https://search.seznam.cz/indexnow"),
    ]:
        try:
            r = urllib.request.Request(ep, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
            with urllib.request.urlopen(r, timeout=15) as resp:
                results["indexnow"].append({"engine": name, "status": resp.getcode(), "urls": len(urls)})
        except urllib.error.HTTPError as e:
            results["indexnow"].append({"engine": name, "status": e.code, "urls": len(urls)})
        except Exception as e:
            results["indexnow"].append({"engine": name, "error": str(e)})

    for name, hub in [
        ("Google PubSubHubbub / WebSub Hub", "https://pubsubhubbub.appspot.com/"),
        ("Superfeedr Open WebSub Hub", "https://pubsubhubbub.superfeedr.com/"),
    ]:
        try:
            form = urllib.parse.urlencode({"hub.mode": "publish", "hub.url": RSS_URL}).encode("utf-8")
            r = urllib.request.Request(hub, data=form, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
            with urllib.request.urlopen(r, timeout=15) as resp:
                results["websub_and_rss_pings"].append({"hub": name, "status": resp.getcode()})
        except Exception as e:
            results["websub_and_rss_pings"].append({"hub": name, "error": str(e)})

    xml_rpc_body = f"""<?xml version="1.0"?>
<methodCall>
  <methodName>weblogUpdates.extendedPing</methodName>
  <params>
    <param><value><string>FLUXIXO — Curated AliExpress Finds</string></value></param>
    <param><value><string>{ORIGIN}/</string></value></param>
    <param><value><string>{ORIGIN}/catalog/</string></value></param>
    <param><value><string>{RSS_URL}</string></value></param>
  </params>
</methodCall>""".encode("utf-8")

    for name, ep in [
        ("Ping-O-Matic (15+ RSS Directories)", "http://rpc.pingomatic.com/"),
        ("Twingly Global Blog/RSS Index", "http://rpc.twingly.com/"),
    ]:
        try:
            r = urllib.request.Request(ep, data=xml_rpc_body, headers={"Content-Type": "text/xml", "User-Agent": "FLUXIXO-RSS-Pinger/1.0"}, method="POST")
            with urllib.request.urlopen(r, timeout=12) as resp:
                results["websub_and_rss_pings"].append({"hub": name, "status": resp.getcode()})
        except Exception as e:
            results["websub_and_rss_pings"].append({"hub": name, "error": str(e)})

    return results

if __name__ == "__main__":
    print(json.dumps(syndicate_all(), indent=2, ensure_ascii=False))
