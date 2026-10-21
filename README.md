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
- Regional search research is recorded in `data/demand_snapshots.json`; it measures normalized search interest, not purchases. No commission validation, independent product testing, revenue increase or complete coverage of advertising is claimed.

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


## Orbit interface and product selection (October 2026)

The default entry is English, including on Russian-language browsers. Language switching is explicit. Cards contain one short use case; longer compatibility checks are on the product page. Saved items stay on the device. CSS motion respects reduced-motion settings, can be switched off, and pauses outside the viewport or on a hidden page. No animation library or remote font is loaded.

`product_selection.py` creates a regional research plan and evaluates every proposed reserve product before `daily_rotator.py` can publish it. `data/selection_policy.json` contains the editorial thresholds. Each candidate needs:

- Original item identity, reviewed source capture, exact variant and destination.
- Explicit free shipping with zero minimum order, no new-customer requirement, paid membership or conditional bundle. Offer, stock and delivery observations expire after 24 hours. Unknown is not free.
- Rating, review count and seller-feedback evidence; negative-review and compatibility/safety review. These are screening thresholds, not a guarantee of quality.
- A documented useful task, a drawback, and comparison with two distinct alternatives. Advertising placement and affiliate commission do not enter the score.
- Fresh country-specific demand evidence (30 days) with sufficient weekly coverage. Partial current weeks and duplicate weeks are excluded. Normalized magnitudes are not compared across countries.
- A country-specific advertising-library review (7 days). High or unknown observed saturation blocks admission. A limited ad-library search cannot establish that a product is unadvertised everywhere.
- Concise use and compatibility text in each of the four languages. Only the selected language appears on the site.

At most two new items in one category and one in one use-case group enter a daily batch. Duplicate item IDs are rejected even if affiliate shortlinks differ. An empty qualified queue leaves the active catalog untouched. The original 35 products remain reference listings, **not certified free-shipping offers**; no free-shipping badge has been added to them.

Run `python product_selection.py` for the decision report and research leads. `data/selection_report.json` is updated by the daily pipeline. Research observations and editorial decisions are refreshed through the assistant/editor; the scheduled job rechecks freshness but does not invent new research. `data/demand_snapshots.json` contains only sanitized public chart data, never account details or browser sessions. Initial limited comparisons cover US, Israel, Germany, Spain and Russia; low-data markets are explicitly inconclusive, not zero demand. These five countries are not a claim of Europe/CIS-wide coverage.

Studio integration copies are in `integrations/studio/`. The installed files on the desktop were also repaired: no fabricated balance, no fixed cat-toy query, explicit candidate index, and up to three candidates per evidence-led query. Captures enter the inbox without automatic editorial approval. The live AliExpress browser pass was blocked by the browser tool's site-safety policy during this revision and was not bypassed. Syntax and offline pipeline behavior were tested; current live selectors, account session, country-specific shipping and stock remain unverified. Do not treat this as an unattended, fully validated shopping robot.

References: [Google Trends data limits](https://support.google.com/trends/answer/4365533?hl=en), [helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [efficient animation](https://web.dev/articles/animations-guide), [Core Web Vitals](https://web.dev/articles/vitals). Lab performance scores do not establish real-user Core Web Vitals or Google ranking.
