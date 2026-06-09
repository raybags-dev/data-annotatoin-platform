# Backend — FastAPI

Python 3.11 + FastAPI. Connects to Supabase Postgres for structured data and Supabase Storage for raw files.

## Structure

```
app/
├── api/v1/endpoints/   # Route handlers (datasets, pipeline, annotations, exports, dashboard)
├── core/               # Config, database (Supabase client), storage
├── models/             # Pydantic schemas
├── pipeline/           # Ingest / Validate / Clean / Label stages
├── repositories/       # Data access layer (DatasetRepository, AnnotationRepository)
└── services/           # ExportService
```

## Running locally

```bash
pip install -e .
uvicorn app.main:app --reload --port 8001
```

Environment variables (see `../.env.example`):
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_KEY` — Supabase service role key
- `SUPABASE_BUCKET` — Storage bucket name (`portfolio-base-bucket`)
- `OLLAMA_URL` — Ollama API URL (default `http://localhost:11434`)
- `SECRET_KEY` — App secret

## Dockerfile

Multi-stage build. Production image runs `uvicorn` on port 8001.
