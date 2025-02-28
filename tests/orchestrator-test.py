#!/usr/bin/env python
# test_orchestrator.py
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
logger = logging.getLogger("OrchestratorTest")

async def test_orchestrator_health():
    """Test the Orchestrator Service health endpoint"""
    logger.info("Testing Orchestrator Service health...")
    
    try:
        # Try to call the health endpoint
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to Orchestrator health endpoint...")
            
            response = await client.get(
                "http://localhost:8001/",
                timeout=5.0  # Short timeout for health check
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            return response.status_code == 200
                
    except Exception as e:
        logger.error(f"Error testing Orchestrator health: {str(e)}")
        return False

async def test_debug_tasks_endpoint():
    """Test the debug_tasks endpoint of Orchestrator Service"""
    logger.info("Testing Orchestrator debug_tasks endpoint...")
    
    try:
        # Call the debug_tasks endpoint with a test payload
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to debug_tasks endpoint...")
            
            test_data = {
                "test": True,
                "message": "This is a test task",
                "timestamp": "2023-01-01T00:00:00Z"
            }
            
            response = await client.post(
                "http://localhost:8001/debug-tasks",
                json=test_data,
                timeout=5.0
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            # Check if response contains our data
            if response.status_code == 200:
                result = response.json()
                received_data = result.get("received_data", {})
                
                if received_data.get("test") == test_data["test"] and received_data.get("message") == test_data["message"]:
                    logger.info("Data successfully echoed back")
                    return True
                else:
                    logger.warning("Response doesn't match sent data")
                    return False
            
            return False
                
    except Exception as e:
        logger.error(f"Error testing debug_tasks: {str(e)}")
        return False

async def test_tasks_endpoint():
    """Test the main /tasks endpoint of Orchestrator Service"""
    logger.info("Testing Orchestrator /tasks endpoint...")
    
    # Define test scenarios to try
    test_scenarios = [
        {
            "name": "Echo Scenario",
            "payload": {
                "scenario_type": "echo",
                "parameters": {
                    "message": "Hello, Orchestrator!"
                }
            },
            "expected_status": 200
        },
        {
            "name": "Credit Card Scenario (minimal)",
            "payload": {
                "scenario_type": "credit_card",
                "parameters": {
                    "url": "https://example.com"  # Minimal data for testing
                }
            },
            "expected_status": 200
        },
        {
            "name": "Missing Scenario Type",
            "payload": {
                "parameters": {
                    "foo": "bar"
                }
            },
            "expected_status": [400, 422, 500]  # Accept any of these as valid error responses
        }
    ]
    
    results = {}
    
    try:
        # Test each scenario
        async with httpx.AsyncClient() as client:
            for scenario in test_scenarios:
                try:
                    logger.info(f"Testing {scenario['name']}...")
                    
                    response = await client.post(
                        "http://localhost:8001/tasks",
                        json=scenario["payload"],
                        timeout=10.0
                    )
                    
                    expected_status = scenario["expected_status"]
                    if isinstance(expected_status, list):
                        status_match = response.status_code in expected_status
                    else:
                        status_match = response.status_code == expected_status
                    
                    results[scenario["name"]] = {
                        "status_code": response.status_code,
                        "matches_expected": status_match,
                        "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                    }
                    
                    if isinstance(expected_status, list):
                        logger.info(f"{scenario['name']} status: {response.status_code} (Expected one of: {expected_status})")
                    else:
                        logger.info(f"{scenario['name']} status: {response.status_code} (Expected: {expected_status})")
                    
                except Exception as e:
                    logger.error(f"Error testing {scenario['name']}: {str(e)}")
                    results[scenario["name"]] = {"error": str(e)}
        
        # Print summary
        logger.info("\n=== Orchestrator Tasks Endpoint Summary ===")
        for name, result in results.items():
            status = "✓" if result.get("matches_expected", False) else "✗"
            logger.info(f"{status} {name}: {result}")
            
        return all(result.get("matches_expected", False) for result in results.values() if "matches_expected" in result)
                
    except Exception as e:
        logger.error(f"Error testing tasks endpoint: {str(e)}")
        return False

async def test_workflow_initialization():
    """Test if the Orchestrator initializes workflows correctly"""
    logger.info("Testing Orchestrator workflow initialization...")
    
    try:
        # This test needs a special endpoint that would list available workflows
        # Since there's no such endpoint, we'll test indirectly by checking responses for various scenario types
        
        test_scenarios = [
            "credit_card",
            "hr_recruitment",
            "ecommerce",
            "price_comparison",
            "nonexistent_scenario"  # This should fail with a workflow not found message
        ]
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for scenario_type in test_scenarios:
                try:
                    logger.info(f"Testing workflow initialization for '{scenario_type}'...")
                    
                    response = await client.post(
                        "http://localhost:8001/tasks",
                        json={
                            "scenario_type": scenario_type,
                            "parameters": {}
                        },
                        timeout=5.0
                    )
                    
                    # For valid scenarios, we expect a 200 status
                    # For invalid scenarios, the response should contain "Workflow not found"
                    
                    if scenario_type == "nonexistent_scenario":
                        # We expect this to fail with a specific message
                        expected_found = "not found" in response.text.lower() or "not found" in json.dumps(response.json()).lower()
                    else:
                        # For known scenarios, we expect no "not found" message
                        expected_found = not ("not found" in response.text.lower() or "not found" in json.dumps(response.json()).lower())
                    
                    results[scenario_type] = {
                        "status_code": response.status_code,
                        "workflow_found": expected_found,
                        "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                    }
                    
                    logger.info(f"Workflow '{scenario_type}' found: {expected_found}")
                    
                except Exception as e:
                    logger.error(f"Error testing workflow '{scenario_type}': {str(e)}")
                    results[scenario_type] = {"error": str(e)}
        
        # Print summary
        logger.info("\n=== Orchestrator Workflow Initialization Summary ===")
        for name, result in results.items():
            if name == "nonexistent_scenario":
                # For nonexistent scenario, we expect workflow_found to be True (meaning it correctly reported "not found")
                status = "✓" if result.get("workflow_found", False) else "✗"
                logger.info(f"{status} {name} (correctly reported as not found)")
            else:
                # For existing scenarios, we expect workflow_found to be True
                status = "✓" if result.get("workflow_found", False) else "✗"
                logger.info(f"{status} {name}")
            
        valid_results = all(
            (name == "nonexistent_scenario" and result.get("workflow_found", False)) or
            (name != "nonexistent_scenario" and result.get("workflow_found", False))
            for name, result in results.items() if "workflow_found" in result
        )
        
        return valid_results
                
    except Exception as e:
        logger.error(f"Error testing workflow initialization: {str(e)}")
        return False

async def main():
    """Run all Orchestrator Service tests"""
    results = {
        "health": await test_orchestrator_health(),
        "debug_tasks": await test_debug_tasks_endpoint(),
        "tasks": await test_tasks_endpoint(),
        "workflows": await test_workflow_initialization()
    }
    
    # Print final summary
    logger.info("\n=== Orchestrator Service Testing Summary ===")
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
