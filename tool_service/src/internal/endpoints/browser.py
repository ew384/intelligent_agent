# 在 tool_service/src/internal/endpoints/browser.py 中整合
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...tools.handlers.credit_card import CreditCardHandler
from ...tools.handlers.hr_resume import HRResumeHandler
from ...tools.handlers.ecommerce import ECommerceHandler
from ...tools.handlers.price_comparison import PriceComparisonHandler
from ...tools.browser.browser_service import BrowserService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# 创建一个全局的浏览器服务实例，设置为显示浏览器窗口
browser_service = BrowserService(headless=False)

@router.post("/credit-card")
async def handle_credit_card_query(parameters: Dict[str, Any]):
    """信用卡查询处理"""
    logger.info("开始处理信用卡账单查询...")
    try:
        # 初始化浏览器
        logger.info("正在初始化浏览器...")
        page = await browser_service.initialize()
        if page is None:
            logger.error("浏览器初始化失败，返回了None")
            return {"status": "error", "message": "Failed to initialize browser"}
            
        logger.info("浏览器初始化成功")
        
        # 创建处理器
        handler = CreditCardHandler(page)
        logger.info(f"开始查询账单: {parameters}")
        
        # 执行查询
        result = await handler.process_bill_query(parameters)
        logger.info(f"查询结果: {result}")
        return result
    except Exception as e:
        logger.error(f"信用卡查询出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        # 确保在出错时也尝试清理资源
        try:
            if page:
                await page.close()
                logger.info("页面已关闭")
        except Exception as e:
            logger.error(f"关闭页面时出错: {str(e)}")

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
