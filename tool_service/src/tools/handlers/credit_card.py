# 在 tool_service/src/tools/handlers/credit_card.py 中整合
from .base import BaseHandler
from typing import Dict, Any
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class CreditCardHandler(BaseHandler):
    """中信银行信用卡账单处理器"""
    
    LOGIN_SELECTORS = {
        'bill_amount': '.bill-amount, .amount-text, .total-amount',  # 添加可能的其他选择器
        'logged_in_indicator': '.account-info, .user-info, .welcome-text'  # 添加其他可能的登录指示器
    }


    async def process_bill_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 保存截图目录
            screenshots_dir = Path("./browser_data/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # 显示详细日志
            logger.info(f"访问URL: {parameters['url']}")
            
            # 使用更人性化的导航
            # 访问URL，增加超时时间
            await self.page.goto(parameters["url"], timeout=60000)
            
            # 等待页面完全加载
            await self.page.wait_for_load_state('domcontentloaded')
            await self.page.wait_for_load_state('networkidle')
            
            logger.info("页面已加载，请在浏览器中完成登录...")
            
            # 检查是否有安全提示，如果有，尝试绕过
            await self._bypass_security_warning()
            
            # 截取登录前的页面
            login_screenshot = screenshots_dir / "credit_card_before_login.png"
            await self.page.screenshot(path=str(login_screenshot))
            logger.info(f"登录前截图已保存: {login_screenshot}")
            
            # 等待用户手动登录
            logger.info("等待用户完成登录...")
            if not await self._wait_for_login():
                logger.error("登录超时")
                # 截取登录失败的页面
                error_screenshot = screenshots_dir / "credit_card_login_timeout.png"
                await self.page.screenshot(path=str(error_screenshot))
                logger.info(f"登录超时截图已保存: {error_screenshot}")
                return {"status": "error", "message": "Login timeout"}
            
            return {"status": "success", "message": "登录成功"}
        except Exception as e:
            logger.error(f"Bill query failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _bypass_security_warning(self):
        """尝试绕过'This browser or app may not be secure'警告"""
        try:
            # 检查是否存在安全警告
            warning_text = "This browser or app may not be secure"
            if await self._is_text_visible(warning_text):
                logger.info("检测到安全警告，尝试绕过...")
                
                # 方法1: 尝试点击"Try anyway"按钮（如果存在）
                try_anyway_selectors = [
                    "text=Try anyway", 
                    "text=Continue anyway",
                    "[aria-label='Try anyway']",
                    "button:has-text('Try')",
                    "a:has-text('Try')"
                ]
                
                for selector in try_anyway_selectors:
                    try:
                        if await self.page.query_selector(selector):
                            await self.page.click(selector)
                            logger.info(f"点击了'{selector}'按钮")
                            await asyncio.sleep(2)
                            return True
                    except:
                        continue
                
                # 方法2: 如果没有按钮，尝试直接跳过这个警告页面
                current_url = self.page.url
                if "signinchallenge" in current_url:
                    # 直接导航到原始目标网址
                    await self.page.goto("https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html")
                    logger.info("已尝试直接跳转到目标页面")
                
                logger.warning("无法绕过安全警告，请手动处理...")
        except Exception as e:
            logger.error(f"尝试绕过安全警告时出错: {str(e)}")
        
        return False
    
    async def _is_text_visible(self, text):
        """检查页面中是否包含指定文本"""
        try:
            return await self.page.evaluate(f'''() => {{
                return document.body.innerText.includes("{text}");
            }}''')
        except:
            return False

    async def _wait_for_login(self) -> bool:
        try:
            # 添加页面截图功能
            screenshots_dir = Path("./browser_data/screenshots")
            await self.page.screenshot(path=str(screenshots_dir / "waiting_for_login.png"))
            logger.info("等待用户登录,请在浏览器窗口中完成登录...")
            
            await self.page.wait_for_selector(
                ' ,'.join(self.LOGIN_SELECTORS['logged_in_indicator'].split(', ')),
                timeout=300000  # 5分钟超时
            )
            
            # 登录成功后再截图
            await self.page.screenshot(path=str(screenshots_dir / "login_successful.png"))
            logger.info("登录成功!")
            
            return True
        except Exception as e:
            logger.error(f"登录等待出错: {str(e)}")
            # 出错时也保存截图
            await self.page.screenshot(path=str(screenshots_dir / "login_error.png"))
            logger.info("登录失败截图已保存")
            return False
