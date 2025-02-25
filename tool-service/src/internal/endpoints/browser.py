# tool-service/src/internal/endpoints/browser.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...tools.handlers.credit_card import CreditCardHandler
from ...tools.handlers.hr_resume import HRResumeHandler
from ...tools.handlers.ecommerce import ECommerceHandler
from ...tools.handlers.price_comparison import PriceComparisonHandler
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

@router.post("/hr-resume")
async def handle_resume_query(parameters: Dict[str, Any]):
    """简历查询处理"""
    try:
        page = await browser_service.initialize()
        handler = HRResumeHandler(page)
        return await handler.process_hr_query(parameters)
    finally:
        await browser_service.cleanup()

@router.post("/ecommerce")
async def handle_ecommerce_query(parameters: Dict[str, Any]):
    """电商平台操作处理"""
    try:
        page = await browser_service.initialize()
        handler = ECommerceHandler(page)
        return await handler.process_ecommerce_action(parameters)
    finally:
        await browser_service.cleanup()

@router.post("/price-comparison")
async def handle_price_comparison(parameters: Dict[str, Any]):
    """价格比较处理"""
    try:
        page = await browser_service.initialize()
        handler = PriceComparisonHandler(page)
        return await handler.process_price_comparison(parameters)
    finally:
        await browser_service.cleanup()