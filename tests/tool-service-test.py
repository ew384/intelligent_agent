#!/usr/bin/env python
# test_tool_service.py
import asyncio
import httpx
import logging
import json
import sys
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ToolServiceTest")

async def test_service_running():
    """Test if the Tool Service is running"""
    logger.info("Testing if Tool Service is running...")
    
    try:
        # Try to connect to the service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8003/",
                timeout=5.0
            )
            
            logger.info(f"Status code: {response.status_code}")
            
            # Most likely this will return a 404 since there's no root endpoint
            # But that still means the service is running
            if response.status_code in [200, 404]:
                logger.info("Tool Service is running")
                return True
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error connecting to Tool Service: {str(e)}")
        return False

async def test_browser_status():
    """Test the browser status endpoint"""
    logger.info("Testing browser status endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8003/tools/browser/browser-status",
                json={},
                timeout=5.0
            )
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                status = response.json()
                logger.info(f"Browser status: {status}")
                return True
            else:
                logger.warning(f"Failed to get browser status: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error checking browser status: {str(e)}")
        return False

async def test_browser_initialization():
    """Test browser initialization directly"""
    logger.info("Testing browser initialization...")
    
    try:
        # This endpoint doesn't exist by default, but we can use a real endpoint
        # that would initialize a browser session to test this functionality
        
        # Try to use the credit-card endpoint but with a dummy URL
        # This should test browser initialization without doing the full flow
        test_data = {
            "url": "https://example.com",  # Simple URL just to test initialization
            "test_only": True  # Add this flag to indicate it's just a test
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8003/tools/browser/credit-card",
                json=test_data,
                timeout=30.0  # Browser initialization can take time
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response content: {response.text}")
            
            # Even if it fails after initialization, the response should tell us
            # if the browser initialized successfully or not
            if response.status_code == 200:
                result = response.json()
                # Look for specific browser initialization errors
                if result.get("status") == "error" and "browser" in result.get("message", "").lower():
                    logger.error(f"Browser initialization failed: {result.get('message')}")
                    return False
                else:
                    logger.info("Browser initialization appears to be working")
                    return True
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error testing browser initialization: {str(e)}")
        return False

async def test_chromedriver_download():
    """Test the ChromeDriver download functionality"""
    logger.info("Testing ChromeDriver download...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8003/tools/browser/download-chromedriver",
                json={"force": False},  # Don't force redownload unless needed
                timeout=30.0  # This might take a while
            )
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"ChromeDriver download result: {result}")
                
                if result.get("status") == "success":
                    # Verify the driver path exists
                    driver_path = result.get("path")
                    if driver_path and os.path.exists(driver_path):
                        logger.info(f"Verified ChromeDriver exists at: {driver_path}")
                        return True
                    else:
                        logger.warning(f"ChromeDriver path not found: {driver_path}")
                        return False
                else:
                    logger.warning(f"ChromeDriver download failed: {result.get('message')}")
                    return False
            else:
                logger.warning(f"Failed to download ChromeDriver: {response.text}")
                return False