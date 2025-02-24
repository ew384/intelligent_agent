from .base import BaseHandler
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CreditCardHandler(BaseHandler):
    LOGIN_SELECTORS = {
        'bill_amount': '.bill-amount',
        'logged_in_indicator': '.account-info'
    }

    async def process_bill_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 访问URL
            await self.page.goto(parameters["url"])
            
            # 等待登录
            if not await self._wait_for_login():
                return {"status": "error", "message": "Login timeout"}
            
            # 获取账单金额
            amount = await self._get_bill_amount()
            return {
                "status": "success",
                "amount": amount
            }
        except Exception as e:
            logger.error(f"Bill query failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _wait_for_login(self) -> bool:
        try:
            await self.page.wait_for_selector(
                self.LOGIN_SELECTORS['logged_in_indicator'],
                timeout=300000  # 5分钟超时
            )
            return True
        except Exception:
            return False

    async def _get_bill_amount(self) -> float:
        element = await self.page.wait_for_selector(
            self.LOGIN_SELECTORS['bill_amount']
        )
        amount_text = await element.text_content()
        return float(amount_text.replace('¥', '').replace(',', '').strip())