# scenario-service/src/routes/api.py
from fastapi import APIRouter
from ..internal.endpoints import scenarios

router = APIRouter()
router.include_router(scenarios.router, tags=["scenarios"])