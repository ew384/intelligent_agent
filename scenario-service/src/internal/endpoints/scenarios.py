# scenario-service/src/internal/endpoints/scenarios.py
from fastapi import APIRouter
from ...scenarios.credit_card import CreditCardScenario
from ...core.registry import ScenarioRegistry

router = APIRouter()
registry = ScenarioRegistry()

@router.get("/{scenario_type}")
async def get_scenario(scenario_type: str):
    scenario = registry.get_scenario(scenario_type)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.get_config()
