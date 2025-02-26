# tool_service/src/internal/endpoints/browser.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import traceback
from ...tools.browser.browser_manager import BrowserManager
from ...tools.handlers.credit_card import CreditCardHandler
from ...tools.handlers.hr_resume import HRResumeHandler
from ...tools.handlers.ecommerce import ECommerceHandler
from ...tools.handlers.price_comparison import PriceComparisonHandler

router = APIRouter()
logger = logging.getLogger(__name__)

# 创建浏览器管理器实例
browser_manager = BrowserManager()

@router.post("/credit-card")
async def handle_credit_card_query(parameters: Dict[str, Any]):
    """信用卡查询处理"""
    logger.info("开始处理信用卡账单查询...")
    session = None
    
    try:
        # 获取浏览器服务
        browser_service = await browser_manager.get_browser_service("credit_card")
        
        # 初始化浏览器
        logger.info("正在初始化浏览器...")
        session = await browser_service.initialize()
        if session is None:
            logger.error("浏览器初始化失败，返回了None")
            return {"status": "error", "message": "Failed to initialize browser"}
            
        logger.info("浏览器初始化成功")
        
        # 创建处理器
        handler = CreditCardHandler(session)
        logger.info(f"开始查询账单: {parameters}")
        
        # 执行查询
        result = await handler.process_bill_query(parameters)
        logger.info(f"查询结果: {result}")
        return result
    except Exception as e:
        logger.error(f"信用卡查询出错: {str(e)}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        # 我们不关闭会话，让浏览器管理器来管理会话的生命周期
        pass

@router.post("/hr-resume")
async def handle_resume_query(parameters: Dict[str, Any]):
    """简历查询处理"""
    logger.info("开始处理简历查询...")
    session = None
    
    try:
        # 获取浏览器服务
        browser_service = await browser_manager.get_browser_service("hr_resume")
        
        # 初始化浏览器
        session = await browser_service.initialize()
        if session is None:
            return {"status": "error", "message": "Failed to initialize browser"}
        
        # 创建处理器
        handler = HRResumeHandler(session)
        
        # 执行查询
        result = await handler.process_query(parameters)
        return result
    except Exception as e:
        logger.error(f"简历查询出错: {str(e)}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        pass

@router.post("/ecommerce")
async def handle_ecommerce_query(parameters: Dict[str, Any]):
    """电商平台操作处理"""
    logger.info("开始处理电商平台操作...")
    session = None
    
    try:
        # 获取浏览器服务
        browser_service = await browser_manager.get_browser_service("ecommerce")
        
        # 初始化浏览器
        session = await browser_service.initialize()
        if session is None:
            return {"status": "error", "message": "Failed to initialize browser"}
        
        # 创建处理器
        handler = ECommerceHandler(session)
        
        # 执行操作
        result = await handler.process_query(parameters)
        return result
    except Exception as e:
        logger.error(f"电商平台操作出错: {str(e)}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        pass

@router.post("/price-comparison")
async def handle_price_comparison(parameters: Dict[str, Any]):
    """价格比较处理"""
    logger.info("开始处理价格比较...")
    session = None
    
    try:
        # 获取浏览器服务
        browser_service = await browser_manager.get_browser_service("price_comparison")
        
        # 初始化浏览器
        session = await browser_service.initialize()
        if session is None:
            return {"status": "error", "message": "Failed to initialize browser"}
        
        # 创建处理器
        handler = PriceComparisonHandler(session)
        
        # 执行操作
        result = await handler.process_query(parameters)
        return result
    except Exception as e:
        logger.error(f"价格比较出错: {str(e)}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        pass

@router.post("/browser-status")
async def handle_browser_status():
    """获取浏览器状态"""
    try:
        services = browser_manager.list_browser_services()
        return {
            "status": "success",
            "services": services,
            "count": len(services)
        }
    except Exception as e:
        logger.error(f"获取浏览器状态出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/close-browser")
async def handle_close_browser(parameters: Dict[str, Any]):
    """关闭浏览器"""
    try:
        service_id = parameters.get("service_id")
        if not service_id:
            return {"status": "error", "message": "Service ID is required"}
        
        success = await browser_manager.close_browser_service(service_id)
        if success:
            return {"status": "success", "message": f"Browser service {service_id} closed"}
        else:
            return {"status": "error", "message": f"Failed to close browser service {service_id}"}
    except Exception as e:
        logger.error(f"关闭浏览器出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/download-chromedriver")
async def handle_download_chromedriver(parameters: Dict[str, Any]):
    """下载ChromeDriver"""
    try:
        force = parameters.get("force", False)
        driver_path = browser_manager.download_chromedriver(force)
        return {
            "status": "success", 
            "message": "ChromeDriver downloaded successfully",
            "path": driver_path
        }
    except Exception as e:
        logger.error(f"下载ChromeDriver出错: {str(e)}")
        return {"status": "error", "message": str(e)}
