# scenario-service/src/scenarios/price_comparison.py
from .base import BaseScenario
from typing import Dict, Any

class PriceComparisonScenario(BaseScenario):
    """
    Price comparison scenario for finding the lowest price of a product
    across multiple e-commerce platforms and adding it to cart.
    """
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "price_comparison",
            "parameters": {
                "product_name": {
                    "type": "string", 
                    "required": True,
                    "description": "Name of the product to search for"
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["taobao", "jd", "pinduoduo", "tmall", "suning"]
                    },
                    "default": ["taobao", "jd", "pinduoduo"],
                    "description": "Platforms to search for the product"
                },
                "price_range": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "number"},
                        "max": {"type": "number"}
                    },
                    "description": "Optional price range for filtering results"
                },
                "specifications": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Product specifications to consider when comparing"
                },
                "credentials": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "description": "Login credentials for the platforms (optional)"
                },
                "auto_checkout": {
                    "type": "boolean",
                    "default": false,
                    "description": "Whether to proceed to checkout automatically"
                }
            },
            "workflow": {
                "steps": [
                    {
                        "type": "browser_action",
                        "action": "search_multiple_platforms",
                        "parameters": {
                            "product_name": "{product_name}",
                            "platforms": "{platforms}",
                            "price_range": "{price_range}"
                        }
                    },
                    {
                        "type": "llm_action",
                        "action": "compare_products",
                        "parameters": {
                            "search_results": "{search_results}",
                            "specifications": "{specifications}"
                        }
                    },
                    {
                        "type": "browser_action",
                        "action": "add_to_cart",
                        "parameters": {
                            "platform": "{best_platform}",
                            "product_url": "{best_product_url}",
                            "credentials": "{credentials}"
                        }
                    },
                    {
                        "type": "conditional",
                        "condition": "{auto_checkout}",
                        "if_true": {
                            "type": "browser_action",
                            "action": "checkout",
                            "parameters": {
                                "platform": "{best_platform}",
                                "credentials": "{credentials}"
                            }
                        }
                    }
                ]
            }
        }