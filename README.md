# DealVault

Production: https://dealvault.pages.dev

Legacy address: https://dealvault.surge.sh (same catalog, canonical URLs point to Cloudflare).

The source lives here. Only `dist/` is published. `index.html` in the source root redirects to production; it is not the build artifact. Historical generators, old mock data builders, screenshots and old broadcasts are preserved in `legacy/` and are not used by the pipeline.

## Run

Python 3.12+ and Node 22 are sufficient. All runtime services used by this version are free; there is no paid API or advertising integration.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
npm ci --ignore-scripts
.\.venv\Scripts\python dealvault_pipeline.py --offline
.\.venv\Scripts\python preview_server.py
```

Open http://127.0.0.1:8080 to preview. The current scheduled workflow updates public currency data, then runs the offline pipeline. Marketplace collection and network rotation are not enabled in this release; live access was blocked during the audit. `--offline --rotate` is rejected before any files or network checks are touched. The selection engine still evaluates imported evidence and its freshness each day, but a successful build does not mean new products were collected.

Publish with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in the environment and `npm run deploy`. `SURGE_TOKEN` is used only for the legacy mirror. Never publish the source directory. The GitHub Actions workflow publishes the same validated `dist/` artifact after a push to `main`, or once a day at 06:00 UTC. The Cloudflare token has Pages Write only and expires October 21, 2027; replace the GitHub secret before then. Concurrent production jobs are serialized. PR builds never receive the deployment secret. GitHub is used for source and CI, not for hosting this commercial catalog on GitHub Pages.

## Catalog integrity

Use the project's isolated Python environment for all Python commands below. Pillow is pinned to 13.0.0 after reviewing published advisories for 12.3.0. Only static JPEG, PNG, WebP and AVIF photos are decoded; inputs are capped at 20 MB and 20 megapixels. The imported photos are AVIF data with old .jpg names; public legacy photo URLs are now re-encoded to match their extension for social-platform compatibility. Changing the image-pipeline version invalidates old optimized-image caches. Other Python projects do not need to change their Pillow installation.

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

Cloudflare Web Analytics was enabled in the Pages dashboard; the beacon is injected on deployment. It measures visits and loading performance, not AliExpress orders or commissions. The privacy page describes it and all saved preferences. Browser storage is optional and failure-safe. Currency rates are fetched once per update, cached with the actual provider date, and attributed to ExchangeRate-API. Network failures preserve the old dated snapshot or fall back to USD.

## Offline adapter (October 22, 2026)

`dealvault_adapter.py status --json`, `validate-import --file <inbox-file.json> --offline` and `stage-import --file <inbox-file.json> --offline` support bounded, pending observations. Both import paths use a shared queue lock; corrupt queues are preserved, and timestamps and original URLs remain distinct from import time. Exact repeat observations deduplicate, while fresh observations of the same link are retained. Local captures and the queue are ignored by Git. See `README_ADAPTER_RU.txt` for the contract and limitations.

This adapter has no enabled browser/account access, live harvesting, API search or financial-summary operation. `check-session` returns a disabled-access result without opening a browser. A new wrapper is not authorization to bypass an existing tool restriction. The legacy `import_portals.py` also defaults to offline and no longer includes a network checker.

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
- Free shipping is optional. Shipping fees and promotional shipping conditions do not block admission or change the score; buyers check final terms on AliExpress. The site does not promise free shipping. Offer, stock and delivery observations expire after 24 hours.
- Rating, review count and seller-feedback evidence; negative-review and compatibility/safety review. These are screening thresholds, not a guarantee of quality.
- A documented useful task, a drawback, and comparison with two distinct alternatives. Advertising placement and affiliate commission do not enter the score.
- Fresh country-specific demand evidence (30 days) with sufficient weekly coverage. Partial current weeks and duplicate weeks are excluded. Normalized magnitudes are not compared across countries.
- A country-specific advertising-library review (7 days). High or unknown observed saturation blocks admission. A limited ad-library search cannot establish that a product is unadvertised everywhere.
- Concise use and compatibility text in each of the four languages. Only the selected language appears on the site.

At most two new items in one category and one in one use-case group enter a daily batch. Duplicate item IDs are rejected even if affiliate shortlinks differ. An empty qualified queue leaves the active catalog untouched. The original 35 products remain reference listings, **not certified free-shipping offers**; no free-shipping badge has been added to them.

Run `python product_selection.py` for the decision report and research leads. `data/selection_report.json` is updated by the daily pipeline. Research observations and editorial decisions are refreshed through the assistant/editor; the scheduled job rechecks freshness but does not invent new research. `data/demand_snapshots.json` contains only sanitized public chart data, never account details or browser sessions. Initial limited comparisons cover US, Israel, Germany, Spain and Russia; low-data markets are explicitly inconclusive, not zero demand. These five countries are not a claim of Europe/CIS-wide coverage.

Studio integration copies are in `integrations/studio/`. The installed files on the desktop were also repaired: no fabricated balance, no fixed cat-toy query, explicit candidate index, and up to three candidates per evidence-led query. Captures enter the inbox without automatic editorial approval. The live AliExpress browser pass was blocked by the browser tool's site-safety policy during this revision and was not bypassed. Syntax and offline pipeline behavior were tested; current live selectors, account session, country-specific shipping and stock remain unverified. Do not treat this as an unattended, fully validated shopping robot.

References: [Google Trends data limits](https://support.google.com/trends/answer/4365533?hl=en), [helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [efficient animation](https://web.dev/articles/animations-guide), [Core Web Vitals](https://web.dev/articles/vitals). Lab performance scores do not establish real-user Core Web Vitals or Google ranking.

## Whole-system audit and recovery

`data/published_routes.json` stores only the slug and translated titles of previously published products. When a product leaves the collection, its URL becomes a localized, noindex archive page linking to current finds, with no stale price or purchase button. Archive pages stay out of the sitemap. This preserves the destination of old social shares without claiming an old offer is still valid.

Every non-PR release now saves the tested catalog snapshots to Git before publishing. A rejected Git push stops publication; it never force-pushes over another change. Non-scheduled CI artifacts are retained for 3 days; daily scheduled builds do not accumulate extra artifact copies. Keep local release archives for longer recovery. A mirror failure is separately flagged and does not discard a verified primary release. After Cloudflare deployment, `verify_deployment.py` checks exact build metadata/static assets, all four languages, the injected analytics beacon, response headers, a product landing page and 404 responses for private paths. It contacts only DealVault. GitHub artifact storage is account-limited even for public repositories; do not enable paid overages to retain more archives.

If a release fails after upload, use Cloudflare Pages → DealVault → Deployments → a previously successful production deployment → rollback, then verify the public root, robots.txt and product page. Keep the corresponding Git commit/artifact together. Revert the faulty source commit before the next scheduled deployment, otherwise the schedule can republish it. Never use an old archive containing an exposed credential. Git source and a private encrypted credential backup are separate recovery assets; DPAPI files alone may not decrypt on a different Windows account or computer.

Cloudflare Web Analytics activation does not create affiliate sales attribution. The public Search Console verification tag is stored in `data/site_integrations.json`; ownership confirmation and sitemap submission are external account steps and should be verified in Google. No OAuth credential or account secret belongs in that file.

## Private business report

Run `python business_health.py` to generate `.local/business/dashboard.html` and `health.json`. They are ignored by Git and excluded from `dist/`. The report reads real catalog/selection snapshots and an optional local `.local/business/periods.json`. It does not fetch account balances or fabricate revenue. See `BUSINESS_PLAYBOOK_RU.txt` for the operating plan, growth gates, limits and sources.

The ledger starts as `{"periods": []}`. Each non-overlapping completed/current period may contain `start`, `end` (YYYY-MM-DD), `currency` (`USD`), and nullable `visits`, `partner_clicks`, `orders`, `approved_commission`, `paid_commission`, `ad_spend`, `other_costs`. Every measured field, including zero, needs a corresponding nonempty `evidence` reference to a private aggregate report. Do not store customer identities or order-level personal data. Null means unmeasured. Do not mix daily observations with cumulative totals.

Only explicitly matched attribution cohorts (`attribution_scope: "matched_cohort"`) can produce approved commission per partner click. A site visit count and a whole-account affiliate click count are not a valid site conversion funnel. Cash after recorded costs uses paid commission minus advertising and other recorded costs; it excludes tax and owner time. Pending or merely approved commission is not available cash. There is no automated reinvestment or paid advertising.


## Integrity repair — October 23, 2026

The handoff folder contains five summaries, not a full conversation export. Their claims are historical assertions, not evidence of current account approval or live sales.

- The active catalog contains 994 reference listings after retaining 13 problematic records in `data/audit_quarantine_20261023.json`: seven fabricated AI product identities/affiliate links, four duplicate marketplace item IDs, and two unrelated fallback photos. Original routes remain localized noindex archives without purchase buttons. Marketplace identity and duplicate IDs are now enforced by catalog validation.
- Rotation requires `decision.eligible`; `reviewed: true` and `source: portals` cannot override missing current evidence. Category/use-case quotas follow the configured policy, and rotation preserves the current catalog size. A configured cap is not an instruction to silently discard products.
- Ordinary Merchant Center does not permit affiliate redirects, except for approved CSS arrangements. DealVault has no established CSS eligibility or direct checkout. Both existing merchant URLs deliberately serve empty withdrawal feeds, instead of invented stock, free shipping, own-brand assertions and current-price claims. Google Search indexing and the ordinary RSS feeds remain available. Existing imported items may remain in Google/Microsoft accounts until those services process their source updates. No account approval is claimed.
- The validated builder always generates returns help in four languages, the public IndexNow key, and both withdrawal feeds. They cannot disappear on the next normal build. Returns help explains seller-specific terms and does not promise universal 30-day returns, free shipping or fixed refund deadlines.
- RSS enclosures identify actual WebP files and their exact byte lengths. New-arrival status is preserved in the browser payload; decorative question marks were repaired. Saved lists support the full catalog, and a missing rate date never becomes January 1970.
- Bulk placeholder titles were translated from the imported English titles. Provenance distinguishes machine translation and editorial translation; this does not verify seller claims, exact variants or product quality. All stored prices remain unverified references. Derived currency fields are recalculated from the same dated USD snapshot. The non-idempotent price recalibration scripts and fabricated-product insertion script are retired.
- `traffic_audit.py` measures public HTTP/content health, appends snapshots atomically and preserves corrupt history. Traffic and private account status remain unmeasured unless actual evidence is supplied. The old scratch entry point delegates to it. Historical hard-coded metrics are explicitly labelled as unverified.
- A complete affiliate destination pass returned 501 matching product destinations and 493 inconclusive responses. Unknown responses are retained, and none is presented as confirmed stock or valid current pricing. This pass itself is test activity and must not be counted as organic demand.

The pre-repair source/data archive and original working-tree diff are stored locally under `.local/codex-audit-20261023T153454Z/`. They include the unsafe original scripts for recovery/reference. Credentials were not added to the archive or Git. Existing daily commits were reconciled by preserving route history and rotation logs; repaired local catalog data is the authoritative replacement.


## Search channel connection follow-up

`search_integrations.py` reproduces the public Bing ownership XML and four language-specific maps plus `sitemap-index.xml`, all based on the canonical `sitemap.xml`. Robots advertises both maps. Archived pages remain excluded. The added maps support separate processing diagnostics; their existence alone does not establish Google ingestion.

The release workflow captures the previous public catalog before building, then `submit_indexnow.py --submit` notifies participating engines after the public release passes verification. Unchanged catalog hashes send nothing. New, changed and retired English feed entries notify all four language URLs and the four homepages. A localized-only catalog change uses the current canonical map. Missing prior observations fail explicitly; an initial full notification requires an explicit `--force --submit`. HTTP 200 is receipt, HTTP 202 is pending key validation, and neither means indexing. There is no Google Indexing API abuse and no paid account integration.

The old Pinterest launcher that forcibly killed all Chrome processes and enabled broad remote debugging is retired. Browser/account setup and RSS publication must be verified through the actual Pinterest business account; clicking an arbitrary Save button is not proof of successful scheduling.
