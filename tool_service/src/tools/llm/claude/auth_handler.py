from typing import Dict, Any, AsyncGenerator
import logging
import time
import json
import asyncio
from .selectors import CLAUDE_SELECTORS

logger = logging.getLogger(__name__)

class ClaudeAuthHandler:
    """Handles authentication and interaction with Claude AI"""
    
    def __init__(self, session):
        """
        Initialize Claude auth handler
        
        Args:
            session: Browser session object
        """
        self.session = session
        self.domain = "claude.ai"
        self.logged_in = False
        
    async def handle_login(self) -> Dict[str, Any]:
        """
        Handle the login process for Claude
        
        Returns:
            Dict with login status
        """
        try:
            # 检查是否已登录
            is_logged_in = await self._check_logged_in()
            if is_logged_in:
                self.logged_in = True
                logger.info("已通过cookie成功登录Claude")
                return {"status": "success", "message": "已使用cookie登录"}
            
            # 如果cookie登录失败，我们需要处理手动登录
            logger.info("Cookie登录失败，等待手动登录")
            
            # 等待手动登录
            is_logged_in = await self._wait_for_manual_login()
            if is_logged_in:
                self.logged_in = True
                return {"status": "success", "message": "已手动登录"}
            else:
                return {"status": "error", "message": "登录超时"}
                
        except Exception as e:
            logger.error(f"Claude登录错误: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _check_logged_in(self) -> bool:
        """
        Check if we're currently logged in to Claude
        
        Returns:
            Boolean indicating logged in status
        """
        try:
            # 等待登录按钮(未登录)或聊天按钮(已登录)
            logged_in = await self.session.wait_for_selector(
                CLAUDE_SELECTORS['logged_in_indicator'],
                timeout=5000
            )
            return logged_in is not None
        except:
            return False
            
    async def _wait_for_manual_login(self, timeout: int = 300000) -> bool:
        """
        Wait for user to manually log in
        
        Args:
            timeout: Maximum time to wait in milliseconds (default 5 minutes)
            
        Returns:
            Boolean indicating success
        """
        try:
            # 显示消息告知用户
            await self.session.execute_script("""() => {
                const div = document.createElement('div');
                div.id = 'login-message';
                div.style = 'position: fixed; top: 0; left: 0; right: 0; background: red; color: white; padding: 10px; text-align: center; z-index: 9999;';
                div.innerText = '请登录Claude';
                document.body.appendChild(div);
            }""")
            
            # 提示用户手动登录
            print("请在浏览器中登录Claude，然后按回车继续...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
            # 检查是否登录成功
            is_logged_in = await self._check_logged_in()
            
            # 移除消息
            await self.session.execute_script("""() => {
                const div = document.getElementById('login-message');
                if (div) div.remove();
            }""")
            
            return is_logged_in
            
        except Exception as e:
            logger.error(f"等待手动登录出错: {str(e)}")
            return False
            
    async def handle_chat_stream(self, image_path: str = None, prompt: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle chat interaction with Claude
        
        Args:
            image_path: Optional path to image to upload
            prompt: Text prompt to send
            
        Yields:
            Dict containing response chunks
        """
        try:
            if not self.logged_in:
                yield {"status": "error", "message": "未登录"}
                return
                
            # 开始新聊天，如果需要
            new_chat_button = await self.session.query_selector(CLAUDE_SELECTORS['new_chat_button'])
            if new_chat_button:
                await self.session.click(CLAUDE_SELECTORS['new_chat_button'])
                
            # 上传图片，如果提供
            if image_path:
                await self._upload_image(image_path)
                
            # 输入提示文本
            if prompt:
                await self.session.fill(CLAUDE_SELECTORS['prompt_textarea'], prompt)
                
                # 发送消息
                await self.session.click(CLAUDE_SELECTORS['send_button'])
                
                # 等待响应开始
                await self.session.wait_for_selector(CLAUDE_SELECTORS['response_container'], timeout=60000)
                
                # 监控响应直到完成
                response_text = ""
                is_complete = False
                
                while not is_complete:
                    # 获取当前响应文本
                    response_element = await self.session.query_selector(CLAUDE_SELECTORS['response_container'])
                    if response_element:
                        new_text = await self.session.execute_script(
                            "return arguments[0].textContent", 
                            response_element
                        )
                        
                        # 如果文本已更改，产生新部分
                        if new_text != response_text:
                            # 仅产生新内容
                            new_content = new_text[len(response_text):]
                            response_text = new_text
                            
                            yield {
                                "status": "streaming",
                                "content": new_content,
                                "complete": False
                            }
                    
                    # 检查响应是否完成
                    thinking_indicator = await self.session.query_selector(CLAUDE_SELECTORS['thinking_indicator'])
                    is_complete = thinking_indicator is None
                    
                    if not is_complete:
                        # 短暂等待再次检查
                        await asyncio.sleep(0.5)
                
                # 最终产生带有完成标志
                yield {
                    "status": "success",
                    "content": response_text,
                    "complete": True
                }
            
        except Exception as e:
            logger.error(f"聊天错误: {str(e)}")
            yield {"status": "error", "message": str(e)}
    
    async def _upload_image(self, image_path: str) -> bool:
        """
        Upload an image to Claude
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Boolean indicating success
        """
        try:
            # 点击上传按钮
            upload_button = await self.session.query_selector(CLAUDE_SELECTORS['upload_button'])
            if not upload_button:
                return False
            
            # 设置文件输入处理
            file_input_selector = 'input[type="file"]'
            file_input = await self.session.query_selector(file_input_selector)
            
            if not file_input:
                # 如果没有文件输入，可能需要点击按钮触发它
                await self.session.click(CLAUDE_SELECTORS['upload_button'])
                file_input = await self.session.wait_for_selector(file_input_selector, timeout=5000)
            
            if file_input:
                # 使用JavaScript设置文件
                await self.session.execute_script(
                    """
                    const input = arguments[0];
                    const filePath = arguments[1];
                    
                    // 创建一个自定义事件
                    const dataTransfer = new DataTransfer();
                    const file = new File([''], filePath.split('/').pop(), { type: 'image/png' });
                    dataTransfer.items.add(file);
                    input.files = dataTransfer.files;
                    
                    // 触发change事件
                    const event = new Event('change', { bubbles: true });
                    input.dispatchEvent(event);
                    """,
                    file_input, image_path
                )
                
                # 等待上传完成
                await self.session.wait_for_selector(CLAUDE_SELECTORS['image_preview'], timeout=30000)
                return True
            else:
                logger.error("找不到文件输入元素")
                return False
                
        except Exception as e:
            logger.error(f"图片上传错误: {str(e)}")
            return False
