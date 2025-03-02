# tool_service/src/tools/handlers/credit_card.py
from .base import BaseHandler
from .browser_operations import BrowserOperations
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
    """
    中信银行信用卡账单处理器
    专注于处理中信银行信用卡业务特定的逻辑和数据提取
    """
    
    # 登录和元素选择器配置
    """
    SELECTORS = {
        'bill_amount': 'td:nth-child(1) > span.txt14',  # 金额选择器
        'min_payment': 'td:nth-child(2) > span.txt14',  # 最低还款金额选择器
        'due_date': 'td:nth-child(2) > span.txt14',     # 到期还款日选择器
        'card_number': '.ca_num',                       # 卡号选择器
        'logged_in_indicators': [
            '#userName', '#nameRare', '.ca_num', '#cardList',
        ],                                              # 登录状态指示器
        'text_indicators': [
            '欢迎您', '本期应还金额', '到期还款日'
        ]                                               # 文本指示器
    }
    """
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理信用卡账单查询 - 高级业务流程
        
        Args:
            parameters: 查询参数，必须包含url
        
        Returns:
            查询结果
        """
        try:
            action = parameters.get('action')    
            account_info = await self._extract_account_info()
            return {
                "status": "success",
                "message": "成功提取信用卡信息",
                "account_info": account_info
            }
            
        except Exception as e:
            logger.error(f"处理信用卡账单查询时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }
    
    async def _extract_account_info(self) -> Dict[str, Any]:
        """
        提取信用卡账户信息 - 完全特定于中信银行的业务逻辑
        
        Returns:
            账户信息字典
        """
        try:
            # 使用JavaScript提取账户信息，专注于中信银行网站的特定结构
            js_script = """
            const result = {
                welcomeMessage: null,
                billAmount: null,
                dueDate: null,
                cardNumber: null,
                minPayment: null
            };
            
            // 查找欢迎信息
            const welcomeElements = Array.from(document.querySelectorAll('*')).filter(el => 
                el.textContent && el.textContent.includes('欢迎您'));
            if (welcomeElements.length > 0) {
                result.welcomeMessage = welcomeElements[0].textContent.trim();
            }
            
            // 查找卡号
            const cardElements = document.querySelectorAll('.ca_num');
            if (cardElements.length > 0) {
                result.cardNumber = cardElements[0].textContent.trim();
            }
            
            // 查找账单金额
            const billElements = document.querySelectorAll('td:nth-child(1) > span.txt14');
            if (billElements.length > 0) {
                for (let el of billElements) {
                    if (el.parentElement && el.parentElement.textContent.includes('本期应还金额')) {
                        result.billAmount = el.textContent.trim();
                        break;
                    }
                }
            }
            
            // 查找最低还款金额
            const minPayElements = document.querySelectorAll('td:nth-child(2) > span.txt14');
            if (minPayElements.length > 0) {
                for (let el of minPayElements) {
                    if (el.parentElement && el.parentElement.textContent.includes('最低还款金额')) {
                        result.minPayment = el.textContent.trim();
                        break;
                    }
                }
            }
            
            // 查找到期还款日
            const dateElements = document.querySelectorAll('td:nth-child(2) > span.txt14');
            if (dateElements.length > 0) {
                for (let el of dateElements) {
                    if (el.parentElement && el.parentElement.textContent.includes('到期还款日')) {
                        result.dueDate = el.textContent.trim();
                        break;
                    }
                }
            }
            
            return result;
            """
            
            account_info = await self.session.execute_script(js_script)
            
            # 格式化并美化提取的数据
            await self._format_account_info(account_info)
            return account_info
        except Exception as e:
            logger.error(f"提取账户信息时出错: {str(e)}")
            return {}
    
    async def _format_account_info(self, account_info: Dict[str, Any]) -> None:
        """
        格式化显示账户信息到日志 - 仅用于日志输出，不影响返回值
        
        Args:
            account_info: 账户信息字典
        """
        try:
            # 提取用户数据
            match = re.search(r'[欢迎您|您好]，([\w*]+)', account_info.get('welcomeMessage', ''))
            username = match.group(1) if match else "未知用户"
            card_number = account_info.get('cardNumber', '未获取到卡号')
            
            # 格式化显示
            info_lines = []
            info_lines.append("="*50)
            info_lines.append("            中信银行信用卡账户信息摘要")
            info_lines.append("="*50)
            
            info_lines.append("\n👤 用户信息:")
            info_lines.append(f"   用户名: {username}")
            info_lines.append(f"   卡号: {card_number}")
            
            info_lines.append("\n💰 账单信息:")
            info_lines.append(f"   应还金额: ¥{account_info.get('billAmount', '未获取到')}")
            info_lines.append(f"   最低还款: ¥{account_info.get('minPayment', '未获取到')}")
            info_lines.append(f"   还款日期: {account_info.get('dueDate', '未获取到')}")
            
            info_lines.append("\n" + "="*50)
            
            # 输出到日志
            for line in info_lines:
                logger.info(line)
        except Exception as e:
            logger.error(f"格式化账户信息时出错: {str(e)}")

    def _extract_domain(self, url: str) -> str:
        """从URL中提取域名"""
        parsed_url = urlparse(url)
        return parsed_url.netloc