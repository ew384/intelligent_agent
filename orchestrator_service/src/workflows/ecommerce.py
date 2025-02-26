# orchestrator-service/src/workflows/ecommerce.py
from .base import BaseWorkflow
from typing import Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class ECommerceWorkflow(BaseWorkflow):
    """
    Workflow for e-commerce operations that handles the sequence of operations
    for managing product listings, customer interactions, and competitor analysis.
    """
    
    PLATFORM_BASE_URLS = {
        "amazon": "https://sellercentral.amazon.com",
        "temu": "https://merchant.temu.com",
        "shopee": "https://seller.shopee.com",
        "alibaba": "https://seller.alibaba.com",
        "ebay": "https://www.ebay.com/sh/landing"
    }
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Validate the parameters
            if "platform" not in parameters:
                return {"status": "error", "message": "Platform parameter is required"}
                
            if "action" not in parameters:
                return {"status": "error", "message": "Action parameter is required"}
                
            # Add the base URL for the platform if not provided
            if "url" not in parameters and parameters["platform"] in self.PLATFORM_BASE_URLS:
                parameters["url"] = self.PLATFORM_BASE_URLS[parameters["platform"]]
            
            # Step 1: Call the tool service to perform the e-commerce action
            async with httpx.AsyncClient() as client:
                browser_response = await client.post(
                    "http://localhost:8003/tools/browser/ecommerce",
                    json=parameters
                )
                
                if browser_response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"E-commerce action failed with status: {browser_response.status_code}"
                    }
                
                browser_result = browser_response.json()
                
                # Step 2: If additional processing is needed, use LLM to interpret results
                if (browser_result.get("status") == "success" and 
                    parameters["action"] in ["check_competitor", "list_products"]):
                    
                    # Prepare LLM parameters for processing the results
                    llm_params = {
                        "prompt": self._generate_processing_prompt(
                            parameters["platform"],
                            parameters["action"],
                            browser_result.get("data", {})
                        ),
                        "provider": "claude"  # Could be configurable
                    }
                    
                    # Call LLM service to process the results
                    llm_response = await client.post(
                        "http://localhost:8003/tools/llm/chat/claude",
                        json=llm_params
                    )
                    
                    if llm_response.status_code != 200:
                        # If LLM processing fails, still return the browser results
                        logger.warning(f"LLM processing failed with status: {llm_response.status_code}")
                        return browser_result
                    
                    llm_result = llm_response.json()
                    
                    # Combine results
                    return {
                        "status": "success",
                        "raw_data": browser_result.get("data", {}),
                        "analysis": llm_result.get("responses", []),
                        "message": browser_result.get("message", "")
                    }
                
                # Return browser results directly for other actions
                return browser_result
                
        except Exception as e:
            logger.error(f"E-commerce workflow failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _generate_processing_prompt(self, platform: str, action: str, data: Dict[str, Any]) -> str:
        """
        Generate a prompt for LLM to process e-commerce data
        
        Args:
            platform: The e-commerce platform
            action: The action performed
            data: Data extracted from the action
        
        Returns:
            Formatted prompt for LLM
        """
        if action == "check_competitor":
            return (
                f"I've extracted pricing and product data from competitors on {platform}. "
                f"Please analyze this data and provide insights:\n\n"
                f"PLATFORM: {platform}\n"
                f"PRODUCT DATA: {str(data.get('product', {}))}\n\n"
                f"COMPETITOR DATA:\n{str(data.get('competitors', []))}\n\n"
                f"Please provide the following analysis:\n"
                f"1. Price comparison between our product and competitors\n"
                f"2. Recommendations for pricing strategy\n"
                f"3. Identify any competitive advantages our product has\n"
                f"4. Suggestions for improving our product listing"
            )
        elif action == "list_products":
            return (
                f"I've extracted our product listings from {platform}. "
                f"Please analyze this data and provide insights:\n\n"
                f"PLATFORM: {platform}\n"
                f"PRODUCT LISTINGS: {str(data.get('products', []))}\n\n"
                f"Please provide the following analysis:\n"
                f"1. Summary of current product portfolio\n"
                f"2. Identify any products with potential issues (low sales, poor ratings, etc.)\n"
                f"3. Recommendations for optimizing product listings\n"
                f"4. Suggestions for new product opportunities based on the current catalog"
            )
        else:
            return (
                f"Please analyze the following data from {platform} after performing {action}:\n\n"
                f"DATA: {str(data)}\n\n"
                f"Provide a summary and any relevant insights or recommendations."
            )