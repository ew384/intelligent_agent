# orchestrator-service/src/workflows/credit_card.py
from .base import BaseWorkflow
from typing import Dict, Any
import httpx

class CreditCardWorkflow(BaseWorkflow):
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 调用工具服务执行信用卡查询
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8003/tools/browser/credit-card",
                    json=parameters
                )
                return response
        except Exception as e:
            return {"status": "error", "message": str(e)}
