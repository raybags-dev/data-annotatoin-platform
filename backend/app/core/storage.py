"""Supabase Storage wrapper for raw dataset uploads."""
from app.core.config import settings

def _client():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

def upload_raw(path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload raw file to Supabase Storage, return public URL."""
    if not settings.SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL not configured")
    sb = _client()
    bucket = settings.SUPABASE_BUCKET
    sb.storage.from_(bucket).upload(path, data, {"content-type": content_type, "upsert": "true"})
    return sb.storage.from_(bucket).get_public_url(path)

def download_raw(path: str) -> bytes:
    """Download raw file bytes from Supabase Storage."""
    sb = _client()
    return sb.storage.from_(settings.SUPABASE_BUCKET).download(path)

def delete_raw(path: str) -> None:
    sb = _client()
    sb.storage.from_(settings.SUPABASE_BUCKET).remove([path])
