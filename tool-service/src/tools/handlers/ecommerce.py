# tool-service/src/tools/handlers/ecommerce.py
from .base import BaseHandler
from typing import Dict, Any, List, Optional
import logging
import json
from playwright.async_api import TimeoutError, Page

logger = logging.getLogger(__name__)

class ECommerceHandler(BaseHandler):
    """Handler for e-commerce platform operations"""
    
    # Platform-specific selectors
    PLATFORM_SELECTORS = {
        "amazon": {
            "login": {
                "username": "#ap_email",
                "password": "#ap_password",
                "submit": "#signInSubmit",
                "success": "#sc-logo-top"
            },
            "navigation": {
                "inventory": "a[href*='/inventory']",
                "orders": "a[href*='/orders']",
                "messages": "a[href*='/messaging']"
            },
            "products": {
                "list_view": "#mt-content-row",
                "product_items": "tr.mt-row",
                "product_title": ".product-title",
                "product_price": ".product-price",
                "product_stock": ".product-quantity"
            },
            "add_product": {
                "create_button": "a[data-testid='add-product-button']",
                "title_input": "#product_title",
                "description_input": "#product-description",
                "price_input": "#list-price",
                "save_button": "#save-submit"
            },
            "messages": {
                "message_list": ".message-list",
                "message_item": ".message-item",
                "reply_button": ".reply-button",
                "reply_textarea": ".reply-textarea",
                "send_button": ".send-button"
            }
        },
        "temu": {
            "login": {
                "username": "#username",
                "password": "#password",
                "submit": ".login-button",
                "success": ".merchant-dashboard"
            },
            # Add Temu-specific selectors
        },
        "shopee": {
            "login": {
                "username": "[name='loginKey']",
                "password": "[name='password']",
                "submit": "[type='submit']",
                "success": ".header-seller-username"
            },
            # Add Shopee-specific selectors
        },
        # Add other platforms as needed
    }

    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generic query processor (required by base class)"""
        return await self.process_ecommerce_action(parameters)

    async def process_ecommerce_action(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process e-commerce platform action
        
        Args:
            parameters: Dictionary containing action parameters
            
        Returns:
            Action result with extracted data
        """
        platform = parameters.get("platform", "").lower()
        action = parameters.get("action", "").lower()
        
        if not platform or platform not in self.PLATFORM_SELECTORS:
            return {"status": "error", "message": f"Unsupported platform: {platform}"}
            
        if not action:
            return {"status": "error", "message": "No action specified"}
            
        try:
            # Step 1: Navigate to the platform URL
            url = parameters.get("url")
            await self.page.goto(url)
            
            # Step 2: Handle login if credentials provided
            if "credentials" in parameters:
                login_result = await self._handle_login(
                    platform, 
                    parameters["credentials"].get("username"),
                    parameters["credentials"].get("password")
                )
                
                if not login_result:
                    return {"status": "error", "message": f"Login to {platform} failed"}
            
            # Step 3: Perform the requested action
            if action == "login":
                # Already handled in step 2
                return {"status": "success", "message": f"Successfully logged into {platform}"}
                
            elif action == "list_products":
                products = await self._list_products(platform)
                return {"status": "success", "data": {"products": products}}
                
            elif action == "add_product":
                if "product_data" not in parameters:
                    return {"status": "error", "message": "Product data required for add_product action"}
                    
                result = await self._add_product(platform, parameters["product_data"])
                return result
                
            elif action == "reply_to_customer":
                if "message_data" not in parameters:
                    return {"status": "error", "message": "Message data required for reply_to_customer action"}
                    
                result = await self._reply_to_customer(platform, parameters["message_data"])
                return result
                
            elif action == "check_competitor":
                if "competitor_data" not in parameters:
                    return {"status": "error", "message": "Competitor data required for check_competitor action"}
                    
                competitor_data = await self._check_competitor(
                    platform, 
                    parameters["competitor_data"]
                )
                return {"status": "success", "data": competitor_data}
                
            else:
                return {"status": "error", "message": f"Unsupported action: {action}"}
        
        except Exception as e:
            logger.error(f"E-commerce action failed: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _handle_login(self, platform: str, username: str, password: str) -> bool:
        """
        Handle login for the specified platform
        
        Args:
            platform: E-commerce platform name
            username: Login username
            password: Login password
            
        Returns:
            Boolean indicating success
        """
        selectors = self.PLATFORM_SELECTORS.get(platform, {}).get("login", {})
        if not selectors:
            logger.error(f"No login selectors for platform: {platform}")
            return False
            
        try:
            # Wait for username input
            await self.page.wait_for_selector(selectors["username"], timeout=10000)
            
            # Fill username
            await self.page.fill(selectors["username"], username)
            
            # Fill password
            await self.page.fill(selectors["password"], password)
            
            # Click submit
            await self.page.click(selectors["submit"])
            
            # Wait for success indicator
            await self.page.wait_for_selector(selectors["success"], timeout=30000)
            
            return True
            
        except TimeoutError:
            logger.warning(f"Login timeout for {platform} - might need manual verification")
            
            # Give time for manual verification if needed
            try:
                await self.page.wait_for_selector(
                    selectors["success"], 
                    timeout=300000  # 5 minutes for manual intervention
                )
                return True
            except TimeoutError:
                return False
                
        except Exception as e:
            logger.error(f"Login error for {platform}: {str(e)}")
            return False
            
    async def _list_products(self, platform: str) -> List[Dict[str, Any]]:
        """
        List products for the specified platform
        
        Args:
            platform: E-commerce platform name
            
        Returns:
            List of product data dictionaries
        """
        selectors = self.PLATFORM_SELECTORS.get(platform, {}).get("products", {})
        if not selectors:
            logger.error(f"No product selectors for platform: {platform}")
            return []
            
        try:
            # Navigate to products/inventory page if needed
            nav_selector = self.PLATFORM_SELECTORS.get(platform, {}).get("navigation", {}).get("inventory")
            if nav_selector:
                await self.page.click(nav_selector)
                await self.page.wait_for_load_state("networkidle")
            
            # Wait for product list view
            await self.page.wait_for_selector(selectors["list_view"], timeout=30000)
            
            # Get all product items
            product_items = await self.page.query_selector_all(selectors["product_items"])
            
            products = []
            for item in product_items:
                product = {}
                
                # Extract title
                title_elem = await item.query_selector(selectors["product_title"])
                if title_elem:
                    product["title"] = await title_elem.text_content()
                
                # Extract price
                price_elem = await item.query_selector(selectors["product_price"])
                if price_elem:
                    price_text = await price_elem.text_content()
                    # Clean up price (remove currency symbol, commas, etc.)
                    price_text = price_text.replace("$", "").replace(",", "").strip()
                    try:
                        product["price"] = float(price_text)
                    except ValueError:
                        product["price"] = price_text
                
                # Extract stock
                stock_elem = await item.query_selector(selectors["product_stock"])
                if stock_elem:
                    product["stock"] = await stock_elem.text_content()
                
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error listing products for {platform}: {str(e)}")
            return []
            
    async def _add_product(self, platform: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a product to the specified platform
        
        Args:
            platform: E-commerce platform name
            product_data: Product details
            
        Returns:
            Dictionary with operation result
        """
        selectors = self.PLATFORM_SELECTORS.get(platform, {}).get("add_product", {})
        if not selectors:
            return {"status": "error", "message": f"No add product selectors for platform: {platform}"}
            
        try:
            # Click create/add product button
            await self.page.click(selectors["create_button"])
            await self.page.wait_for_load_state("networkidle")
            
            # Fill product details
            if "title" in product_data:
                await self.page.fill(selectors["title_input"], product_data["title"])
                
            if "description" in product_data:
                await self.page.fill(selectors["description_input"], product_data["description"])
                
            if "price" in product_data:
                await self.page.fill(
                    selectors["price_input"], 
                    str(product_data["price"])
                )
            
            # TODO: Handle image uploads if needed
            
            # Save the product
            await self.page.click(selectors["save_button"])
            await self.page.wait_for_load_state("networkidle")
            
            return {"status": "success", "message": "Product added successfully"}
            
        except Exception as e:
            logger.error(f"Error adding product for {platform}: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _reply_to_customer(self, platform: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reply to a customer message
        
        Args:
            platform: E-commerce platform name
            message_data: Message details
            
        Returns:
            Dictionary with operation result
        """
        selectors = self.PLATFORM_SELECTORS.get(platform, {}).get("messages", {})
        if not selectors:
            return {"status": "error", "message": f"No message selectors for platform: {platform}"}
            
        try:
            # Navigate to messages page if needed
            nav_selector = self.PLATFORM_SELECTORS.get(platform, {}).get("navigation", {}).get("messages")
            if nav_selector:
                await self.page.click(nav_selector)
                await self.page.wait_for_load_state("networkidle")
            
            # TODO: Implement logic to find specific customer message based on message_data
            
            # For now, just find the reply button and click it
            await self.page.click(selectors["reply_button"])
            
            # Fill in the reply
            await self.page.fill(
                selectors["reply_textarea"], 
                message_data.get("reply_content", "")
            )
            
            # Send the reply
            await self.page.click(selectors["send_button"])
            await self.page.wait_for_load_state("networkidle")
            
            return {"status": "success", "message": "Reply sent successfully"}
            
        except Exception as e:
            logger.error(f"Error sending reply for {platform}: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_competitor(self, platform: str, competitor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check competitor products and pricing
        
        Args:
            platform: E-commerce platform name
            competitor_data: Competitor details
            
        Returns:
            Dictionary with competitor data
        """
        try:
            # Start with our product info if available
            product_id = competitor_data.get("product_id")
            product_info = {}
            
            if product_id:
                # TODO: Implement logic to get our product details
                pass
            
            competitors = []
            competitor_urls = competitor_data.get("competitor_urls", [])
            
            for url in competitor_urls:
                try:
                    # Navigate to competitor product
                    await self.page.goto(url)
                    await self.page.wait_for_load_state("networkidle")
                    
                    # Extract competitor information (this is generic and would need to be
                    # customized for each platform and product type)
                    competitor = {
                        "url": url,
                        "title": await self._extract_text(self.page, "h1") or "Unknown Product",
                        "price": await self._extract_price(self.page) or 0,
                        "rating": await self._extract_rating(self.page) or "N/A",
                        "shipping": await self._extract_shipping(self.page) or "N/A",
                        "features": await self._extract_features(self.page) or []
                    }
                    
                    competitors.append(competitor)
                    
                except Exception as e:
                    logger.error(f"Error processing competitor URL {url}: {str(e)}")
                    competitors.append({"url": url, "error": str(e)})
            
            return {
                "product": product_info,
                "competitors": competitors
            }
            
        except Exception as e:
            logger.error(f"Error checking competitors: {str(e)}")
            return {"error": str(e)}
    
    async def _extract_text(self, page: Page, selector: str) -> Optional[str]:
        """Extract text content from an element"""
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.text_content()
        except:
            pass
        return None
        
    async def _extract_price(self, page: Page) -> Optional[float]:
        """Extract price from a product page"""
        # These selectors would need to be adjusted for each platform
        price_selectors = [
            ".price",
            ".product-price",
            "#price",
            ".a-price .a-offscreen",  # Amazon
            ".price-current"  # General
        ]
        
        for selector in price_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    # Clean up price text
                    text = text.replace("$", "").replace(",", "").strip()
                    return float(text)
            except:
                continue
                
        return None
        
    async def _extract_rating(self, page: Page) -> Optional[str]:
        """Extract rating from a product page"""
        rating_selectors = [
            ".rating",
            ".product-rating",
            "#rating",
            ".a-star-rating",  # Amazon
            ".rating-stars"  # General
        ]
        
        for selector in rating_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return await element.text_content()
            except:
                continue
                
        return None
        
    async def _extract_shipping(self, page: Page) -> Optional[str]:
        """Extract shipping information from a product page"""
        shipping_selectors = [
            ".shipping",
            ".product-shipping",
            "#shipping",
            ".a-shipping"  # Amazon
        ]
        
        for selector in shipping_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return await element.text_content()
            except:
                continue
                
        return None
        
    async def _extract_features(self, page: Page) -> List[str]:
        """Extract product features from a product page"""
        features = []
        
        # These selectors would need to be adjusted for each platform
        feature_selectors = [
            ".features li",
            ".product-features li",
            "#features li",
            ".a-features li"  # Amazon
        ]
        
        for selector in feature_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text:
                        features.append(text.strip())
                
                if features:
                    break
            except:
                continue
                
        return features