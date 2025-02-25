# test_ecommerce.py
import asyncio
import httpx
import logging
import json
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ECommerceTest")

async def test_ecommerce():
    """Test the e-commerce scenario"""
    logger.info("Testing e-commerce scenario")
    
    # Prepare the request data
    request_data = {
        "scenario_type": "ecommerce",
        "parameters": {
            "platform": "amazon",  # or "temu", "shopee", etc.
            "action": "list_products",  # or "add_product", "reply_to_customer", "check_competitor"
            "credentials": {
                "username": "your_username",  # Replace with actual credentials
                "password": "your_password"   # Replace with actual credentials
            }
            # For other actions, you would include additional parameters:
            # "product_data": { ... } for add_product
            # "message_data": { ... } for reply_to_customer
            # "competitor_data": { ... } for check_competitor
        }
    }
    
    try:
        # Call the API gateway
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to API gateway")
            
            response = await client.post(
                "http://localhost:8000/tasks",
                json=request_data,
                timeout=300  # 5 minute timeout
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
        asyncio.run(test_ecommerce())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)