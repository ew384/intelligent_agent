# test_credit_card_direct.py
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleCreditCardHandler:
    def __init__(self, page):
        self.page = page
        self.screenshots_dir = Path("./credit_card_test")
        self.screenshots_dir.mkdir(exist_ok=True)
        
    async def process(self, url):
        """处理信用卡页面"""
        try:
            # 访问页面
            logger.info(f"访问URL: {url}")
            await self.page.goto(url)
            
            # 截图
            await self.page.screenshot(path=str(self.screenshots_dir / "initial.png"))
            logger.info("初始页面截图已保存")
            
            # 等待用户手动登录
            logger.info("请在浏览器中完成登录，然后按回车继续...")
            input()
            
            # 登录后截图
            await self.page.screenshot(path=str(self.screenshots_dir / "after_login.png"))
            logger.info("登录后截图已保存")
            
            # 尝试提取信息
            logger.info("尝试提取账单信息...")
            
            # 这里添加账单元素的选择器，根据实际页面结构调整
            selectors = [
                '.bill-amount', 
                '.amount-text', 
                '.total-amount',
                '.account-info',
                '.user-info'
            ]
            
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        logger.info(f"找到元素 {selector}: {text}")
                except Exception as e:
                    logger.warning(f"查找元素 {selector} 失败: {e}")
            
            return {"status": "success", "message": "测试完成"}
            
        except Exception as e:
            logger.error(f"处理失败: {e}")
            return {"status": "error", "message": str(e)}

async def test_credit_card():
    """测试信用卡功能"""
    playwright = None
    browser = None
    
    try:
        # 启动Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 创建处理器
        handler = SimpleCreditCardHandler(page)
        
        # 处理信用卡网站
        url = "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html"
        result = await handler.process(url)
        
        logger.info(f"测试结果: {result}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_credit_card())
