CREATE TABLE IF NOT EXISTS daily_publish_state (
  day TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  reserved_count INTEGER NOT NULL,
  baseline_count INTEGER NOT NULL,
  utc_day TEXT NOT NULL,
  published_day TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day TEXT NOT NULL,
  catalog_id TEXT NOT NULL UNIQUE,
  product_id TEXT,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seo_telemetry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TEXT NOT NULL,
  engine TEXT NOT NULL,
  indexed_count INTEGER DEFAULT 0,
  submitted_count INTEGER DEFAULT 0,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS studio_generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL,
  view_name TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS redirects (
  source_path TEXT PRIMARY KEY,
  target_path TEXT NOT NULL,
  status_code INTEGER NOT NULL DEFAULT 301
);

CREATE TABLE IF NOT EXISTS cron_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cron TEXT NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,
  details_json TEXT NOT NULL,
  ran_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_daily_ledger_day ON daily_ledger(day);
CREATE INDEX IF NOT EXISTS idx_seo_telemetry_run_at ON seo_telemetry(run_at);
CREATE INDEX IF NOT EXISTS idx_studio_generations_product ON studio_generations(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_cron_runs_ran_at ON cron_runs(ran_at);
