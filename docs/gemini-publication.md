# Gemini text and reviewed product media

The scheduled `fluxixo_daily_rotate.yml` workflow uses the existing shared
`fluxixo-daily-accumulation` lock and always checks out current `main`.

## Credentials and model selection

Create the repository Actions secret `FLUXIXO_TEXT_GEMINI_API_KEY` in
`sayros2601-hub/aliradar-pro`. Its value is never checked into this repository.
Only trusted preparation and explicitly dispatched smoke steps receive it.
The owner has confirmed that its Gemini project has billing disabled.

- Text: `gemini-3.5-flash-lite`, `thinkingConfig.thinkingLevel=HIGH`.
- Photo assessment: `gemini-3.8-flash`, `HIGH`.
- Text selection is explicit: `FLUXIXO_TEXT_PROVIDER=gemini`.
- No other model/provider is attempted after a Gemini failure.
- Existing language, source-title, numerical-claim and catalog similarity gates
  remain in place. These checks are not proof that every product claim is true.

The local durable ledger limits this pipeline to 480 text and 18 photo requests
per rolling 24 hours, spaced by at least 4.1 / 12.1 seconds respectively.
It includes failed or response-lost requests. Other clients can consume the
project's remaining allowance; 429 honors Retry-After and defers without fallback.
The code cannot independently enforce the Google project's billing setting.

## Shared Workers Paid budget

Cloudflare's account analytics is delayed/adaptively sampled, and other clients
can spend neurons concurrently. It is not an atomic reservation of free usage.
Consequently the production reviewed-media path does **not** supply a FLUX
generator or a positive free-budget authorization. It cannot call the legacy
Worker/direct-FLUX fallback. Existing unrelated Workers jobs are not modified;
this is not a promise of a zero bill for the entire account.

The automatically selected safe path uses distinct genuine seller references,
alpha-only background matting and transparent padding. Product RGB pixels and
geometry are retained; no recoloring, invented view or fake effect is used.
Each final lossless WebP is reviewed against its exact source and the preceding
accepted frames. Roles are product, application, supported result (or a genuinely
informative functional detail where a result cannot be photographed truthfully).

An optional generator interface exists for a future verified account-wide budget
allocator: one 9B hero and two 4B slots, with bounded correction. It is not enabled
in the production workflow. A manual environment flag cannot authorize paid FLUX.

## Recovery and publication gate

Candidate retry data: `data/fluxixo_pending.sqlite3`.
Gemini reservations/backoff: `data/fluxixo_gemini_usage.sqlite3`.
Exact source/output files and assessments: `fluxixo_site/reserve/reviewed-media/`.

With `FLUXIXO_DURABLE_CHECKPOINT=git`, candidates and request reservations are
pushed before calls; accepted frames and deferred state are pushed afterwards.
Only allowlisted internal state/assets are committed, never the working catalog.
If checkpointing fails, further AI calls stop. A crash after the provider consumed
a request but before its response was saved may require a new review; the old
request remains charged against the conservative local quota, and its output is
never treated as approved.

Leases expire; due candidates are selected oldest-first and excluded from new
discovery. A rejected frame gets at most one alternate-reference/correction
attempt per invocation. Already accepted unchanged frames survive retries.
Unchanged rejected sources are not repeatedly rematted; unavailable/changed
sources are refreshed on the delayed retry. Status and next attempt are internal.

New catalog entries carry review policy version, exact output/source SHA256,
source-title hash and prior-frame hashes. The release gate checks the same bytes
again. Private seller references remain in `dist/assets/originals/` for verification
and are excluded from public Pages deployment. Existing catalog entries are not
mass-updated. Verified partial batches can publish in the existing publication
window; unfinished candidates remain queued for later runs/days.

The existing preparation cron is supplemented with hourly recovery through the
existing daily window. GitHub scheduling/service outages can delay execution.
If a seller has no truthful distinct application/result references, the item waits
with `awaiting_distinct_source` and a scheduled refresh rather than publishing
invented or duplicate imagery. Publication cannot be guaranteed without suitable
sources and available review quota.

## Isolated validation

The manually dispatched `fluxixo_text_smoke.yml` accepts an existing catalog
ID with a seller reference and three images. It validates a copy in six
languages, then reviews the existing hero, application and result in order.
Each assessment includes the canonical product identity, slot reference and
previously accepted images. A rejection or deferred request stops later frames.
The artifact reports individual decisions and hashes. Checkpoints include
quota reservations, cached copy and exact-version assessments. The smoke
workflow has no deployment step.
