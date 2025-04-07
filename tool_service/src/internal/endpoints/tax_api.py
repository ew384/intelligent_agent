# tool_service/src/internal/endpoints/tax_api.py
from fastapi import APIRouter, Request
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
#from ...tools.browser.browser_manager import BrowserManager
from ...tools.handlers.tax_handler import TaxHandler

router = APIRouter()
logger = logging.getLogger(__name__)
#browser_manager = BrowserManager()
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
import asyncio
@router.post("/query_complete")
async def query_tax_records_complete(request: Request):
    """
    一次性完成整个税务查询流程：从导航到查询返回结果的自动化查询
    
    Args:
        request: 请求对象，可以包含以下参数:
            city: 城市名称（默认为"深圳市"）
            start_date: 开始日期（格式：YYYY-MM-DD），可选，默认为90天前
            end_date: 结束日期（格式：YYYY-MM-DD），可选，默认为当前日期
            wait_for_login: 是否等待用户登录（默认为True）
            login_timeout: 登录等待超时时间（默认为300秒）
            service_id: 服务ID，用于cookie管理（默认为'tax_service'）
            close_session: 查询完成后是否关闭会话（默认为False）
        
    Returns:
        完整的查询结果
    """
    pass
@router.post("/{action}")
async def handle_tax_action(action: str, request: Request):
    """
    处理电子税务局操作
    
    Args:
        action: 要执行的操作，如check_login、select_city、query_tax_record等
        request: 请求对象
        
    Returns:
        操作执行结果
    """
    browser_use_context = None
    try:
        # 1. 请求解析
        parameters = await request.json()
        parameters['action'] = action
        
        logger.info(f"执行税务操作: {action}, 参数: {parameters}")
        
        # 2. 获取或创建浏览器上下文
        chrome_debug_port = 54805
        
        # 配置连接到已有的Chrome
        browser_config = BrowserConfig(
            cdp_url=f"http://localhost:{chrome_debug_port}"
        )
        
        # 创建Browser实例
        browser_use_browser = Browser(config=browser_config)
        
        # 创建BrowserContext
        browser_use_context = BrowserContext(browser=browser_use_browser)
        
        # 初始化上下文
        await browser_use_context._initialize_session()
        
        # 3. 创建处理器并执行操作
        handler = TaxHandler(browser_use_context)
        result = await handler.process_query(parameters)
        
        return result
    except Exception as e:
        logger.error(f"处理税务操作 {action} 时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"操作失败: {str(e)}"}
    finally:
        # 如果请求参数中明确指定了关闭会话，则在此处关闭
        # 只有在创建了上下文但未能成功创建Handler的情况下，才需要在此处直接关闭
        if browser_use_context and not parameters.get('keep_alive', False):
            try:
                # 避免使用asyncio.run()
                await browser_use_context.close()
            except Exception as e:
                logger.error(f"关闭浏览器上下文失败: {str(e)}")