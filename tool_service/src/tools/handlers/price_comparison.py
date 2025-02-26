# tool-service/src/tools/handlers/price_comparison.py
from .base import BaseHandler
from typing import Dict, Any, List, Optional
import logging
import json
from urllib.parse import quote
from playwright.async_api import TimeoutError, Page

logger = logging.getLogger(__name__)

class PriceComparisonHandler(BaseHandler):
    """Handler for price comparison across e-commerce platforms"""
    
    # Platform-specific configurations
    PLATFORM_CONFIG = {
        "taobao": {
            "base_url": "https://s.taobao.com/search?q=",
            "search": {
                "result_container": ".m-itemlist",
                "items": ".items .item",
                "title": ".title a",
                "price": ".price",
                "seller": ".shop",
                "rating": ".icon-service-free",
                "shipping": ".shipping"
            },
            "cart": {
                "add_to_cart_button": ".J_LinkBuy",
                "size_selector": ".J_SKU a",
                "color_selector": ".J_SKU a",
                "confirm_button": ".J_LinkAdd",
                "cart_indicator": ".J_MiniCartNum"
            },
            "login": {
                "username": "#fm-login-id",
                "password": "#fm-login-password",
                "submit": ".fm-button"
            }
        },
        "jd": {
            "base_url": "https://search.jd.com/Search?keyword=",
            "search": {
                "result_container": "#J_goodsList",
                "items": ".gl-item",
                "title": ".p-name a",
                "price": ".p-price",
                "seller": ".p-shop",
                "rating": ".p-commit",
                "shipping": ".p-icons"
            },
            "cart": {
                "add_to_cart_button": "#InitCartUrl",
                "size_selector": ".product-choose li",
                "color_selector": ".product-choose li",
                "confirm_button": ".product-button button",
                "cart_indicator": ".cart-count"
            },
            "login": {
                "username": "#loginname",
                "password": "#nloginpwd",
                "submit": ".login-btn"
            }
        },
        "pinduoduo": {
            "base_url": "https://mobile.yangkeduo.com/search_result.html?search_key=",
            "search": {
                "result_container": ".goods-list",
                "items": ".goods-item",
                "title": ".goods-name",
                "price": ".price",
                "seller": ".merchant",
                "rating": ".review",
                "shipping": ".free-shipping"
            },
            "cart": {
                "add_to_cart_button": ".add-cart-btn",
                "size_selector": ".sku-spec-value",
                "color_selector": ".sku-spec-value",
                "confirm_button": ".sku-confirm-btn",
                "cart_indicator": ".cart-num"
            },
            "login": {
                "username": "input[name='username']",
                "password": "input[name='password']",
                "submit": ".submit-btn"
            }
        }
    }

    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generic query processor (required by base class)"""
        return await self.process_price_comparison(parameters)

    async def process_price_comparison(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process price comparison actions
        
        Args:
            parameters: Dictionary containing action parameters
            
        Returns:
            Action result with extracted data
        """
        action = parameters.get("action", "").lower()
        
        if not action:
            return {"status": "error", "message": "No action specified"}
            
        try:
            if action == "search_multiple_platforms":
                return await self._search_multiple_platforms(
                    parameters.get("product_name", ""),
                    parameters.get("platforms", ["taobao", "jd", "pinduoduo"]),
                    parameters.get("price_range")
                )
                
            elif action == "add_to_cart":
                return await self._add_to_cart(
                    parameters.get("platform", ""),
                    parameters.get("product_url", ""),
                    parameters.get("credentials")
                )
                
            elif action == "checkout":
                return await self._checkout(
                    parameters.get("platform", ""),
                    parameters.get("credentials")
                )
                
            else:
                return {"status": "error", "message": f"Unsupported action: {action}"}
                
        except Exception as e:
            logger.error(f"Price comparison action failed: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _search_multiple_platforms(self, product_name: str, 
                                       platforms: List[str],
                                       price_range: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Search for a product across multiple platforms
        
        Args:
            product_name: Name of the product to search for
            platforms: List of platforms to search
            price_range: Optional price range for filtering
            
        Returns:
            Dictionary with search results from all platforms
        """
        if not product_name:
            return {"status": "error", "message": "Product name is required"}
            
        results = {}
        
        for platform in platforms:
            if platform not in self.PLATFORM_CONFIG:
                logger.warning(f"Unsupported platform: {platform}, skipping")
                continue
                
            platform_config = self.PLATFORM_CONFIG[platform]
            search_url = f"{platform_config['base_url']}{quote(product_name)}"
            
            try:
                # Navigate to search page
                await self.page.goto(search_url)
                await self.page.wait_for_load_state("networkidle")
                
                # Wait for search results
                selectors = platform_config["search"]
                await self.page.wait_for_selector(selectors["result_container"], timeout=10000)
                
                # Extract product data
                products = await self._extract_products(platform, selectors, price_range)
                
                results[platform] = products
                
            except TimeoutError:
                logger.error(f"Timeout waiting for search results on {platform}")
                results[platform] = []
                
            except Exception as e:
                logger.error(f"Error searching on {platform}: {str(e)}")
                results[platform] = []
        
        return {
            "status": "success",
            "data": results
        }
        
    async def _extract_products(self, platform: str, selectors: Dict[str, str], 
                              price_range: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Extract product information from search results
        
        Args:
            platform: The platform being searched
            selectors: CSS selectors for the platform
            price_range: Optional price range for filtering
            
        Returns:
            List of product information dictionaries
        """
        products = []
        
        try:
            # Get all product items
            items = await self.page.query_selector_all(selectors["items"])
            
            # Limit to first 10 items to avoid processing too many
            items = items[:10]
            
            for item in items:
                try:
                    product = {"platform": platform}
                    
                    # Extract title
                    title_elem = await item.query_selector(selectors["title"])
                    if title_elem:
                        product["title"] = await title_elem.text_content()
                        product["url"] = await title_elem.get_attribute("href")
                        
                        # Make relative URLs absolute
                        if product["url"] and not product["url"].startswith("http"):
                            product["url"] = f"https:{product['url']}" if product["url"].startswith("//") else f"https://{platform}.com{product['url']}"
                    
                    # Extract price
                    price_elem = await item.query_selector(selectors["price"])
                    if price_elem:
                        price_text = await price_elem.text_content()
                        # Clean up price (remove currency symbol, commas, etc.)
                        price_text = price_text.replace("¥", "").replace(",", "").strip()
                        try:
                            product["price"] = float(price_text)
                        except ValueError:
                            product["price"] = price_text
                    
                    # Extract seller
                    seller_elem = await item.query_selector(selectors["seller"])
                    if seller_elem:
                        product["seller"] = await seller_elem.text_content()
                    
                    # Extract rating
                    rating_elem = await item.query_selector(selectors["rating"])
                    if rating_elem:
                        product["rating"] = await rating_elem.text_content()
                    
                    # Extract shipping
                    shipping_elem = await item.query_selector(selectors["shipping"])
                    if shipping_elem:
                        product["shipping"] = await shipping_elem.text_content()
                    
                    # Apply price filter if provided
                    if price_range and "price" in product and isinstance(product["price"], float):
                        min_price = price_range.get("min")
                        max_price = price_range.get("max")
                        
                        if (min_price is not None and product["price"] < min_price) or \
                           (max_price is not None and product["price"] > max_price):
                            continue
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.error(f"Error extracting product data: {str(e)}")
            
            return products
            
        except Exception as e:
            logger.error(f"Error extracting products: {str(e)}")
            return []
            
    async def _add_to_cart(self, platform: str, product_url: str, 
                         credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Add a product to cart
        
        Args:
            platform: The e-commerce platform
            product_url: URL of the product to add to cart
            credentials: Optional login credentials
            
        Returns:
            Dictionary with operation result
        """
        if not platform or platform not in self.PLATFORM_CONFIG:
            return {"status": "error", "message": f"Unsupported platform: {platform}"}
            
        if not product_url:
            return {"status": "error", "message": "Product URL is required"}
            
        platform_config = self.PLATFORM_CONFIG[platform]
        cart_selectors = platform_config["cart"]
        
        try:
            # Navigate to product page
            await self.page.goto(product_url)
            await self.page.wait_for_load_state("networkidle")
            
            # Handle login if needed and credentials provided
            if credentials:
                logged_in = await self._handle_login(
                    platform, 
                    credentials.get("username"),
                    credentials.get("password")
                )
                
                if not logged_in:
                    return {"status": "error", "message": "Login failed"}
                    
                # Reload the page after login
                await self.page.goto(product_url)
                await self.page.wait_for_load_state("networkidle")
            
            # Select product options if available (size, color, etc.)
            size_selector = cart_selectors.get("size_selector")
            if size_selector:
                try:
                    size_options = await self.page.query_selector_all(size_selector)
                    if size_options and len(size_options) > 0:
                        await size_options[0].click()
                except Exception as e:
                    logger.warning(f"Error selecting size: {str(e)}")
            
            color_selector = cart_selectors.get("color_selector")
            if color_selector:
                try:
                    color_options = await self.page.query_selector_all(color_selector)
                    if color_options and len(color_options) > 0:
                        await color_options[0].click()
                except Exception as e:
                    logger.warning(f"Error selecting color: {str(e)}")
            
            # Click add to cart button
            add_button = await self.page.query_selector(cart_selectors["add_to_cart_button"])
            if not add_button:
                return {"status": "error", "message": "Add to cart button not found"}
                
            await add_button.click()
            
            # Handle confirmation if needed
            confirm_button = cart_selectors.get("confirm_button")
            if confirm_button:
                try:
                    # Wait for the confirmation button and click it
                    await self.page.wait_for_selector(confirm_button, timeout=5000)
                    await self.page.click(confirm_button)
                except TimeoutError:
                    logger.warning("Confirmation button not found, continuing")
            
            # Verify cart update
            cart_indicator = cart_selectors.get("cart_indicator")
            if cart_indicator:
                try:
                    await self.page.wait_for_selector(cart_indicator, timeout=5000)
                    indicator_text = await self.page.text_content(cart_indicator)
                    logger.info(f"Cart indicator: {indicator_text}")
                except TimeoutError:
                    logger.warning("Cart indicator not found, assuming success")
            
            return {"status": "success", "message": "Product added to cart"}
            
        except Exception as e:
            logger.error(f"Error adding to cart: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _checkout(self, platform: str, credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Proceed to checkout
        
        Args:
            platform: The e-commerce platform
            credentials: Optional login credentials
            
        Returns:
            Dictionary with operation result
        """
        # This is a placeholder - checkout would require more detailed implementation
        # and would be highly platform-specific
        return {
            "status": "warning",
            "message": "Checkout initiated but requires manual approval. Please check your browser to complete payment."
        }
        
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
        if platform not in self.PLATFORM_CONFIG:
            logger.error(f"No login config for platform: {platform}")
            return False
            
        login_selectors = self.PLATFORM_CONFIG[platform]["login"]
        
        try:
            # Fill username
            await self.page.fill(login_selectors["username"], username)
            
            # Fill password
            await self.page.fill(login_selectors["password"], password)
            
            # Click submit
            await self.page.click(login_selectors["submit"])
            
            # Wait for navigation to complete
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful
            # This would need platform-specific checks
            return True
            
        except Exception as e:
            logger.error(f"Login error for {platform}: {str(e)}")
            return False