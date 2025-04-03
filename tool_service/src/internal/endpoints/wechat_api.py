# tool_service/src/internal/endpoints/wechat_api.py
from fastapi import APIRouter, Request
from typing import Dict, Any
import logging
from ...tools.browser.browser_manager import BrowserManager
from ...tools.handlers.wechat import WeChatHandler

router = APIRouter()
logger = logging.getLogger(__name__)
browser_manager = BrowserManager()
@router.post("/{action}")
async def handle_wechat_action(action: str, request: Request):
    """
    处理微信操作
    
    Args:
        action: 要执行的操作，如search_contact、send_message等
        request: 请求对象
        
    Returns:
        操作执行结果
    """
    try:
        # 1. 请求解析
        parameters = await request.json()
        parameters['action'] = action
        
        logger.info(f"执行微信操作: {action}, 参数: {parameters}")
        
        # 2. 会话管理 - 使用标签页管理
        service_id = parameters.get('service_id', 'wechat')
        wechat_url = "https://wx2.qq.com/"
        
        # 获取专用标签页
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(
            service_id, 
            url=wechat_url if parameters.get('skip_navigation', False) is not True else None
        )
        
        # 3. 创建处理器并执行操作
        handler = WeChatHandler(session)
        result = await handler.process_query(parameters)
        
        # 4. 资源清理
        if parameters.get('close_session', False):
            await session.close()
            # 从标签页映射中删除
            if tab_handle in browser_manager.tab_services:
                del browser_manager.tab_services[tab_handle]
            
        return result
    except Exception as e:
        logger.error(f"处理微信操作 {action} 时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"操作失败: {str(e)}"}

