CREATE TABLE IF NOT EXISTS listings(
  key text PRIMARY KEY,
  company text NOT NULL,
  ats text,
  title text NOT NULL,
  location text,
  mode text NOT NULL CHECK (mode IN ('bay','remote')),
  is_sf boolean NOT NULL DEFAULT false,
  apply_url text NOT NULL,
  posted_at timestamptz,
  first_seen timestamptz NOT NULL,
  last_seen timestamptz NOT NULL,
  baseline boolean NOT NULL DEFAULT false,
  effective_at timestamptz,
  closed boolean NOT NULL DEFAULT false,
  years_req int,
  score int NOT NULL DEFAULT 0,
  score_detail jsonb,
  pay text,
  snippet text,
  description text,
  source_endpoint text
);
CREATE INDEX IF NOT EXISTS listings_eff ON listings(effective_at DESC);
CREATE INDEX IF NOT EXISTS listings_src ON listings(source_endpoint);
CREATE TABLE IF NOT EXISTS marks(
  key text PRIMARY KEY REFERENCES listings(key) ON DELETE CASCADE,
  applied_at timestamptz,
  contacted_at timestamptz,
  contact_note text
);
CREATE TABLE IF NOT EXISTS boards(
  endpoint text PRIMARY KEY,
  company text,
  first_scan timestamptz,
  last_scan timestamptz,
  last_ok boolean,
  last_error text,
  listing_count int
);
CREATE TABLE IF NOT EXISTS poll_runs(
  id serial PRIMARY KEY,
  started_at timestamptz,
  finished_at timestamptz,
  tier text,
  boards_ok int,
  boards_failed int,
  listings_seen int
);
