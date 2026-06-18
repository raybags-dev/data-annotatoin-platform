# Intelligent Data Annotation & Processing Platform

A full-stack data engineering platform for collecting, cleaning, labeling, analyzing, and exporting structured datasets using local LLMs and modern data engineering practices.

## Architecture

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind CSS + TanStack Query |
| Backend | FastAPI + Python 3.11 |
| Database | Supabase Postgres (`ann_datasets`, `ann_records` tables) |
| File storage | Supabase Storage (`portfolio-base-bucket`) |
| AI labeling | Ollama (`llama3.2:3b`) running in Docker |
| CI/CD | GitHub Actions → Docker Hub → VPS (12.345.67.891) |

## Pipeline stages

```
Upload → Ingest → Validate → Clean → Label → Review → Export
```

Each stage is independently re-runnable via `POST /api/v1/pipeline/{id}/stage/{stage}`.

## Getting started

### 1. Supabase setup (one-time)

Run `supabase_migrations.sql` in your Supabase project:  
Supabase dashboard → SQL Editor → New Query → paste → Run

### 2. Local development

```bash
# Backend
cd backend
pip install -e .
cp ../.env.example ../.env   # fill in your values
uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev
```

### 3. Docker Compose (full stack)

```bash
cp .env.example .env   # fill in SUPABASE_URL, SUPABASE_SERVICE_KEY
docker compose up -d

# Pull the llama3.2:3b model (first run only)
docker exec data-annotation-platform-ollama-1 ollama pull llama3.2:3b
```

Services:
- Backend: http://localhost:8001
- Frontend: http://localhost:5174
- API docs: http://localhost:8001/docs

### 4. Production (VPS)

The GitHub Actions workflow builds and deploys automatically on push to `main`.

Required GitHub Secrets:
| Secret | Description |
|---|---|
| `DOCKERHUB_USERNAME_PERSONAL` | Docker Hub username |
| `DOCKERHUB_TOKEN_PERSONAL` | Docker Hub access token |
| `VPS_SSH_KEY` | Private SSH key for root@12.345.67.891 |

First deploy (manual setup on VPS):
```bash
ssh root@12.345.67.891
mkdir -p /opt/data-annotation-platform
cat > /opt/data-annotation-platform/.env << 'EOF'
APP_ENV=production
SECRET_KEY=<your-secret-key>
SUPABASE_URL=https://123ygro4567whfg***.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key>
SUPABASE_BUCKET=portfolio-base-bucket
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
EOF
```

After first deploy, pull the Ollama model:
```bash
docker exec $(docker ps -qf name=ollama) ollama pull llama3.2:3b
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/datasets` | List all datasets |
| `POST` | `/api/v1/datasets` | Upload dataset (multipart) |
| `POST` | `/api/v1/pipeline/{id}/run` | Run full pipeline |
| `POST` | `/api/v1/pipeline/{id}/stage/{stage}` | Run single stage |
| `GET` | `/api/v1/annotations/{id}/records` | List records with annotations |
| `PATCH` | `/api/v1/annotations/record/{id}/review` | Approve / reject / override |
| `GET` | `/api/v1/exports/{id}/csv` | Export annotated CSV |
| `GET` | `/api/v1/dashboard` | Aggregated stats |

Full interactive docs: `http://localhost:8001/docs`
