# scenario-service/src/scenarios/credit_card.py
from .base import BaseScenario
from typing import Dict, Any

class CreditCardScenario(BaseScenario):
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "credit_card",
            "description": "Credit card bill retrieval scenario",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "Bank URL"}
            },
            "workflow": {
                "steps": [
                    {
                        "id": "navigate",
                        "type": "browser_operations",
                        "action": "navigate",
                        "parameters": {"url": "{url}"}
                    },
                    {
                        "id": "wait_for_login",
                        "type": "browser_operations",
                        "action": "wait_for_login",
                        "parameters": {
                            "logged_in_indicators": ['#userName', '#nameRare', '.ca_num', '#cardList'],
                            "text_indicators": ['欢迎您', '本期应还金额', '到期还款日'],
                            "timeout": 300
                        }
                    },
                    {
                        "id": "extract_data",
                        "type": "credit_card_action",
                        "action": "extract_account_info",
                        "parameters": {
                            "selectors": {
                                "billAmount": ".txt14",
                                "dueDate": "td:nth-child(2) > span.txt14"
                            }
                        }
                    }
                ]
            }
        }