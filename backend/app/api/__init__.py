from fastapi import APIRouter
from app.api.endpoints import router as rest_router
from app.api.websockets import router as ws_router

api_router = APIRouter()
api_router.include_router(rest_router, prefix="/api", tags=["tasks"])
api_router.include_router(ws_router, prefix="/api", tags=["websockets"])
