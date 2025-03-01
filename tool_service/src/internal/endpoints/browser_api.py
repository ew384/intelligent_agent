# tool_service/src/internal/endpoints/browser_api.py
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
from ...tools.browser.browser_manager import BrowserManager
from ...tools.handlers.browser_operations import BrowserOperations
from ...tools.handlers.credit_card import CreditCardHandler

router = APIRouter()
logger = logging.getLogger(__name__)
browser_manager = BrowserManager()
"""
浏览器API端点模块
职责:
1. 提供HTTP接口接收外部请求
2. 管理浏览器会话生命周期
3. 将请求转发给相应的处理器
4. 格式化HTTP响应
"""
@router.post("/{action}")
async def handle_browser_action(action: str, request: Request):
    """
    处理通用浏览器操作
    
    Args:
        action: 要执行的操作类型，如navigate、click等
        request: 请求对象
        
    Returns:
        操作执行结果
    """
    try:
        # 1. 请求解析 - API层职责
        parameters = await request.json()
        parameters['action'] = action
        logger.info(f"执行浏览器操作: {action}, 参数: {parameters}")
        # 2. 会话管理 - API层职责
        service_id = parameters.get('service_id', 'default')
        browser_service = await browser_manager.get_browser_service(service_id)
        session = await browser_service.initialize()
        
        # 3. 调用处理器 - 委托业务逻辑
        handler = BrowserOperations(session)  # 注意这里使用了新名称
        result = await handler.process_query(parameters)
        
        # 4. 清理资源 - API层职责
        if parameters.get('close_session', False):
            await session.close()
        return result
    except Exception as e:
        logger.error(f"处理浏览器操作 {action} 时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"操作失败: {str(e)}"}

@router.post("/credit-card")
async def handle_credit_card(request: Request):
    """
    处理信用卡查询
    
    Args:
        request: 请求对象
        
    Returns:
        查询结果
    """
    try:
        # 解析请求体
        parameters = await request.json()
        
        logger.info(f"执行信用卡查询，参数: {parameters}")
        
        # 获取浏览器服务
        service_id = parameters.get('service_id', 'credit_card')
        browser_service = await browser_manager.get_browser_service(service_id)
        
        if not browser_service:
            return {"status": "error", "message": "无法创建浏览器服务"}
        
        # 初始化会话
        session = await browser_service.initialize()
        if not session:
            return {"status": "error", "message": "无法创建浏览器会话"}
        
        # 创建信用卡处理器
        handler = CreditCardHandler(session)
        
        # 执行查询
        result = await handler.process_query(parameters)
        
        # 如果需要关闭会话，则关闭
        if parameters.get('close_session', False):
            await session.close()
        
        return result
    except Exception as e:
        logger.error(f"处理信用卡查询时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"查询失败: {str(e)}"}