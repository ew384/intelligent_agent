# tool_service/src/internal/endpoints/base_api.py
from fastapi import APIRouter, Request
from typing import Dict, Any, Type
import logging
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
import asyncio
from ...tools.handlers.base import BaseHandler

logger = logging.getLogger(__name__)

class BaseAPI:
    """
    基础API处理类，提供通用的浏览器操作API功能
    
    Attributes:
        router: FastAPI路由器
        handler_class: 处理器类，应该是BaseHandler的子类
        chrome_debug_port: Chrome调试端口
    """
    
    def __init__(self, handler_class: Type[BaseHandler], prefix: str = "", chrome_debug_port: int = 54905):
        """
        初始化基础API处理器
        
        Args:
            handler_class: 处理器类，必须是BaseHandler的子类
            prefix: API路由前缀
            chrome_debug_port: Chrome调试端口
        """
        self.router = APIRouter(prefix=prefix)
        self.handler_class = handler_class
        self.chrome_debug_port = chrome_debug_port
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.router.post("/{action}")
        async def handle_action(action: str, request: Request):
            """
            处理浏览器操作
            
            Args:
                action: 要执行的操作
                request: 请求对象
                
            Returns:
                操作执行结果
            """
            browser_use_context = None
            try:
                # 1. 请求解析
                parameters = await request.json()
                parameters['action'] = action
                
                logger.info(f"执行操作: {action}, 参数: {parameters}")
                
                # 2. 获取或创建浏览器上下文
                browser_config = BrowserConfig(
                    cdp_url=f"http://localhost:{self.chrome_debug_port}"
                )
                
                # 创建Browser实例
                browser_use_browser = Browser(config=browser_config)
                
                # 创建BrowserContext
                browser_use_context = BrowserContext(browser=browser_use_browser)
                
                # 初始化上下文
                await browser_use_context._initialize_session()
                
                # 3. 创建处理器并执行操作
                handler = self.handler_class(browser_use_context)
                result = await handler.process_query(parameters)
                
                return result
            except Exception as e:
                logger.error(f"处理操作 {action} 时出错: {str(e)}", exc_info=True)
                return {"status": "error", "message": f"操作失败: {str(e)}"}
            finally:
                # 如果请求参数中未明确指定保持会话，则关闭
                if browser_use_context and not parameters.get('keep_alive', False):
                    try:
                        await browser_use_context.close()
                    except Exception as e:
                        logger.error(f"关闭浏览器上下文失败: {str(e)}")
    
    def get_router(self):
        """获取路由器实例"""
        return self.router