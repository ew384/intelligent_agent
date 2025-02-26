# scenario-service/src/scenarios/ecommerce.py
from .base import BaseScenario
from typing import Dict, Any

class ECommerceScenario(BaseScenario):
    """
    E-commerce scenario for managing accounts across multiple platforms
    (Amazon, Temu, Shopee, etc.)
    """
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "ecommerce",
            "parameters": {
                "platform": {
                    "type": "string", 
                    "required": True,
                    "description": "E-commerce platform (amazon, temu, shopee, etc.)",
                    "enum": ["amazon", "temu", "shopee", "alibaba", "ebay"]
                },
                "action": {
                    "type": "string",
                    "required": True,
                    "description": "Action to perform",
                    "enum": ["login", "list_products", "add_product", "reply_to_customer", "check_competitor"]
                },
                "credentials": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["username", "password"]
                },
                "product_data": {
                    "type": "object",
                    "description": "Product data for add_product action",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "price": {"type": "number"},
                        "images": {"type": "array", "items": {"type": "string"}},
                        "categories": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "message_data": {
                    "type": "object",
                    "description": "Message data for reply_to_customer action",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "message_id": {"type": "string"},
                        "reply_content": {"type": "string"}
                    }
                },
                "competitor_data": {
                    "type": "object",
                    "description": "Competitor data for check_competitor action",
                    "properties": {
                        "product_id": {"type": "string"},
                        "competitor_urls": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "workflow": {
                "steps": [
                    {
                        "type": "browser_action",
                        "action": "navigate",
                        "parameters": {
                            "platform": "{platform}"
                        }
                    },
                    {
                        "type": "browser_action",
                        "action": "login",
                        "parameters": {
                            "platform": "{platform}",
                            "credentials": "{credentials}"
                        }
                    },
                    {
                        "type": "browser_action",
                        "action": "perform_ecommerce_action",
                        "parameters": {
                            "platform": "{platform}",
                            "action": "{action}",
                            "product_data": "{product_data}",
                            "message_data": "{message_data}",
                            "competitor_data": "{competitor_data}"
                        }
                    },
                    {
                        "type": "llm_action",
                        "action": "process_ecommerce_result",
                        "parameters": {
                            "platform": "{platform}",
                            "action": "{action}",
                            "extracted_data": "{extracted_data}"
                        }
                    }
                ]
            }
        }