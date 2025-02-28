#!/usr/bin/env python
# debug_credit_card_handler.py
"""
Direct debugging script for the credit card handler.
This bypasses the full service stack and directly tests the handler with minimal dependencies.
"""

import sys
import os
import time
import logging
import traceback
import asyncio
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CreditCardHandlerDebug")

class BrowserSession:
    """Simplified browser session class for testing"""
    
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)
        self.screenshots_dir = Path("./debug_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
    
    async def goto(self, url, timeout=60000):
        """Navigate to URL"""
        try:
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page load
            timeout_seconds = timeout / 1000
            end_time = time.time() + timeout_seconds
            
            while time.time() < end_time:
                state = self.driver.execute_script("return document.readyState")
                if state == "complete":
                    break
                await asyncio.sleep(0.5)
            
            logger.info("Page loaded")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            return False
    
    async def wait_for_selector(self, selector, timeout=30000):
        """Wait for element by CSS selector"""
        try:
            timeout_seconds = timeout / 1000
            element = WebDriverWait(self.driver, timeout_seconds).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except Exception as e:
            logger.warning(f"Selector not found: {selector} - {str(e)}")
            return None
    
    async def query_selector(self, selector):
        """Find element by CSS selector"""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            return None
    
    async def query_selector_all(self, selector):
        """Find all elements by CSS selector"""
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            return []
    
    async def execute_script(self, script, *args):
        """Execute JavaScript"""
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Script execution failed: {str(e)}")
            return None
    
    async def screenshot(self, path=None):
        """Take screenshot"""
        try:
            if path is None:
                timestamp = int(time.time())
                path = str(self.screenshots_dir / f"screenshot_{timestamp}.png")
            else:
                path = str(self.screenshots_dir / path)
            
            self.driver.save_screenshot(path)
            logger.info(f"Screenshot saved to: {path}")
            return path
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            return ""
    
    async def wait_for_load_state(self, state, timeout=30000):
        """Wait for page load state"""
        try:
            timeout_seconds = timeout / 1000
            end_time = time.time() + timeout_seconds
            
            if state in ["load", "domcontentloaded"]:
                while time.time() < end_time:
                    document_state = self.driver.execute_script("return document.readyState")
                    if document_state == "complete":
                        return True
                    await asyncio.sleep(0.5)
            
            elif state == "networkidle":
                # Simple approximation of network idle
                await asyncio.sleep(2)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Wait for load state failed: {str(e)}")
            return False

class SimpleCreditCardHandler:
    """Simplified credit card handler for direct testing"""
    
    def __init__(self, session):
        self.session = session
        
        # Login selectors
        self.LOGIN_SELECTORS = {
            'bill_amount': '.bill-amount, .amount-text, .total-amount',
            'logged_in_indicator': '.account-info, .user-info, .welcome-text',
            'security_warning': 'body:contains("browser or app may not be secure")',
            'try_anyway_button': [
                "text=Try anyway", 
                "text=Continue anyway",
                "[aria-label='Try anyway']",
                "button:has-text('Try')",
                "a:has-text('Try')"
            ]
        }
    
    async def process_bill_query(self, parameters):
        """Process credit card bill query"""
        try:
            logger.info(f"Processing bill query with parameters: {parameters}")
            
            # Navigate to URL
            url = parameters['url']
            await self.session.goto(url)
            
            # Take screenshot of initial state
            await self.session.screenshot("initial_page.png")
            
            # Check if already logged in
            logged_in = await self._check_already_logged_in()
            if logged_in:
                logger.info("Already logged in")
            else:
                logger.info("Not logged in, waiting for manual login")
                
                # Take screenshot before login
                await self.session.screenshot("before_login.png")
                
                # Wait for manual login
                if not await self._wait_for_login():
                    logger.error("Login timed out")
                    await self.session.screenshot("login_timeout.png")
                    return {"status": "error", "message": "Login timeout"}
            
            # Extract bill info
            bill_info = await self._extract_bill_info()
            
            # Take screenshot of bill
            bill_screenshot = await self.session.screenshot("bill.png")
            
            return {
                "status": "success",
                "message": "Bill information extracted",
                "bill_info": bill_info,
                "screenshot_path": bill_screenshot
            }
            
        except Exception as e:
            logger.error(f"Process bill query failed: {str(e)}")
            logger.error(traceback.format_exc())
            await self.session.screenshot("error.png")
            return {"status": "error", "message": str(e)}
    
    async def _check_already_logged_in(self):
        """Check if already logged in"""
        try:
            indicators = self.LOGIN_SELECTORS['logged_in_indicator'].split(', ')
            
            for selector in indicators:
                element = await self.session.query_selector(selector)
                if element:
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"Check logged in failed: {str(e)}")
            return False
    
    async def _wait_for_login(self):
        """Wait for user to log in manually"""
        logger.info("Please log in manually in the browser window...")
        print("请在浏览器窗口中完成登录，然后按回车键继续...")
        
        # Use sync input() for simplicity in this script
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Check if login successful
        indicators = self.LOGIN_SELECTORS['logged_in_indicator'].split(', ')
        
        for selector in indicators:
            element = await self.session.query_selector(selector)
            if element:
                logger.info("Login successful")
                return True
        
        logger.warning("Login indicators not found after user input")
        return False
    
    async def _extract_bill_info(self):
        """Extract bill information"""
        bill_info = {}
        
        try:
            # Wait for page to be stable
            await self.session.wait_for_load_state("networkidle")
            
            # Try all possible bill amount selectors
            bill_selectors = self.LOGIN_SELECTORS['bill_amount'].split(', ')
            
            for selector in bill_selectors:
                element = await self.session.query_selector(selector)
                if element:
                    text = element.text
                    if text:
                        bill_info['amount'] = text
                        logger.info(f"Found bill amount: {text}")
                        break
            
            # If we couldn't find the amount, try JavaScript
            if 'amount' not in bill_info:
                logger.info("Trying JavaScript to find bill amount")
                
                # Find all elements with text content that might be amounts
                amounts = await self.session.execute_script("""
                    const textNodes = [];
                    const walker = document.createTreeWalker(
                        document.body, 
                        NodeFilter.SHOW_TEXT, 
                        null, 
                        false
                    );
                    
                    let node;
                    while(node = walker.nextNode()) {
                        if (node.textContent.trim()) {
                            textNodes.push(node.textContent.trim());
                        }
                    }
                    
                    // Find text nodes with patterns like currency amounts
                    const amountRegex = /([¥￥]?\\s*\\d+[,，]?\\d*\\.?\\d*)/;
                    const possibleAmounts = [];
                    
                    for (const text of textNodes) {
                        const match = text.match(amountRegex);
                        if (match) {
                            possibleAmounts.push({
                                text: text,
                                amount: match[1].replace(/[¥￥,，]/g, '')
                            });
                        }
                    }
                    
                    return possibleAmounts;
                """)
                
                if amounts and len(amounts) > 0:
                    # Log all possible amounts for debugging
                    logger.info(f"Found {len(amounts)} possible amounts:")
                    for i, amount in enumerate(amounts):
                        logger.info(f"  {i+1}. {amount.get('text')}: {amount.get('amount')}")
                    
                    # Try to find the best match
                    for amount in amounts:
                        text = amount.get('text', '')
                        if '账单' in text or '金额' in text or '应还' in text:
                            bill_info['amount'] = amount.get('amount', '')
                            logger.info(f"Found likely bill amount: {bill_info['amount']}")
                            break
                    
                    # If no clear match, use the first one
                    if 'amount' not in bill_info and amounts:
                        bill_info['amount'] = amounts[0].get('amount', '')
                        logger.info(f"Using first amount found: {bill_info['amount']}")
            
            logger.info(f"Extracted bill info: {bill_info}")
            return bill_info
            
        except Exception as e:
            logger.error(f"Extract bill info failed: {str(e)}")
            return bill_info

