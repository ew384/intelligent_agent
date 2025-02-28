# tool_service/src/tools/handlers/credit_card.py
from .base import BaseHandler
from typing import Dict, Any
import logging
import asyncio
import time
import re
import json
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class CreditCardHandler(BaseHandler):
    """中信银行信用卡账单处理器"""
    # 更新选择器，使用更精确的指示器
    LOGIN_SELECTORS = {
        'bill_amount': '.txt14',  # 金额选择器
        'logged_in_indicator': '#userName, #nameRare, .ca_num, #cardList',  # 登录状态指示器
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
            # 获取URL并解析域名（用于cookie管理）
            url = parameters['url']
            domain = self._extract_domain(url)
            # 显示详细日志
            logger.info(f"访问URL: {url}")
            # 尝试从cookies管理器加载cookies
            cookies_manager = getattr(self.session.browser_service, 'cookies_manager', None)
            if cookies_manager:
                logger.info(f"尝试加载 {domain} 的cookies")
                try:
                    cookies_loaded = await self.session.execute_script("""
                        const cookies = arguments[0];
                        let success = true;
                        for (const cookie of cookies) {
                            try {
                                document.cookie = `${cookie.name}=${cookie.value}; path=${cookie.path || '/'}; domain=${cookie.domain || document.domain}`;
                            } catch (e) {
                                success = false;
                                console.error('设置cookie失败:', e);
                            }
                        }
                        return success;
                    """, cookies_manager.load_cookies(domain))
                    logger.info(f"Cookies加载结果: {cookies_loaded}")
                except Exception as e:
                    logger.warning(f"加载cookies时出错: {str(e)}")
            # 使用更人性化的导航
            await self.session.goto(url, timeout=60000)
            # 等待页面完全加载
            await self.session.wait_for_load_state('domcontentloaded')
            await self.session.wait_for_load_state('networkidle')
            
            # 给用户时间在浏览器中完成登录
            logger.info("页面已加载，请在浏览器中完成登录...")
            # 等待用户操作的时间，可以根据需要调整
            login_wait_time = 300  # 等待3分钟
            logger.info(f"等待 {login_wait_time} 秒以完成手动登录...")
            
            # 等待指定时间
            for i in range(login_wait_time, 0, -30):
                logger.info(f"剩余等待时间: {i} 秒...")
                await asyncio.sleep(30)
                if await self._check_already_logged_in():
                    logger.info("检测到登录状态，继续处理...")
                    break

            # 检查是否已经登录 - 使用新的登录检测方法
            already_logged_in = await self._check_already_logged_in()
            if already_logged_in:
                logger.info("检测到已经登录状态")
                
                # 提取账户信息
                account_info = await self._extract_account_info()
                logger.info(f"成功提取账户信息: {json.dumps(account_info, ensure_ascii=False)}")
                
                # 格式化显示账户信息到日志
                await self._display_account_info(account_info)
                
                # 保存截图
                timestamp = int(time.time())
                screenshot_path = screenshots_dir / f"credit_card_{timestamp}.png"
                await self.session.screenshot(path=str(screenshot_path))
                logger.info(f"页面截图已保存到: {screenshot_path}")
                
                # 返回结果
                return {
                    "status": "success",
                    "message": "已登录并提取账户信息",
                    "account_info": account_info,
                    "screenshot": str(screenshot_path)
                }
            else:
                logger.info("页面已加载，请在浏览器中完成登录...")
                return {
                    "status": "pending",
                    "message": "需要登录，请在浏览器中完成登录操作"
                }
        except Exception as e:
            logger.error(f"处理账单查询时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }

    async def _check_already_logged_in(self) -> bool:
        """检查用户是否已登录 - 新的实现方法"""
        try:
            # 方法1: 检查元素是否存在
            element_indicators = self.LOGIN_SELECTORS['logged_in_indicator'].split(', ')
            for selector in element_indicators:
                try:
                    element = await self.session.query_selector(selector)
                    if element:
                        # 检查元素是否可见 - 修正方法调用
                        is_visible = await self.session.execute_script("""
                            function isVisible(el) {
                                if (!el) return false;
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetWidth > 0 && el.offsetHeight > 0;
                            }
                            return isVisible(arguments[0]);
                        """, element)
                        
                        if is_visible:
                            logger.info(f"元素检测: 找到登录指示器 {selector}")
                            return True
                except Exception as e:
                    logger.debug(f"检查选择器 {selector} 时出错: {str(e)}")
            
            # 方法2: 检查文本内容
            # 将 evaluate 替换为 execute_script
            text_detection_result = await self.session.execute_script("""() => {
                const textContent = document.body.innerText;
                return {
                    hasName: textContent.includes('欢迎您'),
                    hasBill: textContent.includes('本期应还金额'),
                    hasDate: textContent.includes('到期还款日')
                };
            }""")
            
            if text_detection_result and any(text_detection_result.values()):
                logger.info(f"文本检测: 找到登录指示 {text_detection_result}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"检查登录状态时出错: {str(e)}")
            return False

    async def _extract_account_info(self) -> Dict[str, Any]:
        """提取账户信息 - 新的实现方法"""
        try:
            # 使用JavaScript提取账户信息
            # 将 evaluate 替换为 execute_script
            account_data = await self.session.execute_script("""() => {
                const result = {
                    welcomeMessage: null,
                    billAmount: null,
                    dueDate: null,
                    cardNumber: null,
                    minPayment: null,
                    userName: null
                };
                
                // 获取用户名
                const userNameElement = document.querySelector('#userName');
                if (userNameElement && userNameElement.textContent) {
                    result.userName = userNameElement.textContent.trim();
                }
                
                // 获取卡号
                const cardNumElement = document.querySelector('.ca_num');
                if (cardNumElement && cardNumElement.textContent) {
                    result.cardNumber = cardNumElement.textContent.trim();
                }
                
                // 获取账单金额
                const billElements = document.querySelectorAll('td');
                for (let el of billElements) {
                    if (el.textContent.includes('本期应还金额')) {
                        const amountEl = el.querySelector('.txt14');
                        if (amountEl) {
                            result.billAmount = amountEl.textContent.trim();
                        }
                        break;
                    }
                }
                
                // 获取最低还款额
                const minPayElements = document.querySelectorAll('td');
                for (let el of minPayElements) {
                    if (el.textContent.includes('最低还款金额')) {
                        const amountEl = el.querySelector('.txt14');
                        if (amountEl) {
                            result.minPayment = amountEl.textContent.trim();
                        }
                        break;
                    }
                }
                
                // 获取还款日期
                const dateElements = document.querySelectorAll('td');
                for (let el of dateElements) {
                    if (el.textContent.includes('到期还款日')) {
                        const dateEl = el.querySelector('.txt14');
                        if (dateEl) {
                            result.dueDate = dateEl.textContent.trim();
                        }
                        break;
                    }
                }
                
                // 获取欢迎信息
                const welcomeElements = Array.from(document.querySelectorAll('*'))
                    .filter(el => el.textContent && (el.textContent.includes('欢迎您') || el.textContent.includes('您好')));
                if (welcomeElements.length > 0) {
                    result.welcomeMessage = welcomeElements[0].textContent.trim();
                }
                
                return result;
            }""")
            
            # 从欢迎信息中提取用户名（如果直接获取失败）
            if not account_data.get('userName') and account_data.get('welcomeMessage'):
                username_match = re.search(r'[欢迎您|您好]，([\w*]+)', account_data['welcomeMessage'])
                if username_match:
                    account_data['userName'] = username_match.group(1)
            
            # 格式化结果为更友好的结构
            formatted_info = {
                "用户信息": {
                    "用户名": account_data.get('userName', '未获取到'),
                    "卡号": account_data.get('cardNumber', '未获取到')
                },
                "账单信息": {
                    "应还金额": account_data.get('billAmount', '未获取到'),
                    "最低还款": account_data.get('minPayment', '未获取到'),
                    "还款日期": account_data.get('dueDate', '未获取到')
                },
                "原始数据": account_data
            }
            
            return formatted_info
        except Exception as e:
            logger.error(f"提取账户信息时出错: {str(e)}")
            return {"错误": f"提取信息失败: {str(e)}"}

    async def _display_account_info(self, account_info: Dict[str, Any]) -> None:
        """格式化显示账户信息到日志"""
        try:
            # 提取用户数据
            user_info = account_info.get("用户信息", {})
            bill_info = account_info.get("账单信息", {})
            
            # 格式化显示
            info_lines = []
            info_lines.append("="*50)
            info_lines.append("            中信银行信用卡账户信息摘要")
            info_lines.append("="*50)
            
            info_lines.append("\n👤 用户信息:")
            info_lines.append(f"   用户名: {user_info.get('用户名', '未获取到')}")
            info_lines.append(f"   卡号: {user_info.get('卡号', '未获取到')}")
            
            info_lines.append("\n💰 账单信息:")
            info_lines.append(f"   应还金额: ¥{bill_info.get('应还金额', '未获取到')}")
            info_lines.append(f"   最低还款: ¥{bill_info.get('最低还款', '未获取到')}")
            info_lines.append(f"   还款日期: {bill_info.get('还款日期', '未获取到')}")
            
            info_lines.append("\n" + "="*50)
            
            # 输出到日志
            for line in info_lines:
                logger.info(line)
        except Exception as e:
            logger.error(f"显示账户信息时出错: {str(e)}")

    def _extract_domain(self, url: str) -> str:
        """从URL中提取域名"""
        parsed_url = urlparse(url)
        return parsed_url.netloc
