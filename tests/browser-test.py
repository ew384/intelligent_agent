#!/usr/bin/env python
# test_chrome_selenium.py
"""
Standalone test script to verify Chrome and Selenium functionality
independent of the rest of the system.
"""

import sys
import os
import time
import logging
import traceback
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
logger = logging.getLogger("ChromeSeleniumTest")

def create_directories():
    """Create necessary directories for test"""
    base_dir = Path("./browser_test")
    base_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (base_dir / "screenshots").mkdir(exist_ok=True)
    (base_dir / "user_data").mkdir(exist_ok=True)
    
    return base_dir

def test_chrome_selenium():
    """Test Chrome and Selenium functionality"""
    logger.info("Starting Chrome-Selenium test")
    
    test_dir = create_directories()
    driver = None
    
    try:
        # Step 1: Test Chrome installation
        logger.info("Checking Chrome installation")
        chrome_paths = [
            "/usr/local/bin/chrome-for-testing",
            "/usr/bin/chromium-browser",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                logger.info(f"Found Chrome at: {path}")
                break
        
        if not chrome_binary:
            logger.error("Chrome not found. Please install Chrome browser.")
            return False
        
        chromedriver_paths = [
            "/usr/local/bin/chromedriver",
        ]
        
        driver_path = None
        for path in chromedriver_paths:
            if os.path.exists(path):
                driver_path = path
                logger.info(f"Found ChromeDriver at: {path}")
                break
        
        if not driver_path:
            logger.error("ChromeDriver not found. Please install it manually.")
            return False
        
        # Step 3: Setup WebDriver
        logger.info("Setting up WebDriver")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add user data directory
        user_data_dir = test_dir / "user_data"
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Create service
        service = Service(driver_path)
        
        # Create WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("WebDriver created successfully")
        
        # Step 4: Test basic browsing functionality
        logger.info("Testing basic browsing")
        driver.get("https://www.example.com")
        logger.info(f"Page title: {driver.title}")
        
        # Take screenshot
        screenshot_path = test_dir / "screenshots" / "example.png"
        driver.save_screenshot(str(screenshot_path))
        logger.info(f"Screenshot saved to: {screenshot_path}")
        
        # Verify page elements
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            h1_text = driver.find_element(By.TAG_NAME, "h1").text
            logger.info(f"Found header: {h1_text}")
        except Exception as e:
            logger.error(f"Failed to find elements: {str(e)}")
            return False
        
        # Step 5: Test JavaScript execution
        logger.info("Testing JavaScript execution")
        js_result = driver.execute_script("return navigator.userAgent")
        logger.info(f"User agent: {js_result}")
        
        # Step 6: Test cookies
        logger.info("Testing cookies")
        cookies = driver.get_cookies()
        logger.info(f"Cookies: {cookies}")
        
        logger.info("Chrome-Selenium test completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        if driver:
            logger.info("Closing WebDriver")
            driver.quit()

if __name__ == "__main__":
    result = test_chrome_selenium()
    sys.exit(0 if result else 1)
