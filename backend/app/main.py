import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import connect_db, close_db
from app.api.v1.router import api_router

log = structlog.get_logger()


async def _warm_ollama() -> None:
    """Pre-load the LLM model into Ollama at startup so the first user request is instant."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": "hello", "stream": False},
            )
            resp.raise_for_status()
        log.info("ollama.warmup.done", model=settings.OLLAMA_MODEL)
    except Exception as exc:
        log.warning("ollama.warmup.failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    log.info("Connected to Supabase")
    asyncio.create_task(_warm_ollama())
    yield
    await close_db()

app = FastAPI(
    title="Data Annotation Platform",
    description="Intelligent data annotation and processing pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
