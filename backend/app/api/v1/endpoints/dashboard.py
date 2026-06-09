from fastapi import APIRouter, Depends
from supabase._async.client import AsyncClient
from app.core.database import get_db

router = APIRouter()

@router.get("")
async def dashboard_stats(db: AsyncClient = Depends(get_db)):
    ds_res = await db.table("ann_datasets").select("*").order("created_at", desc=True).execute()
    rec_res = await db.table("ann_records").select("annotation").execute()

    datasets = ds_res.data or []
    records = rec_res.data or []

    # Status distribution
    status_dist: dict[str, int] = {}
    for d in datasets:
        s = d.get("status", "unknown")
        status_dist[s] = status_dist.get(s, 0) + 1

    # Annotation status distribution
    ann_dist: dict[str, int] = {}
    label_dist: dict[str, int] = {}
    confidence_vals: list[float] = []
    for r in records:
        ann = r.get("annotation")
        status = ann.get("status") if ann else "unannotated"
        ann_dist[status or "unannotated"] = ann_dist.get(status or "unannotated", 0) + 1
        if ann and ann.get("label"):
            lbl = ann["label"]
            label_dist[lbl] = label_dist.get(lbl, 0) + 1
        if ann and ann.get("confidence", 0) > 0:
            confidence_vals.append(float(ann["confidence"]))

    confidence_stats = {}
    if confidence_vals:
        confidence_stats = {
            "avg": sum(confidence_vals) / len(confidence_vals),
            "min": min(confidence_vals),
            "max": max(confidence_vals),
        }

    # Top 20 labels
    top_labels = dict(sorted(label_dist.items(), key=lambda x: x[1], reverse=True)[:20])

    return {
        "total_datasets": len(datasets),
        "total_records": len(records),
        "dataset_status_distribution": status_dist,
        "annotation_status_distribution": ann_dist,
        "label_distribution": top_labels,
        "confidence_stats": confidence_stats,
        "recent_datasets": datasets[:5],
    }
