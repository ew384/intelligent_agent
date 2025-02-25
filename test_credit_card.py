# test_credit_card.py
import asyncio
import httpx
import logging
import json
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CreditCardTest")

async def test_credit_card():
    """Test the credit card scenario"""
    logger.info("Testing credit card scenario")
    
    # Prepare the request data
    request_data = {
        "scenario_type": "credit_card",
        "parameters": {
            "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html"
        }
    }
    
    try:
        # Call the API gateway
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to API gateway")
            
            response = await client.post(
                "http://localhost:8000/tasks",
                json=request_data,
                timeout=300  # 5 minute timeout since login might take time
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
        asyncio.run(test_credit_card())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)