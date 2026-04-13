-- Run this SQL in your Supabase SQL editor to create the required table.

CREATE TABLE IF NOT EXISTS fellowships (
    id          TEXT        PRIMARY KEY,   -- fellowship URL used as unique key
    title       TEXT        NOT NULL,
    url         TEXT        NOT NULL,
    date        TEXT,                      -- publication date (raw string)
    deadline    TEXT,                      -- application deadline (raw string)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optional: index for fast existence checks
CREATE INDEX IF NOT EXISTS idx_fellowships_id ON fellowships (id);
