export interface Dataset {
  id: string
  name: string
  filename: string
  file_type: string
  storage_path: string
  status: string
  row_count: number
  column_count: number
  columns: string[]
  validation_report?: ValidationReport
  cleaning_report?: CleaningReport
  labeling_config: LabelingConfig
  processing_history: ProcessingEntry[]
  created_at: string
  updated_at: string
  file_size_bytes?: number
  kaggle_handle?: string
}

export interface ValidationReport {
  total_rows: number
  duplicate_rows: number
  missing_value_counts: Record<string, number>
  schema_fields: Record<string, SchemaField>
  issues: string[]
}

export interface SchemaField {
  dtype: string
  nullable: boolean
  unique_count: number
  sample_values: string[]
}

export interface CleaningReport {
  rows_before: number
  rows_after: number
  duplicates_removed: number
  missing_filled: number
  missing_dropped: number
  text_normalized: number
}

export interface LabelingConfig {
  categories: string[]
  model: string
  label_column_hint?: string
}

export interface ProcessingEntry {
  stage: string
  status: string
  started_at: string
  completed_at?: string
  metrics: Record<string, unknown>
  error?: string
}

export interface DataRecord {
  id: string
  dataset_id: string
  row_index: number
  raw_data: Record<string, unknown>
  cleaned_data: Record<string, unknown>
  annotation?: Annotation
}

export interface Annotation {
  label: string
  confidence: number
  model: string
  reasoning: string
  human_reviewed: boolean
  human_label?: string
  status: string
  reviewed_at?: string
}

export interface KaggleDataset {
  ref: string        // "owner/dataset-slug"
  title: string
  subtitle?: string | null
  size?: number | null
  last_updated: string
  download_count: number
  vote_count: number
  url: string
}

export interface KaggleFile {
  filename: string  // relative path inside archive
  size: number
  type: string      // csv | json | xlsx | xls
}

export interface KaggleDownloadResult {
  download_id: string
  handle: string
  files: KaggleFile[]
}

export interface KaggleDownloadStatus {
  status: 'pending' | 'ready' | 'error'
  handle: string
  files?: KaggleFile[]
  error?: string
}

export interface DataPreview {
  columns: string[]
  rows: Record<string, unknown>[]
}

export interface StorageSummary {
  total_bytes: number
  dataset_count: number
}

export interface DashboardStats {
  total_datasets: number
  total_records: number
  dataset_status_distribution: Record<string, number>
  annotation_status_distribution: Record<string, number>
  label_distribution: Record<string, number>
  confidence_stats: { avg?: number; min?: number; max?: number }
  recent_datasets: Dataset[]
}
