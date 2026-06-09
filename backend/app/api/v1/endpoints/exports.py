from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from supabase._async.client import AsyncClient
from app.core.database import get_db
from app.services.export_service import ExportService

router = APIRouter()

def _svc(db: AsyncClient = Depends(get_db)) -> ExportService:
    return ExportService(db)

@router.get("/{dataset_id}/csv")
async def export_csv(dataset_id: str, svc: ExportService = Depends(_svc)):
    data = await svc.to_csv(dataset_id)
    return Response(data, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={dataset_id}.csv"})

@router.get("/{dataset_id}/json")
async def export_json(dataset_id: str, svc: ExportService = Depends(_svc)):
    data = await svc.to_json(dataset_id)
    return Response(data, media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename={dataset_id}.json"})

@router.get("/{dataset_id}/excel")
async def export_excel(dataset_id: str, svc: ExportService = Depends(_svc)):
    data = await svc.to_excel(dataset_id)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={dataset_id}.xlsx"},
    )

@router.get("/{dataset_id}/report")
async def processing_report(dataset_id: str, svc: ExportService = Depends(_svc)):
    try:
        return await svc.processing_report(dataset_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