async def setup_browser():
    """Set up Chrome browser with Selenium"""
    logger.info("Setting up Chrome browser")
    
    # Print system information for debugging
    logger.info(f"Python version: {sys.version}")
    logger.info(f"OS: {os.name} - {sys.platform}")
    
    # Check Chrome installation
    chrome_paths = [
        "/usr/local/bin/chrome-for-testing",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]
    
    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            logger.info(f"Chrome found at: {path}")
            chrome_found = True
            break
    
    if not chrome_found:
        logger.warning("Chrome not found in common locations")
    
    # Create directories
    data_dir = Path("./debug_data")
    data_dir.mkdir(exist_ok=True)
    (data_dir / "user_data").mkdir(exist_ok=True)
    
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-data-dir={data_dir}/user_data")
        
        # Use Chrome binary if specified
        chrome_binary = os.environ.get('CHROME_BINARY')
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
        
        # Set up ChromeDriver
        # Try to find ChromeDriver in common locations
        chromedriver_paths = [
            "/usr/local/bin/chromedriver",
            "chromedriver.exe"
        ]
        
        driver_path = None
        for path in chromedriver_paths:
            if os.path.exists(path):
                driver_path = path
                logger.info(f"Found ChromeDriver at: {path}")
                break
        
        if not driver_path:
            raise Exception("ChromeDriver not found. Please install it manually.")
        
        # Create WebDriver
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("WebDriver created successfully")
        
        # Create browser session
        session = BrowserSession(driver)
        return driver, session
        
    except Exception as e:
        logger.error(f"Browser setup failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def main():
    """Run the credit card handler debug test"""
    logger.info("Starting Credit Card Handler debug test")
    
    driver = None
    
    try:
        # Set up browser
        driver, session = await setup_browser()
        
        # Create handler
        handler = SimpleCreditCardHandler(session)
        
        # Process bill query
        parameters = {
            "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html"
        }
        
        logger.info(f"Starting bill query with URL: {parameters['url']}")
        result = await handler.process_bill_query(parameters)
        
        # Print results
        logger.info(f"Credit Card Handler test result: {json.dumps(result, indent=2)}")
        
        # Save result to file
        with open("credit_card_debug_result.json", "w") as f:
            json.dump(result, f, indent=2)
            
        logger.info("Test complete. Results saved to credit_card_debug_result.json")
        return result["status"] == "success"
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if driver:
            logger.info("Closing WebDriver")
            driver.quit()

if __name__ == "__main__":
    try:
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description="Debug Credit Card Handler")
        parser.add_argument("--url", default="https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html", 
                            help="URL to test with")
        parser.add_argument("--headless", action="store_true", help="Run in headless mode")
        parser.add_argument("--chrome-path", help="Path to Chrome binary")
        
        args = parser.parse_args()
        
        if args.chrome_path:
            os.environ["CHROME_BINARY"] ="/usr/local/bin/chrome-for-testing"
            
        if args.headless:
            os.environ["BROWSER_HEADLESS"] = "true"
            
        # Run the test
        exit_code = asyncio.run(main())
        sys.exit(0 if exit_code else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
