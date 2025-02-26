import asyncio
import json
import logging
from tool_service.src.tools.browser.browser_manager import BrowserManager
from tool_service.src.tools.handlers.credit_card import CreditCardHandler

# 配置日志
logging.basicConfig(level=logging.INFO)

async def test_credit_card():
    """测试信用卡模块"""
    # 加载配置
    with open('browser_config.json', 'r') as f:
        config = json.load(f)
    
    # 创建浏览器管理器
    browser_manager = BrowserManager(config)
    
    try:
        # 获取浏览器服务
        browser_service = await browser_manager.get_browser_service("test")
        
        # 初始化会话
        session = await browser_service.initialize()
        if not session:
            print("浏览器初始化失败")
            return
        
        # 创建处理器
        handler = CreditCardHandler(session)
        
        # 执行测试
        result = await handler.process_bill_query({
            "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html"
        })
        
        print(f"测试结果: {result}")
        
    finally:
        # 清理资源
        await browser_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_credit_card())
