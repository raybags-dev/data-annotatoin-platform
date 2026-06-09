from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient | None = None

async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGO_URL)

async def close_db() -> None:
    if _client:
        _client.close()

def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("DB not connected")
    return _client[settings.MONGO_DB]
