# run_local.py
import asyncio
import argparse
import json
import logging
import os
import uvicorn
import subprocess
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LocalRunner")

# Service configurations
SERVICES = {
    "api-gateway": {
        "port": 8000,
        "module": "api-gateway.src.main:app",
        "dependencies": []
    },
    "orchestrator": {
        "port": 8001,
        "module": "orchestrator-service.src.main:app",
        "dependencies": []
    },
    "scenario": {
        "port": 8002,
        "module": "scenario-service.src.main:app",
        "dependencies": []
    },
    "tool": {
        "port": 8003,
        "module": "tool-service.src.main:app",
        "dependencies": ["playwright", "asyncio"]
    }
}

async def install_dependencies():
    """Install required Python dependencies"""
    try:
        subprocess.check_call(["pip", "install", "-r", "requirements.txt"])
        logger.info("Installed common dependencies")
        
        # Install Playwright and its browsers
        subprocess.check_call(["pip", "install", "playwright"])
        subprocess.check_call(["playwright", "install", "chromium"])
        logger.info("Installed Playwright and browsers")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False
    
    return True

async def start_service(name: str, service_config: dict):
    """Start a service using uvicorn"""
    logger.info(f"Starting {name} service on port {service_config['port']}")
    
    config = uvicorn.Config(
        service_config["module"],
        host="0.0.0.0",
        port=service_config["port"],
        reload=True,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main(selected_services: List[str] = None):
    """Main entry point for running services locally"""
    # Install dependencies
    if not await install_dependencies():
        return
    
    # Determine which services to run
    if not selected_services:
        selected_services = list(SERVICES.keys())
    else:
        # Validate services
        for service in selected_services:
            if service not in SERVICES:
                logger.error(f"Unknown service: {service}")
                logger.info(f"Available services: {list(SERVICES.keys())}")
                return
    
    # Start services
    tasks = []
    for service_name in selected_services:
        service_config = SERVICES[service_name]
        task = asyncio.create_task(
            start_service(service_name, service_config)
        )
        tasks.append(task)
    
    # Wait for all services to complete (should run indefinitely)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run services locally")
    parser.add_argument(
        "--services", 
        nargs="+", 
        choices=list(SERVICES.keys()) + ["all"],
        default=["all"],
        help="Services to run (default: all)"
    )
    
    args = parser.parse_args()
    selected = None if "all" in args.services else args.services
    
    asyncio.run(main(selected))