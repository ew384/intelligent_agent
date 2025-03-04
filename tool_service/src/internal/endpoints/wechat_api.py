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


@router.post("/login")
async def wechat_login(request: Request):
    """
    初始化微信登录，并等待用户扫码登录
    
    Args:
        request: 请求对象
        
    Returns:
        登录结果
    """
    try:
        parameters = await request.json()
        service_id = parameters.get('service_id', 'wechat')
        
        # 是否等待登录完成
        wait_for_login = parameters.get('wait_for_login', True)
        
        # 是否强制重新登录（忽略已有 cookies）
        force_login = parameters.get('force_login', False)
        
        # 如果强制重新登录，删除现有 cookies
        if force_login:
            browser_service = await browser_manager.get_browser_service(service_id)
            browser_service.cookies_manager.delete_cookies(service_id)
            logger.info(f"已删除服务 {service_id} 的 cookies")
        
        # 获取或创建浏览器标签页
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(
            service_id, 
            url="https://wx2.qq.com"
        )
        
        # 创建处理器
        handler = WeChatHandler(session)
        
        # 检查登录状态并等待登录
        result = await handler.check_wechat_login({
            "service_id": service_id,
            "wait_for_login": wait_for_login,
            "login_timeout": parameters.get('login_timeout', 300)
        })
        
        # 关闭会话，如果请求关闭
        if parameters.get('close_session', False):
            await session.close()
            if tab_handle in browser_manager.tab_services:
                del browser_manager.tab_services[tab_handle]
        
        return result
    except Exception as e:
        logger.error(f"微信登录初始化失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"登录初始化失败: {str(e)}",
            "logged_in": False
        }

@router.post("/cookies/save")
async def save_wechat_cookies(request: Request):
    """
    保存微信 cookies
    
    Args:
        request: 请求对象
        
    Returns:
        保存结果
    """
    try:
        parameters = await request.json()
        service_id = parameters.get('service_id', 'wechat')
        
        # 获取浏览器服务
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(service_id)
        
        # 保存 cookies
        result = await session.save_cookies(service_id)
        
        if result:
            return {
                "status": "success", 
                "message": f"成功保存微信 cookies"
            }
        else:
            return {
                "status": "error",
                "message": "保存 cookies 失败"
            }
    except Exception as e:
        logger.error(f"保存微信 cookies 失败: {str(e)}")
        return {"status": "error", "message": f"保存失败: {str(e)}"}

@router.post("/cookies/load")
async def load_wechat_cookies(request: Request):
    """
    加载微信 cookies
    
    Args:
        request: 请求对象
        
    Returns:
        加载结果
    """
    try:
        parameters = await request.json()
        service_id = parameters.get('service_id', 'wechat')
        
        # 获取浏览器服务
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(
            service_id,
            url=parameters.get('url', 'https://wx.qq.com/')
        )
        
        # 加载 cookies
        result = await session.load_cookies(service_id, domain="wx.qq.com")
        
        if result:
            # 刷新页面
            await session.refresh_page()
            await asyncio.sleep(2)
            
            return {
                "status": "success", 
                "message": f"成功加载微信 cookies"
            }
        else:
            return {
                "status": "error",
                "message": "未找到可用的 cookies"
            }
    except Exception as e:
        logger.error(f"加载微信 cookies 失败: {str(e)}")
        return {"status": "error", "message": f"加载失败: {str(e)}"}
