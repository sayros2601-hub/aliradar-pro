# DealVault

Production: https://dealvault.pages.dev

Legacy address: https://dealvault.surge.sh (same catalog, canonical URLs point to Cloudflare).

The source lives here. Only `dist/` is published. `index.html` in the source root redirects to production; it is not the build artifact. Historical generators, old mock data builders, screenshots and old broadcasts are preserved in `legacy/` and are not used by the pipeline.

## Run

Python 3.12+ and Node 22 are sufficient. All runtime services used by this version are free; there is no paid API or advertising integration.

```powershell
python -m pip install -r requirements.txt
npm ci --ignore-scripts
python dealvault_pipeline.py --offline
python preview_server.py
```

Open http://127.0.0.1:8080 to preview. A normal update with live destination checks and a dated currency snapshot is:

```powershell
python dealvault_pipeline.py --rotate 7
```

Publish with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in the environment and `npm run deploy`. `SURGE_TOKEN` is used only for the legacy mirror. Never publish the source directory. The GitHub Actions workflow publishes the same validated `dist/` artifact after a push to `main`, or once a day at 06:00 UTC. The Cloudflare token has Pages Write only and expires October 21, 2027; replace the GitHub secret before then. Concurrent production jobs are serialized. PR builds never receive the deployment secret. GitHub is used for source and CI, not for hosting this commercial catalog on GitHub Pages.

## Catalog integrity

- `data/products.json` is the active catalog. Original affiliate shortlinks are preserved exactly, including any existing query parameters. Undocumented attribution parameters are not appended.
- The imported prices are **unverified reference estimates**, not current offers. No old-price discounts, unverified ratings, stock assertions, coupon promises or customs guarantees are published.
- `RESOLVED` means the affiliate URL leads to a specific product URL. It does **not** verify stock, shipping, price, quality, eligibility or commission credit. Timeouts, CAPTCHA, 403 and inconclusive 200 responses are `UNKNOWN`, never deletion signals.
- `data/link_health_report.json` is a non-destructive audit. A specific unavailable/mismatched URL is withheld from the public build. If an unusual number of URLs fail, the builder refuses to replace the last artifact.
- The initial migration quarantined seven unrelated products sharing one affiliate URL and all 35 reserve placeholders in `data/quarantine.json`.
- New reserve entries must have an original Portals link, actual item ID, source evidence, local images, four translated titles, a valid price, `source: "portals"` and `reviewed: true`. They must pass a fresh destination check before rotation. Rotation preserves the configured catalog size, is idempotent per UTC date, and uses a recoverable journal. With no reviewed candidates it does nothing.
- The Studio harvester now stages actual captured records in `data/portals_inbox.json` through `import_portals.py`. It does not invent product titles from search queries or pretend that a missing session is working. Newly captured products still need editorial review and real images before entering the reserve.
- No new product discovery, revenue analytics, commission validation, independent product testing, or revenue increase is claimed by this build.

## Browser behavior

EN is the default. RU, HE (RTL) and ES have static, crawlable URLs with reciprocal hreflang and self-canonical links. The catalog and original outbound links work without JavaScript. The script adds search, category/budget filters, sorting, approximate currency display, theme selection, native dialog focus handling and sharing of the actual localized product page.

No third-party analytics are enabled. Browser storage is optional and failure-safe. Currency rates are fetched once per update, cached with the actual provider date, and attributed to ExchangeRate-API. Network failures preserve the old dated snapshot or fall back to USD.

## Local marketing tools

`broadcasts/current/dealvault_*.csv` contains drafts, without scheduling or claims of universal CSV importer compatibility. `promo_dispatcher.html` is a local copy desk. Neither is deployed publicly.

`telegram_mass_poster.py` and `vk_mass_poster.py` preview by default. Actual sending requires `--send`, credentials and an explicit channel/owner. They use plain text, preserve affiliate URLs, stop on ambiguous outcomes and log acknowledged posts to avoid repeats. The website update workflow never invokes them. No social messages were sent during this repair.

## Verify

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python verify_site.py
python -m pip install playwright
python -m playwright install chromium
python tests/browser_qa.py --output .qa
```

Tests use a hidden browser and localhost. They cover network failure classification, data validation, safe JSON embedding, dry-run immutability, rotation/recovery, all four locales, 16 viewport/locale combinations, search/filter/sort, modal keyboard handling, original affiliate URLs, sharing, disabled storage and disabled JavaScript.

## Operational limits

The imported dataset does not contain reliable timestamps or evidence for live seller prices, ratings or offers. Those fields cannot honestly be presented as verified. A real editorial contact address has not been supplied, so the site does not fabricate an email address. Order support points users to their AliExpress account. Affiliate income must be checked in the user's Portals dashboard; outbound clicks are not sales.

The old free `dealvault.surge.sh/robots.txt` endpoint was observed returning a platform-generated `Disallow: /` even though the uploaded file allows crawling; the correct uploaded file is served with a query string. This was resolved by migrating production to Cloudflare Pages; the public `https://dealvault.pages.dev/robots.txt` endpoint was verified as `Allow: /`. This permits crawling but does not guarantee ranking or indexing. Public routes, canonical links and sitemap use Cloudflare's extension-less URLs. GitHub Pages is not used for this commercial catalog.
