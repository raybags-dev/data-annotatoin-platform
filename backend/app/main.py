import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import connect_db, close_db
from app.api.v1.router import api_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    log.info("Connected to Supabase")
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
