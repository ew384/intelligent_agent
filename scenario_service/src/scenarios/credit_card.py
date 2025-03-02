# scenario-service/src/scenarios/credit_card.py
from .base import BaseScenario
from typing import Dict, Any

class CreditCardScenario(BaseScenario):
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "credit_card",
            "description": "Credit card bill retrieval scenario with WeChat notification",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "Bank URL"},
                "notify_wechat": {"type": "boolean", "required": False, "description": "Whether to send notification via WeChat", "default": False},
                "wechat_contact": {"type": "string", "required": False, "description": "WeChat contact name to notify"}
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
                    },
                    {
                        "id": "wechat_notification",
                        "type": "wechat_action",
                        "action": "search_and_send",
                        "parameters": {
                            "contact_name": "{wechat_contact}",
                            "message": "信用卡账单通知：\n账单金额: {extract_data.account_info.billAmount}\n还款日期: {extract_data.account_info.dueDate}\n卡号: {extract_data.account_info.cardNumber}"
                        },
                        "condition": "{notify_wechat} == True"
                    }
                ]
            }
        }