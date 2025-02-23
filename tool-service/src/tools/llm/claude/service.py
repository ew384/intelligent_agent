from typing import Dict, Any, AsyncGenerator
from ....tools.browser import BrowserService
from .auth_handler import ClaudeAuthHandler

class ClaudeService:
    """Claude服务实现"""
    def __init__(self, browser_service: BrowserService):
        self.browser = browser_service
        self.auth_handler = None
        self.page = None
        
    async def initialize(self):
        """初始化Claude服务"""
        try:
            self.page = await self.browser.new_page()
            await self.page.goto("https://claude.ai")
            
            # 初始化认证处理器
            self.auth_handler = ClaudeAuthHandler(self.page)
            self.auth_handler.cookies_manager = self.browser.cookies_manager
            
            # 处理登录
            login_result = await self.auth_handler.handle_login()
            if login_result["status"] != "success":
                raise Exception(f"Claude登录失败: {login_result['message']}")
                
        except Exception as e:
            await self.cleanup()
            raise

    async def chat(self, prompt: str, image_path: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """与Claude对话"""
        if not self.auth_handler:
            raise Exception("Service not initialized")
            
        async for response in self.auth_handler.handle_chat_stream(image_path, prompt):
            yield response

    async def cleanup(self):
        """清理资源"""
        if self.page:
            await self.page.close()
            self.page = None