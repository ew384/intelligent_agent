# scenario-service/src/scenarios/credit_card.py
from .base import BaseScenario
from typing import Dict, Any

class CreditCardScenario(BaseScenario):
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "credit_card",
            "parameters": {
                "url": {"type": "string", "required": True}
            },
            "workflow": {
                "steps": [
                    {
                        "type": "browser_action",
                        "action": "navigate",
                        "parameters": {"url": "{url}"}
                    },
                    {
                        "type": "browser_action",
                        "action": "wait_for_login",
                        "parameters": {"selector": ".account-info"}
                    },
                    {
                        "type": "browser_action",
                        "action": "extract",
                        "parameters": {"selector": ".bill-amount"}
                    }
                ]
            }
        }