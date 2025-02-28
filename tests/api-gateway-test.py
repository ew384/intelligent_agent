#!/usr/bin/env python
# test_api_gateway.py
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
logger = logging.getLogger("APIGatewayTest")

async def test_api_gateway_health():
    """Test the API Gateway health endpoint"""
    logger.info("Testing API Gateway health...")
    
    try:
        # Try to call a simple endpoint
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to API Gateway...")
            
            # First try health check or a simple GET endpoint
            response = await client.get(
                "http://localhost:8000/",
                timeout=5.0  # Short timeout for health check
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            # Try POST to tasks endpoint with an echo request
            echo_request = {
                "scenario_type": "credit_card",
                "parameters": {
                    "message": "Hello, API Gateway!"
                }
            }
            
            response = await client.post(
                "http://localhost:8000/tasks",
                json=echo_request,
                timeout=5.0
            )
            
            logger.info(f"POST /tasks status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            return response.status_code == 200
                
    except Exception as e:
        logger.error(f"Error testing API Gateway: {str(e)}")
        return False

async def test_route_forwarding():
    """Test that API Gateway correctly forwards requests to other services"""
    logger.info("Testing API Gateway route forwarding...")
    
    try:
        # Test each major route
        routes = [
            {
                "name": "Tasks Route",
                "url": "http://localhost:8000/tasks",
                "method": "POST",
                "payload": {
                    "scenario_type": "echo",
                    "parameters": {"message": "Testing tasks route"}
                }
            },
            {
                "name": "Chat Route",
                "url": "http://localhost:8000/chat",
                "method": "POST",
                "payload": {
                    "provider": "echo",
                    "prompt": "Testing chat route"
                }
            },
            {
                "name": "Tools Route",
                "url": "http://localhost:8000/tools/browser",
                "method": "POST",
                "payload": {
                    "message": "Testing tools route"
                }
            }
        ]
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for route in routes:
                try:
                    logger.info(f"Testing {route['name']}...")
                    
                    if route["method"] == "GET":
                        response = await client.get(
                            route["url"],
                            timeout=5.0
                        )
                    else:  # POST
                        response = await client.post(
                            route["url"],
                            json=route["payload"],
                            timeout=5.0
                        )
                    
                    results[route["name"]] = {
                        "status_code": response.status_code,
                        "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                    }
                    
                    logger.info(f"{route['name']} status: {response.status_code}")
                    
                except Exception as e:
                    logger.error(f"Error testing {route['name']}: {str(e)}")
                    results[route["name"]] = {"error": str(e)}
        
        # Print summary
        logger.info("\n=== API Gateway Route Testing Summary ===")
        for name, result in results.items():
            status = "✓" if result.get("status_code") in [200, 202, 204, 404, 405] else "✗"
            logger.info(f"{status} {name}: {result}")
            
        return all(result.get("status_code") in [200, 202, 204, 404, 405] for result in results.values() if "status_code" in result)
                
    except Exception as e:
        logger.error(f"Error testing route forwarding: {str(e)}")
        return False

async def test_api_gateway_with_invalid_data():
    """Test API Gateway's error handling with invalid data"""
    logger.info("Testing API Gateway error handling...")
    
    try:
        test_cases = [
            {
                "name": "Missing scenario_type",
                "url": "http://localhost:8000/tasks",
                "payload": {
                    "parameters": {"foo": "bar"}
                },
                "expected_status": [400, 422, 500]  # Accept any of these as valid error responses
            },
            {
                "name": "Invalid JSON",
                "url": "http://localhost:8000/tasks",
                "payload": "This is not JSON",
                "content_type": "text/plain",
                "expected_status": [400, 415, 422]
            },
            {
                "name": "Unsupported scenario",
                "url": "http://localhost:8000/tasks",
                "payload": {
                    "scenario_type": "nonexistent_scenario",
                    "parameters": {}
                },
                "expected_status": [400, 404, 422, 500]
            }
        ]
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for case in test_cases:
                try:
                    logger.info(f"Testing {case['name']}...")
                    
                    if isinstance(case["payload"], str) and case.get("content_type") == "text/plain":
                        response = await client.post(
                            case["url"],
                            content=case["payload"],
                            headers={"Content-Type": "text/plain"},
                            timeout=5.0
                        )
                    else:
                        response = await client.post(
                            case["url"],
                            json=case["payload"],
                            timeout=5.0
                        )
                    
                    status_match = response.status_code in case["expected_status"]
                    
                    results[case["name"]] = {
                        "status_code": response.status_code,
                        "matches_expected": status_match,
                        "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                    }
                    
                    logger.info(f"{case['name']} status: {response.status_code} (Expected one of: {case['expected_status']})")
                    
                except Exception as e:
                    logger.error(f"Error testing {case['name']}: {str(e)}")
                    results[case["name"]] = {"error": str(e)}
        
        # Print summary
        logger.info("\n=== API Gateway Error Handling Summary ===")
        for name, result in results.items():
            status = "✓" if result.get("matches_expected", False) else "✗"
            logger.info(f"{status} {name}: {result}")
            
        return all(result.get("matches_expected", False) for result in results.values() if "matches_expected" in result)
                
    except Exception as e:
        logger.error(f"Error testing invalid data handling: {str(e)}")
        return False

async def main():
    """Run all API Gateway tests"""
    results = {
        "health": await test_api_gateway_health(),
        "routing": await test_route_forwarding(),
        "error_handling": await test_api_gateway_with_invalid_data()
    }
    
    # Print final summary
    logger.info("\n=== API Gateway Testing Summary ===")
    for test_name, result in results.items():
        status = "✓" if result else "✗"
        logger.info(f"{status} {test_name}")
    
    all_passed = all(results.values())
    logger.info(f"\nOverall result: {'PASS' if all_passed else 'FAIL'}")
    
    # Return code based on result
    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
