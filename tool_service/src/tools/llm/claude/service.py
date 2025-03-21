from typing import Dict, Any, AsyncGenerator
from ...browser.browser_manager import BrowserManager
from .auth_handler import ClaudeAuthHandler

class ClaudeService:
    """Claude服务实现"""
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.auth_handler = None
        self.session = None
        
    async def initialize(self):
        """初始化Claude服务"""
        try:
            # 获取浏览器服务
            browser_service = await self.browser_manager.get_browser_service("claude")
            
            # 初始化会话
            self.session = await browser_service.initialize()
            if not self.session:
                raise Exception("浏览器会话初始化失败")
                
            # 导航到Claude
            #await self.session.goto("https://claude.ai")
            
            # 初始化认证处理器
            self.auth_handler = ClaudeAuthHandler(self.session)
            
            # 处理登录
            #login_result = await self.auth_handler.handle_login()
            #if login_result["status"] != "success":
            #    raise Exception(f"Claude登录失败: {login_result['message']}")
                
        except Exception as e:
            await self.cleanup()
            raise

    async def chat(self, prompt: str = None, image_path: str = None, stream: bool = True, new_chat: bool = False) -> AsyncGenerator[str, None]:
        """与Claude对话
    
        Args:
            prompt: 发送给Claude的提示文本
            image_path: 可选图片路径
            new_chat: 是否开始新聊天
        """
        if not self.auth_handler:
            raise Exception("Service not initialized")
    
        async for response in self.auth_handler.handle_chat_stream(prompt, image_path, stream, new_chat):
            yield response

    async def cleanup(self):
        """清理资源"""
        if self.session:
            # 注意：我们不关闭会话，由浏览器管理器负责管理会话生命周期
            self.session = None
