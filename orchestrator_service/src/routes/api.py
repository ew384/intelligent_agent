# orchestrator-service/src/routes/api.py
from fastapi import APIRouter
from ..internal.endpoints import tasks

router = APIRouter()
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])