from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db

router = APIRouter()

@router.get("")
async def dashboard_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    total_datasets = await db.datasets.count_documents({})
    total_records = await db.records.count_documents({})

    status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_dist = {r["_id"]: r["count"] for r in await db.datasets.aggregate(status_pipeline).to_list(None)}

    ann_pipeline = [{"$group": {"_id": "$annotation.status", "count": {"$sum": 1}}}]
    ann_dist = {r["_id"] or "unannotated": r["count"] for r in await db.records.aggregate(ann_pipeline).to_list(None)}

    label_pipeline = [
        {"$match": {"annotation": {"$ne": None}}},
        {"$group": {"_id": "$annotation.label", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    label_dist = {r["_id"]: r["count"] for r in await db.records.aggregate(label_pipeline).to_list(None) if r["_id"]}

    conf_pipeline = [
        {"$match": {"annotation.confidence": {"$gt": 0}}},
        {"$group": {"_id": None, "avg": {"$avg": "$annotation.confidence"}, "min": {"$min": "$annotation.confidence"}, "max": {"$max": "$annotation.confidence"}}},
    ]
    conf_result = await db.records.aggregate(conf_pipeline).to_list(1)
    confidence_stats = conf_result[0] if conf_result else {}
    if "_id" in confidence_stats:
        del confidence_stats["_id"]

    recent = await db.datasets.find({}).sort("created_at", -1).limit(5).to_list(None)
    for d in recent:
        d["_id"] = str(d["_id"])

    return {
        "total_datasets": total_datasets,
        "total_records": total_records,
        "dataset_status_distribution": status_dist,
        "annotation_status_distribution": ann_dist,
        "label_distribution": label_dist,
        "confidence_stats": confidence_stats,
        "recent_datasets": recent,
    }
