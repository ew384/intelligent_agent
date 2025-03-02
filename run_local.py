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
    from tool_service.src.tools.browser.browser_manager import BrowserManager
    import asyncio
    import logging
    import time
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("WeChatTest")
    
    try:
        logger.info("开始测试微信Web登录...")
        
        # 询问是否使用现有 cookies
        use_cookies = input("是否使用已保存的 cookies 尝试登录？(y/n): ").lower() == 'y'
        
        # 初始化浏览器管理器
        browser_manager = BrowserManager({
            'headless': False,  # 必须使用有头模式扫码登录
            'data_dir': './browser_data'
        })
        
        # 获取浏览器服务
        browser_service = await browser_manager.get_browser_service('credit_card')
        
        # 初始化会话
        session = await browser_service.initialize()
        
        if not session:
            logger.error("无法初始化浏览器会话")
            return
        
        # 导航到微信Web页面
        logger.info("导航到微信Web页面...")
        #await session.goto("https://web.wechat.com/")
        
        # 导入WeChatHandler
        from tool_service.src.tools.handlers.wechat import WeChatHandler
        
        # 创建处理器
        handler = WeChatHandler(session)
        
        # 如果使用 cookies，尝试加载
        if use_cookies:
            logger.info("尝试使用已保存的 cookies 登录...")
            cookies_loaded = await session.load_cookies('wechat_test', domain="web.wechat.com")
            
            if cookies_loaded:
                logger.info("成功加载 cookies，刷新页面...")
                await session.refresh_page()
                await asyncio.sleep(3)  # 等待页面加载
            else:
                logger.warning("未找到已保存的 cookies")
        
        # 检查登录状态
        login_status = await handler.check_wechat_login({"service_id": "wechat_test"})
        
        # 如果未登录，等待扫码
        if not login_status.get("logged_in", False):
            logger.info("检测到未登录状态，请使用微信扫描二维码登录...")
            
            # 循环检查登录状态
            start_time = time.time()
            while time.time() - start_time < 300:  # 最多等待5分钟
                login_status = await handler.check_wechat_login({"service_id": "wechat_test"})
                
                if login_status.get("logged_in", False):
                    logger.info("微信登录成功！")
                    
                    # 保存 cookies 供下次使用
                    await session.save_cookies('wechat_test')
                    logger.info("已保存登录 cookies 供下次使用")
                    
                    break
                
                logger.info("等待登录中...")
                await asyncio.sleep(5)
            
            if not login_status.get("logged_in", False):
                logger.error("登录超时，请稍后再试")
                await session.close()
                return
        else:
            logger.info("检测到已登录状态！")
        
        # 测试搜索联系人
        contact_name = input("请输入要搜索的联系人名称: ")
        logger.info(f"搜索联系人: {contact_name}")
        
        search_result = await handler.search_contact({"contact_name": contact_name})
        
        if search_result.get("status") == "success":
            logger.info(f"找到联系人: {search_result.get('contact_name')}")
            
            # 测试发送消息
            message = f"这是一条测试消息，发送时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            logger.info(f"发送消息: {message}")
            
            send_result = await handler.send_message({
                "message": message,
                "contact_id": search_result.get("contact_id")
            })
            
            if send_result.get("status") == "success":
                logger.info("消息发送成功！")
            else:
                logger.error(f"消息发送失败: {send_result.get('message')}")
        else:
            logger.error(f"联系人搜索失败: {search_result.get('message')}")
        
        # 再次保存 cookies 以确保保存了所有变更
        await session.save_cookies('wechat_test')
        logger.info("已保存最新的 cookies")
        
        # 等待几秒后关闭
        await asyncio.sleep(5)
        
        # 关闭会话
        await session.close()
        
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试微信Web登录失败: {str(e)}", exc_info=True)
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