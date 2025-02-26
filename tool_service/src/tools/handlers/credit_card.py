# tool_service/src/tools/handlers/credit_card.py
from .base import BaseHandler
from typing import Dict, Any
import logging
import asyncio
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class CreditCardHandler(BaseHandler):
    """中信银行信用卡账单处理器"""
    
    # 选择器
    LOGIN_SELECTORS = {
        'bill_amount': '.bill-amount, .amount-text, .total-amount',  # 添加可能的其他选择器
        'logged_in_indicator': '.account-info, .user-info, .welcome-text',  # 添加其他可能的登录指示器
        'security_warning': 'body:contains("browser or app may not be secure")',
        'try_anyway_button': [
            "text=Try anyway", 
            "text=Continue anyway",
            "[aria-label='Try anyway']",
            "button:has-text('Try')",
            "a:has-text('Try')"
        ]
    }

    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """实现基类的抽象方法"""
        return await self.process_bill_query(parameters)

    async def process_bill_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理信用卡账单查询
        
        Args:
            parameters: 查询参数
            
        Returns:
            查询结果
        """
        try:
            # 保存截图目录
            screenshots_dir = Path("./browser_data/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # 显示详细日志
            logger.info(f"访问URL: {parameters['url']}")
            
            # 使用更人性化的导航
            await self.session.goto(parameters["url"], timeout=60000)
            
            # 等待页面完全加载
            await self.session.wait_for_load_state('domcontentloaded')
            await self.session.wait_for_load_state('networkidle')
            
            logger.info("页面已加载，请在浏览器中完成登录...")
            
            # 检查是否有安全提示，如果有，尝试绕过
            await self._bypass_security_warning()
            
            # 截取登录前的页面
            login_screenshot = str(screenshots_dir / "credit_card_before_login.png")
            await self.session.screenshot(login_screenshot)
            logger.info(f"登录前截图已保存: {login_screenshot}")
            
            # 等待用户手动登录
            logger.info("等待用户完成登录...")
            if not await self._wait_for_login():
                logger.error("登录超时")
                # 截取登录失败的页面
                error_screenshot = str(screenshots_dir / "credit_card_login_timeout.png")
                await self.session.screenshot(error_screenshot)
                logger.info(f"登录超时截图已保存: {error_screenshot}")
                return {"status": "error", "message": "Login timeout"}
            
            # 尝试提取账单信息
            bill_info = await self._extract_bill_info()
            
            return {
                "status": "success", 
                "message": "登录成功", 
                "bill_info": bill_info
            }
        except Exception as e:
            logger.error(f"账单查询失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _bypass_security_warning(self) -> bool:
        """
        尝试绕过'This browser or app may not be secure'警告
        
        Returns:
            是否成功绕过
        """
        try:
            # 检查是否存在安全警告
            warning_text = "This browser or app may not be secure"
            warning_exists = await self.session.execute_script(f"""
                return document.body.innerText.includes("{warning_text}");
            """)
            
            if warning_exists:
                logger.info("检测到安全警告，尝试绕过...")
                
                # 方法1: 尝试点击"Try anyway"按钮（如果存在）
                for selector in self.LOGIN_SELECTORS['try_anyway_button']:
                    try:
                        element = await self.session.query_selector(selector)
                        if element:
                            await self.session.click(selector)
                            logger.info(f"点击了'{selector}'按钮")
                            await asyncio.sleep(2)
                            return True
                    except:
                        continue
                
                # 方法2: 如果没有按钮，尝试直接跳过这个警告页面
                current_url = await self.session.execute_script("return window.location.href;")
                if "signinchallenge" in current_url:
                    # 直接导航到原始目标网址
                    await self.session.goto("https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html")
                    logger.info("已尝试直接跳转到目标页面")
                
                logger.warning("无法绕过安全警告，请手动处理...")
                return False
            
            # 没有检测到安全警告
            return True
            
        except Exception as e:
            logger.error(f"尝试绕过安全警告时出错: {str(e)}")
            return False
    
    async def _wait_for_login(self) -> bool:
        """
        等待用户登录
        
        Returns:
            是否成功登录
        """
        try:
            # 添加页面截图功能
            screenshots_dir = Path("./browser_data/screenshots")
            await self.session.screenshot(str(screenshots_dir / "waiting_for_login.png"))
            logger.info("等待用户登录,请在浏览器窗口中完成登录...")
            
            # 等待用户交互
            await self.wait_for_user_interaction("请在浏览器中完成登录，然后按回车继续...")
            
            # 检查是否已登录
            logged_in_selectors = self.LOGIN_SELECTORS['logged_in_indicator'].split(', ')
            
            for selector in logged_in_selectors:
                is_visible = await self.is_element_visible(selector)
                if is_visible:
                    # 登录成功后再截图
                    await self.session.screenshot(str(screenshots_dir / "login_successful.png"))
                    logger.info("登录成功!")
                    return True
            
            logger.error("未检测到登录成功指示器")
            return False
            
        except Exception as e:
            logger.error(f"登录等待出错: {str(e)}")
            # 出错时也保存截图
            await self.session.screenshot(str(screenshots_dir / "login_error.png"))
            logger.info("登录失败截图已保存")
            return False
    
    async def _extract_bill_info(self) -> Dict[str, Any]:
        """
        提取账单信息
        
        Returns:
            账单信息字典
        """
        bill_info = {}
        
        try:
            # 等待页面加载完成
            await self.session.wait_for_load_state('networkidle')
            
            # 尝试提取账单金额
            bill_selectors = self.LOGIN_SELECTORS['bill_amount'].split(', ')
            
            for selector in bill_selectors:
                try:
                    text = await self.extract_text(selector)
                    if text:
                        bill_info['amount'] = text.strip()
                        logger.info(f"提取到账单金额: {text}")
                        break
                except Exception as e:
                    logger.warning(f"提取账单金额 {selector} 失败: {str(e)}")
            
            # 如果没有找到账单金额，尝试使用XPath
            if 'amount' not in bill_info:
                try:
                    xpath_expressions = [
                        "//span[contains(text(),'账单金额')]/following-sibling::span",
                        "//div[contains(text(),'账单金额')]/following-sibling::div",
                        "//div[contains(text(),'账单金额')]/../following-sibling::div",
                        "//div[contains(@class,'bill-amount')]"
                    ]
                    
                    for xpath in xpath_expressions:
                        text = await self.extract_text_xpath(xpath)
                        if text:
                            bill_info['amount'] = text.strip()
                            logger.info(f"通过XPath提取到账单金额: {text}")
                            break
                except Exception as e:
                    logger.warning(f"通过XPath提取账单金额失败: {str(e)}")
            
            # 尝试提取更多账单信息，如账单日期、到期还款日等
            try:
                bill_date_xpath = "//span[contains(text(),'账单日期')]/following-sibling::span"
                due_date_xpath = "//span[contains(text(),'到期还款日')]/following-sibling::span"
                
                bill_date = await self.extract_text_xpath(bill_date_xpath)
                due_date = await self.extract_text_xpath(due_date_xpath)
                
                if bill_date:
                    bill_info['bill_date'] = bill_date.strip()
                if due_date:
                    bill_info['due_date'] = due_date.strip()
                
            except Exception as e:
                logger.warning(f"提取额外账单信息失败: {str(e)}")
            
            return bill_info
            
        except Exception as e:
            logger.error(f"提取账单信息失败: {str(e)}")
            return bill_info
