from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...tools.handlers.credit_card import CreditCardHandler
from ...tools.browser.browser_service import BrowserService

router = APIRouter()
browser_service = BrowserService(headless=False)

@router.post("/credit-card")
async def handle_credit_card_query(parameters: Dict[str, Any]):
    """信用卡查询处理"""
    try:
        page = await browser_service.initialize()
        handler = CreditCardHandler(page)
        return await handler.process_bill_query(parameters)
    finally:
        await browser_service.cleanup()

@router.post("/hr-resume")  # 预留HR场景API
async def handle_resume_query(parameters: Dict[str, Any]):
    """简历查询处理"""
    pass  # 预留实现