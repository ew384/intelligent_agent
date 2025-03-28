# run_local.py
import asyncio
import argparse
import json
import logging
import os
import uvicorn
import subprocess
import signal
import sys
import time
from typing import List
from pathlib import Path

# 存储所有启动的子进程
child_processes = []

# 处理退出信号
def handle_exit(signum, frame):
    print("\n接收到终止信号，正在清理资源...")
    for proc in child_processes:
        try:
            proc.terminate()
            print(f"已终止进程 {proc.pid}")
        except:
            pass
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LocalRunner")

# Service configurations
SERVICES = {
    "api-gateway": {
        "port": 8000,
        "module": "api_gateway.src.main:app",  # 使用下划线而不是连字符
        "dependencies": []
    },
    "orchestrator": {
        "port": 8001,
        "module": "orchestrator_service.src.main:app",  # 使用下划线而不是连字符
        "dependencies": []
    },
    "scenario": {
        "port": 8002,
        "module": "scenario_service.src.main:app",  # 使用下划线而不是连字符
        "dependencies": []
    },
    "tool": {
        "port": 8003,
        "module": "tool_service.src.main:app",  # 使用下划线而不是连字符
        "dependencies": ["selenium", "asyncio"]  # 修改为selenium依赖
    },
    "LLM": {
        "port": 8005,
        "module": "LLM_chromeTab_manager:app",
        "dependencies": []
    }
}


async def start_service(name: str, service_config: dict):
    """Start a service using uvicorn"""
    global child_processes
    
    logger.info(f"Starting {name} service on port {service_config['port']}")
    
    # 创建uvicorn进程
    import subprocess
    cmd = [
        "uvicorn", 
        service_config["module"], 
        "--host", "0.0.0.0", 
        "--port", str(service_config["port"]),
        "--reload"
    ]
    
    proc = subprocess.Popen(cmd)
    child_processes.append(proc)
    
    # 等待进程
    return_code = await asyncio.to_thread(proc.wait)
    if return_code != 0:
        logger.error(f"Service {name} exited with code {return_code}")


async def main(selected_services: List[str] = None):
    """Main entry point for running services locally"""
    
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


async def test_wechat_login():
    """测试微信Web登录功能"""
    pass
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run services locally")
    parser.add_argument(
        "--services", 
        nargs="+", 
        choices=list(SERVICES.keys()) + ["all"],
        default=["all"],
        help="Services to run (default: all)"
    )

    parser.add_argument(
        "--test-wechat",
        action="store_true",
        help="Test WeChat Web login and messaging functionality"
    )
    
    args = parser.parse_args()
    
    if args.test_wechat:
        asyncio.run(test_wechat_login())
    else:
        selected = None if "all" in args.services else args.services
        asyncio.run(main(selected))
