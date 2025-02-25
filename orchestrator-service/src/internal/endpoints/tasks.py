# orchestrator-service/src/internal/endpoints/tasks.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...workflows.credit_card import CreditCardWorkflow
from ...core.orchestrator import TaskOrchestrator

router = APIRouter()
orchestrator = TaskOrchestrator()

@router.post("/")
async def handle_task(request: Dict[str, Any]):
    try:
        workflow = orchestrator.get_workflow(request["scenario_type"])
        return await workflow.execute(request["parameters"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))