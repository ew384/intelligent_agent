import asyncio
import httpx
import logging
import json
import sys
import os
from pathlib import Path
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("claude_test")

async def test_claude_chat():
    """
    Test the Claude chat functionality via the tool service API
    """
    # Prepare the request parameters
    prompt = input("Input Prompt\n")#"Tell me about the benefits of artificial intelligence in healthcare. Keep your answer under 200 words."
    
    # You can optionally include an image
    file_paths = None  # Set to a valid path if you want to test with an image
    #file_paths="/oper/work/endian/intelligent_agent/tests/5g.png"
    request_data = {
        "prompt": prompt,
        "file_paths": file_paths,
        "stream": False,
        "new_chat":False
    }
    
    logger.info(f"Sending prompt to Claude: {prompt[:50]}...")
    
    # Make the API call
    async with httpx.AsyncClient() as client:
        try:
            # Based on llm_api.py, the endpoint pattern is /llm/chat/{provider}
            response = await client.post(
                "http://localhost:8003/tools/llm/chat/claude",
                json=request_data,
                timeout=300.0  # 5 minute timeout since Claude might take time to respond
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            if result.get("status") == "success":
                # Print the responses
                print(result)
                for idx, resp in enumerate(result.get("responses", [])):
                    logger.info(f"Response {idx+1}:")
                    
                    # Handle streaming responses
                    if resp.get("status") == "streaming":
                        logger.info(f"Streaming content: {resp.get('content')[:100]}...")
                        if resp.get("complete"):
                            logger.info("Response complete.")
                    else:
                        logger.info(f"Response status: {resp.get('status')}")
                        if resp.get("message"):
                            logger.info(f"Message: {resp.get('message')}")
                
                return result
            else:
                logger.error(f"Error from API: {result.get('message', 'Unknown error')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Response content: {e.response.text}")
            return {"status": "error", "message": f"HTTP error: {str(e)}"}
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return {"status": "error", "message": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

# Alternative version based on your API structure
async def test_claude_chat_v2():
    """
    Test the Claude chat functionality - alternative endpoint format
    """
    # Prepare the request parameters
    prompt = "Tell me about the benefits of artificial intelligence in healthcare. Keep your answer under 200 words."
    
    # You can optionally include an image
    file_paths = None
    
    request_data = {
        "prompt": prompt,
        "file_paths": file_paths
    }
    
    logger.info(f"Trying alternative API endpoint format...")
    
    # Make the API call
    async with httpx.AsyncClient() as client:
        try:
            # Try the format used in api.py
            response = await client.post(
                "http://localhost:8003/tools/llm/claude",
                json=request_data,
                timeout=300.0
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            logger.info(f"Alternative endpoint successful: {result}")
            return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error with alt endpoint: {e}")
            logger.error(f"Response content: {e.response.text}")
            return {"status": "error", "message": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error with alt endpoint: {e}")
            return {"status": "error", "message": str(e)}

async def debug_api_structure():
    """
    Get the API structure/available endpoints to debug
    """
    logger.info("Checking API structure...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Get the root endpoint to see available routes
            response = await client.get("http://localhost:8003/")
            response.raise_for_status()
            result = response.json()
            logger.info(f"API structure: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"Error checking API structure: {e}")
            return {"status": "error", "message": str(e)}

# Run the test function
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Debug mode - check API structure
        result = asyncio.run(debug_api_structure())
    elif len(sys.argv) > 1 and sys.argv[1] == "--alt":
        # Try alternative endpoint
        result = asyncio.run(test_claude_chat_v2())
    else:
        # Regular test
        result = asyncio.run(test_claude_chat())
    
    # Print final result status
    print(f"\nFinal result status: {result.get('status', 'unknown')}")
    
    # If there's an error message, print it
    if result.get('status') != 'success' and result.get('message'):
        print(f"Error message: {result.get('message')}")
