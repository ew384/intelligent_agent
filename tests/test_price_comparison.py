# test_price_comparison.py
import asyncio
import httpx
import logging
import json
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PriceComparisonTest")

async def test_price_comparison():
    """Test the price comparison scenario"""
    logger.info("Testing price comparison scenario")
    
    # Prepare the request data
    request_data = {
        "scenario_type": "price_comparison",
        "parameters": {
            "product_name": "iPhone 14 Pro 256GB",  # Replace with product of interest
            "platforms": ["taobao", "jd", "pinduoduo"],
            "price_range": {
                "min": 5000,
                "max": 9000
            },
            "specifications": [
                "256GB存储",
                "黑色",
                "国行正品"
            ],
            "credentials": {
                "username": "your_username",  # Replace with actual credentials
                "password": "your_password"   # Replace with actual credentials
            },
            "auto_checkout": False  # Set to True for automatic checkout
        }
    }
    
    try:
        # Call the API gateway
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to API gateway")
            
            response = await client.post(
                "http://localhost:8000/tasks",
                json=request_data,
                timeout=600  # 10 minute timeout for multi-platform search
            )
            
            if response.status_code != 200:
                logger.error(f"API gateway returned status code {response.status_code}")
                logger.error(f"Response: {response.text}")
                return
            
            result = response.json()
            
            logger.info("Response received from API gateway")
            logger.info(f"Status: {result.get('status')}")
            logger.info(f"Task ID: {result.get('task_id')}")
            
            # Pretty print the result
            logger.info("Result details:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(test_price_comparison())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)