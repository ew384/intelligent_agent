# tool-service/src/tools/browser/browser_service.py
from typing import Dict, Any, Optional
import logging
import asyncio
import os
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from ..common.cookies_manager import CookiesManager

logger = logging.getLogger(__name__)

class BrowserService:
    def __init__(self, headless: bool = True, config: Dict[str, Any] = None):
        """
        Initialize the browser service
        
        Args:
            headless: Whether to run the browser in headless mode
            config: Additional configuration options
        """
        self.headless = headless
        self.config = config or {
            'data_dir': os.environ.get('BROWSER_DATA_DIR', './browser_data'),
            'timeout': int(os.environ.get('BROWSER_TIMEOUT', 30000)),
            'user_agent': os.environ.get(
                'BROWSER_USER_AGENT', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            )
        }
        self.playwright = None
        self.browser = None
        self.context = None
        self.cookies_manager = CookiesManager(self.config['data_dir'])
        
    async def initialize(self) -> Page:
        """
        Initialize browser and create a new page
        
        Returns:
            A configured page object
        """
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless
            )
            
        # Create a context with custom options
        self.context = await self.browser.new_context(
            user_agent=self.config['user_agent'],
            viewport={'width': 1280, 'height': 800},
            ignore_https_errors=True
        )
        
        # Create and configure page
        page = await self.context.new_page()
        await page.set_default_timeout(self.config['timeout'])
        
        return page
        
    async def new_page(self) -> Page:
        """
        Create a new page in the existing browser context
        
        Returns:
            A new page object
        """
        if not self.context:
            # Initialize browser if not already done
            await self.initialize()
            
        return await self.context.new_page()
        
    async def load_cookies(self, domain: str) -> bool:
        """
        Load cookies for the specified domain
        
        Args:
            domain: The domain to load cookies for
            
        Returns:
            Boolean indicating success
        """
        if not self.context:
            logger.error("Browser context not initialized")
            return False
            
        try:
            cookies = self.cookies_manager.load_cookies(domain)
            if cookies:
                await self.context.add_cookies(cookies)
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading cookies: {str(e)}")
            return False
            
    async def save_cookies(self, domain: str) -> bool:
        """
        Save cookies for the specified domain
        
        Args:
            domain: The domain to save cookies for
            
        Returns:
            Boolean indicating success
        """
        if not self.context:
            logger.error("Browser context not initialized")
            return False
            
        try:
            cookies = await self.context.cookies()
            self.cookies_manager.save_cookies(domain, cookies)
            return True
        except Exception as e:
            logger.error(f"Error saving cookies: {str(e)}")
            return False
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")