-- Data Annotation Platform — Supabase Postgres migrations

CREATE TABLE IF NOT EXISTS ann_datasets (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  filename    TEXT NOT NULL,
  file_type   TEXT NOT NULL CHECK (file_type IN ('csv', 'json', 'excel', 'txt')),
  storage_path TEXT NOT NULL,
  storage_url  TEXT DEFAULT '',
  status       TEXT DEFAULT 'uploaded',
  row_count    INTEGER DEFAULT 0,
  column_count INTEGER DEFAULT 0,
  columns            JSONB DEFAULT '[]'::jsonb,
  validation_report  JSONB,
  cleaning_report    JSONB,
  labeling_config    JSONB DEFAULT '{"categories": [], "model": "llama3.2:3b"}'::jsonb,
  processing_history JSONB DEFAULT '[]'::jsonb,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ann_records (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id   UUID NOT NULL REFERENCES ann_datasets(id) ON DELETE CASCADE,
  row_index    INTEGER NOT NULL,
  raw_data     JSONB DEFAULT '{}'::jsonb,
  cleaned_data JSONB DEFAULT '{}'::jsonb,
  annotation   JSONB DEFAULT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ann_records_dataset_id ON ann_records(dataset_id);
CREATE INDEX IF NOT EXISTS idx_ann_records_row_index ON ann_records(dataset_id, row_index);
CREATE INDEX IF NOT EXISTS idx_ann_records_ann_status ON ann_records USING GIN (annotation);

-- Allow the service role (used by the backend) to read/write both tables
ALTER TABLE ann_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ann_records  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service role full access on ann_datasets"
  ON ann_datasets FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service role full access on ann_records"
  ON ann_records FOR ALL USING (true) WITH CHECK (true);

-- v2: file size tracking and Kaggle source tracking
ALTER TABLE ann_datasets ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT DEFAULT 0;
ALTER TABLE ann_datasets ADD COLUMN IF NOT EXISTS kaggle_handle TEXT DEFAULT '';
