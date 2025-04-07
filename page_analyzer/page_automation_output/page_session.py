import asyncio
import logging
from typing import Optional, Any, Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PageSession')

class PageSession:
    """
    Class that handles browser session and basic page interactions
    """
    
    def __init__(self, driver, timeout=10):
        """
        Initialize page session
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Default wait timeout in seconds
        """
        self.driver = driver
        self.timeout = timeout
    
    async def navigate_to(self, url: str) -> bool:
        """
        Navigate to specified URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            # Add a small delay to let the page start loading
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Optional[Any]:
        """
        Wait for element matching selector to be present
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in seconds (uses default if None)
            
        Returns:
            WebElement if found, None otherwise
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for selector: {selector}")
            return None
        except Exception as e:
            logger.error(f"Error waiting for selector {selector}: {str(e)}")
            return None
    
    async def wait_for_clickable(self, selector: str, timeout: Optional[int] = None) -> Optional[Any]:
        """
        Wait for element matching selector to be clickable
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in seconds (uses default if None)
            
        Returns:
            WebElement if found and clickable, None otherwise
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for clickable element: {selector}")
            return None
        except Exception as e:
            logger.error(f"Error waiting for clickable element {selector}: {str(e)}")
            return None
    
    async def click(self, selector: str, wait_time: float = 0.5) -> bool:
        """
        Click element matching selector
        
        Args:
            selector: CSS selector
            wait_time: Time to wait after clicking in seconds
            
        Returns:
            Success status
        """
        try:
            element = await self.wait_for_clickable(selector)
            if not element:
                return False
                
            element.click()
            await asyncio.sleep(wait_time)
            return True
        except ElementNotInteractableException:
            # Try JavaScript click as fallback
            logger.info(f"Element not interactable, trying JavaScript click: {selector}")
            try:
                self.driver.execute_script("arguments[0].click();", 
                    self.driver.find_element(By.CSS_SELECTOR, selector))
                await asyncio.sleep(wait_time)
                return True
            except Exception as e:
                logger.error(f"JavaScript click failed: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Click failed on {selector}: {str(e)}")
            return False
    
    async def fill(self, selector: str, text: str) -> bool:
        """
        Fill form field with text
        
        Args:
            selector: CSS selector for input field
            text: Text to enter
            
        Returns:
            Success status
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return False
                
            # Clear field first
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            logger.error(f"Fill failed on {selector}: {str(e)}")
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """
        Get text content from element
        
        Args:
            selector: CSS selector
            
        Returns:
            Text content or None if element not found
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return None
                
            return element.text
        except Exception as e:
            logger.error(f"Get text failed on {selector}: {str(e)}")
            return None
    
    async def query_selector(self, selector: str) -> Optional[Any]:
        """
        Find element matching selector without waiting
        
        Args:
            selector: CSS selector
            
        Returns:
            WebElement if found, None otherwise
        """
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            return None
        except Exception as e:
            logger.error(f"Query selector failed for {selector}: {str(e)}")
            return None
    
    async def query_selector_all(self, selector: str) -> List[Any]:
        """
        Find all elements matching selector
        
        Args:
            selector: CSS selector
            
        Returns:
            List of WebElements (empty if none found)
        """
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            logger.error(f"Query selector all failed for {selector}: {str(e)}")
            return []
    
    async def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in browser
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to script
            
        Returns:
            Script execution result
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Script execution failed: {str(e)}")
            return None
    
    async def refresh_page(self) -> bool:
        """
        Refresh current page
        
        Returns:
            Success status
        """
        try:
            self.driver.refresh()
            await asyncio.sleep(2)  # Wait for page to reload
            return True
        except Exception as e:
            logger.error(f"Page refresh failed: {str(e)}")
            return False
