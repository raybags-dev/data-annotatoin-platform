from fastapi import APIRouter
from app.api.v1.endpoints import datasets, pipeline, annotations, exports, dashboard
from app.api.v1.endpoints import kaggle

api_router = APIRouter()
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(kaggle.router, prefix="/kaggle", tags=["kaggle"])
