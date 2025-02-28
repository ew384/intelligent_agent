#!/usr/bin/env python
# test_scenario_service.py
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
logger = logging.getLogger("ScenarioServiceTest")

async def test_service_running():
    """Test if the Scenario Service is running"""
    logger.info("Testing if Scenario Service is running...")
    
    try:
        # Try to connect to the service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8002/",
                timeout=5.0
            )
            
            logger.info(f"Status code: {response.status_code}")
            
            # Most likely this will return a 404 since there's no root endpoint
            # But that still means the service is running
            if response.status_code in [200, 404]:
                logger.info("Scenario Service is running")
                return True
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error connecting to Scenario Service: {str(e)}")
        return False

async def test_scenarios_endpoint():
    """Test the /scenarios endpoint of the Scenario Service"""
    logger.info("Testing Scenario Service /scenarios endpoint...")
    
    try:
        # This might not be a directly accessible endpoint in the API
        # But we'll try it anyway
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8002/scenarios",
                timeout=5.0
            )
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("Successfully called /scenarios endpoint")
                return True
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Error calling /scenarios endpoint: {str(e)}")
        return False

async def test_individual_scenarios():
    """Test getting individual scenario configurations"""
    logger.info("Testing individual scenario configurations...")
    
    # List of scenarios to test
    scenarios = [
        "credit_card",
        "hr_recruitment",
        "ecommerce",
        "price_comparison",
        "nonexistent_scenario"  # This should fail
    ]
    
    results = {}
    
    try:
        async with httpx.AsyncClient() as client:
            for scenario in scenarios:
                try:
                    logger.info(f"Testing scenario: {scenario}")
                    
                    response = await client.get(
                        f"http://localhost:8002/scenarios/{scenario}",
                        timeout=5.0
                    )
                    
                    if scenario == "nonexistent_scenario":
                        expected_status = 404  # We expect this to fail
                    else:
                        expected_status = 200
                    
                    status_match = response.status_code == expected_status
                    
                    results[scenario] = {
                        "status_code": response.status_code,
                        "matches_expected": status_match,
                        "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                    }
                    
                    logger.info(f"Scenario '{scenario}' status: {response.status_code} (Expected: {expected_status})")
                    
                except Exception as e:
                    logger.error(f"Error testing scenario '{scenario}': {str(e)}")
                    results[scenario] = {"error": str(e)}
        
        # Print summary
        logger.info("\n=== Individual Scenarios Testing Summary ===")
        for name, result in results.items():
            status = "✓" if result.get("matches_expected", False) else "✗"
            logger.info(f"{status} {name}: {result}")
            
        return all(result.get("matches_expected", False) for result in results.values() if "matches_expected" in result)
                
    except Exception as e:
        logger.error(f"Error testing individual scenarios: {str(e)}")
        return False

async def test_scenario_config_structure():
    """Test the structure of returned scenario configurations"""
    logger.info("Testing scenario configuration structure...")
    
    # We'll test one scenario in detail to check its structure
    scenario = "credit_card"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8002/scenarios/{scenario}",
                timeout=5.0
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get scenario config: {response.status_code}")
                return False
            
            config = response.json()
            
            # Check for required fields in the configuration
            required_fields = ["type", "parameters", "workflow"]
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                logger.error(f"Missing required fields in configuration: {missing_fields}")
                return False
            
            # Check workflow structure
            if "steps" not in config["workflow"]:
                logger.error("Workflow is missing 'steps' field")
                return False
            
            steps = config["workflow"]["steps"]
            if not isinstance(steps, list) or len(steps) == 0:
                logger.error("Workflow steps should be a non-empty list")
                return False
            
            # Check if each step has a type
            for i, step in enumerate(steps):
                if "type" not in step:
                    logger.error(f"Step {i} is missing 'type' field")
                    return False
            
            logger.info(f"Scenario '{scenario}' has valid configuration structure")
            return True
                
    except Exception as e:
        logger.error(f"Error testing scenario config structure: {str(e)}")
        return False

async def main():
    """Run all Scenario Service tests"""
    results = {
        "service_running": await test_service_running(),
        "scenarios_endpoint": await test_scenarios_endpoint(),
        "individual_scenarios": await test_individual_scenarios(),
        "config_structure": await test_scenario_config_structure()
    }
    
    # Print final summary
    logger.info("\n=== Scenario Service Testing Summary ===")
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
