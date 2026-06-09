from supabase import AsyncClient, acreate_client
from app.core.config import settings

_client: AsyncClient | None = None

async def connect_db() -> None:
    global _client
    _client = await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

async def close_db() -> None:
    global _client
    _client = None

def get_db() -> AsyncClient:
    if _client is None:
        raise RuntimeError("Database not connected")
    return _client
