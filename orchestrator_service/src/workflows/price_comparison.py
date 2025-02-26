# orchestrator-service/src/workflows/price_comparison.py
from .base import BaseWorkflow
from typing import Dict, Any, List
import httpx
import logging

logger = logging.getLogger(__name__)

class PriceComparisonWorkflow(BaseWorkflow):
    """
    Workflow for price comparison that handles searching multiple platforms,
    comparing prices, and adding the best option to cart.
    """
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Step 1: Validate required parameters
            if not parameters.get("product_name"):
                return {"status": "error", "message": "Product name is required"}
            
            # Default platforms if not specified
            if "platforms" not in parameters:
                parameters["platforms"] = ["taobao", "jd", "pinduoduo"]
                
            # Step 2: Search multiple platforms
            async with httpx.AsyncClient() as client:
                search_response = await client.post(
                    "http://localhost:8003/tools/browser/price-comparison",
                    json={
                        "action": "search_multiple_platforms",
                        "product_name": parameters["product_name"],
                        "platforms": parameters["platforms"],
                        "price_range": parameters.get("price_range")
                    }
                )
                
                if search_response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"Product search failed with status: {search_response.status_code}"
                    }
                
                search_result = search_response.json()
                
                if search_result.get("status") != "success":
                    return search_result
                
                # Step 3: Compare products using LLM
                llm_response = await client.post(
                    "http://localhost:8003/tools/llm/chat/claude",
                    json={
                        "prompt": self._generate_comparison_prompt(
                            search_result["data"],
                            parameters.get("specifications", [])
                        )
                    }
                )
                
                if llm_response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"Product comparison failed with status: {llm_response.status_code}"
                    }
                
                llm_result = llm_response.json()
                
                # Extract best product recommendation from LLM response
                best_product = self._extract_best_product(
                    llm_result.get("responses", []),
                    search_result["data"]
                )
                
                if not best_product:
                    return {
                        "status": "error", 
                        "message": "Failed to determine best product",
                        "search_results": search_result["data"],
                        "llm_analysis": llm_result.get("responses", [])
                    }
                
                # Step 4: Add best product to cart
                cart_response = await client.post(
                    "http://localhost:8003/tools/browser/price-comparison",
                    json={
                        "action": "add_to_cart",
                        "platform": best_product["platform"],
                        "product_url": best_product["url"],
                        "credentials": parameters.get("credentials")
                    }
                )
                
                if cart_response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"Add to cart failed with status: {cart_response.status_code}",
                        "best_product": best_product
                    }
                
                cart_result = cart_response.json()
                
                # Step 5: Checkout if requested
                if parameters.get("auto_checkout") and cart_result.get("status") == "success":
                    checkout_response = await client.post(
                        "http://localhost:8003/tools/browser/price-comparison",
                        json={
                            "action": "checkout",
                            "platform": best_product["platform"],
                            "credentials": parameters.get("credentials")
                        }
                    )
                    
                    checkout_result = checkout_response.json()
                    
                    return {
                        "status": cart_result.get("status"),
                        "message": cart_result.get("message"),
                        "best_product": best_product,
                        "search_results": search_result["data"],
                        "analysis": llm_result.get("responses", []),
                        "checkout": checkout_result
                    }
                
                # Return results without checkout
                return {
                    "status": cart_result.get("status"),
                    "message": cart_result.get("message"),
                    "best_product": best_product,
                    "search_results": search_result["data"],
                    "analysis": llm_result.get("responses", [])
                }
                
        except Exception as e:
            logger.error(f"Price comparison workflow failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _generate_comparison_prompt(self, search_results: Dict[str, List[Dict[str, Any]]], 
                                   specifications: List[str]) -> str:
        """
        Generate a prompt for LLM to compare products
        
        Args:
            search_results: Search results from multiple platforms
            specifications: Product specifications to consider
            
        Returns:
            Formatted prompt for LLM
        """
        prompt = (
            f"Please compare the following product search results and recommend "
            f"the best option based on price, reviews, and seller reputation.\n\n"
        )
        
        # Include specifications if provided
        if specifications:
            prompt += "Please pay special attention to these specifications:\n"
            for spec in specifications:
                prompt += f"- {spec}\n"
            prompt += "\n"
        
        # Add search results by platform
        for platform, products in search_results.items():
            prompt += f"\n## {platform.upper()} RESULTS:\n"
            
            for i, product in enumerate(products, 1):
                prompt += f"\n### Product {i}:\n"
                prompt += f"Title: {product.get('title', 'N/A')}\n"
                prompt += f"Price: {product.get('price', 'N/A')}\n"
                prompt += f"Rating: {product.get('rating', 'N/A')}\n"
                prompt += f"Seller: {product.get('seller', 'N/A')}\n"
                prompt += f"Shipping: {product.get('shipping', 'N/A')}\n"
                
                if "specifications" in product:
                    prompt += "Specifications:\n"
                    for key, value in product["specifications"].items():
                        prompt += f"- {key}: {value}\n"
                
                prompt += f"URL: {product.get('url', 'N/A')}\n"
        
        prompt += (
            "\n\nPlease analyze these products and recommend the best option. "
            "Consider the following factors:\n"
            "1. Price (including shipping costs)\n"
            "2. Product quality and features\n"
            "3. Seller reputation and reviews\n"
            "4. Delivery options\n\n"
            "Format your response as follows:\n"
            "RECOMMENDED PRODUCT: (provide the full title)\n"
            "PLATFORM: (name of the platform)\n"
            "PRICE: (total price including shipping)\n"
            "REASONS FOR RECOMMENDATION: (explain why this is the best option)\n"
            "CONSIDERATIONS: (any important considerations the user should know)"
        )
        
        return prompt
    
    def _extract_best_product(self, llm_responses: List[str], 
                             search_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Extract the best product recommendation from LLM response
        
        Args:
            llm_responses: LLM response text
            search_results: Original search results
            
        Returns:
            Dict with best product information or None if not found
        """
        # Combine all LLM responses
        full_response = " ".join(llm_responses)
        
        # Extract recommended product title and platform
        recommended_title = None
        recommended_platform = None
        
        for line in full_response.split('\n'):
            if line.startswith("RECOMMENDED PRODUCT:"):
                recommended_title = line.replace("RECOMMENDED PRODUCT:", "").strip()
            elif line.startswith("PLATFORM:"):
                recommended_platform = line.replace("PLATFORM:", "").strip().lower()
        
        if not recommended_title or not recommended_platform:
            logger.error("Could not extract recommendation from LLM response")
            return None
        
        # Find matching product in search results
        platform_results = search_results.get(recommended_platform, [])
        if not platform_results:
            return None
            
        # Try to find exact match
        for product in platform_results:
            if product.get("title") == recommended_title:
                return {
                    "platform": recommended_platform,
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "url": product.get("url"),
                    "seller": product.get("seller"),
                    "rating": product.get("rating")
                }
        
        # Try fuzzy match
        for product in platform_results:
            title = product.get("title", "")
            if title and (title in recommended_title or recommended_title in title):
                return {
                    "platform": recommended_platform,
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "url": product.get("url"),
                    "seller": product.get("seller"),
                    "rating": product.get("rating")
                }
        
        # Return first product as fallback
        if platform_results:
            product = platform_results[0]
            return {
                "platform": recommended_platform,
                "title": product.get("title"),
                "price": product.get("price"),
                "url": product.get("url"),
                "seller": product.get("seller"),
                "rating": product.get("rating")
            }
            
        return None
