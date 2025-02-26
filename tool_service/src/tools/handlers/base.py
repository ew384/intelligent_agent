# tool_service/src/tools/handlers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class BaseHandler(ABC):
    """处理器基类，所有特定处理器都应继承此类"""
    
    def __init__(self, session):
        """
        初始化处理器
        
        Args:
            session: 浏览器会话对象
        """
        self.session = session
    
    @abstractmethod
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理查询的抽象方法
        
        Args:
            parameters: 查询参数
            
        Returns:
            处理结果
        """
        pass
    
    async def wait_for_user_interaction(self, message: str = "请在浏览器中完成操作，然后按回车继续...") -> None:
        """
        等待用户交互
        
        Args:
            message: 显示给用户的消息
        """
        # 如果在session上显示消息的方法存在，则使用它
        if hasattr(self.session, 'execute_script'):
            try:
                await self.session.execute_script(f"""
                    const div = document.createElement('div');
                    div.id = 'user-interaction-message';
                    div.style = 'position: fixed; top: 0; left: 0; right: 0; background: #ff5722; color: white; padding: 10px; text-align: center; z-index: 9999; font-size: 16px;';
                    div.innerText = '{message}';
                    document.body.appendChild(div);
                """)
            except Exception as e:
                logger.error(f"显示用户交互消息失败: {str(e)}")
        
        # 在控制台打印消息
        print(message)
        
        # 等待用户按回车键
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # 移除消息
        if hasattr(self.session, 'execute_script'):
            try:
                await self.session.execute_script("""
                    const div = document.getElementById('user-interaction-message');
                    if (div) div.remove();
                """)
            except Exception as e:
                logger.error(f"移除用户交互消息失败: {str(e)}")
    
    async def extract_text(self, selector: str, default: str = "") -> str:
        """
        提取元素文本
        
        Args:
            selector: CSS选择器
            default: 默认值
            
        Returns:
            元素文本或默认值
        """
        try:
            text = await self.session.get_text(selector)
            return text or default
        except Exception as e:
            logger.error(f"提取文本失败: {str(e)}")
            return default
    
    async def extract_text_xpath(self, xpath: str, default: str = "") -> str:
        """
        提取XPath元素文本
        
        Args:
            xpath: XPath表达式
            default: 默认值
            
        Returns:
            元素文本或默认值
        """
        try:
            text = await self.session.get_text_xpath(xpath)
            return text or default
        except Exception as e:
            logger.error(f"提取XPath文本失败: {str(e)}")
            return default
    
    async def safe_fill(self, selector: str, text: str, retry_count: int = 3) -> bool:
        """
        安全填充输入框，包含重试逻辑
        
        Args:
            selector: CSS选择器
            text: 要输入的文本
            retry_count: 重试次数
            
        Returns:
            是否成功填充
        """
        for attempt in range(retry_count):
            try:
                result = await self.session.fill(selector, text)
                if result:
                    return True
                
                # 如果填充失败，等待一下再重试
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"填充选择器 {selector} 失败 (尝试 {attempt+1}/{retry_count}): {str(e)}")
                await asyncio.sleep(1)
        
        return False
    
    async def safe_click(self, selector: str, retry_count: int = 3) -> bool:
        """
        安全点击元素，包含重试逻辑
        
        Args:
            selector: CSS选择器
            retry_count: 重试次数
            
        Returns:
            是否成功点击
        """
        for attempt in range(retry_count):
            try:
                result = await self.session.click(selector)
                if result:
                    return True
                
                # 如果点击失败，等待一下再重试
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"点击选择器 {selector} 失败 (尝试 {attempt+1}/{retry_count}): {str(e)}")
                await asyncio.sleep(1)
        
        return False
    
    async def is_element_visible(self, selector: str) -> bool:
        """
        检查元素是否可见
        
        Args:
            selector: CSS选择器
            
        Returns:
            元素是否可见
        """
        try:
            element = await self.session.query_selector(selector)
            if not element:
                return False
            
            # 检查元素是否可见
            is_visible = await self.session.execute_script("""
                function isVisible(el) {
                    if (!el.offsetParent && el.offsetWidth === 0 && el.offsetHeight === 0) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                }
                return isVisible(arguments[0]);
            """, element)
            
            return is_visible
        except Exception as e:
            logger.error(f"检查元素可见性失败: {str(e)}")
            return False
    
    async def wait_for_any_selector(self, selectors: list, timeout: int = 30000) -> str:
        """
        等待任意选择器出现
        
        Args:
            selectors: CSS选择器列表
            timeout: 超时时间（毫秒）
            
        Returns:
            第一个出现的选择器或空字符串
        """
        try:
            # 创建一个任务列表，每个任务等待一个选择器
            tasks = []
            for selector in selectors:
                tasks.append(self.session.wait_for_selector(selector, timeout))
            
            # 等待第一个完成的任务
            done, pending = await asyncio.wait(
                tasks, 
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout/1000
            )
            
            # 取消其余任务
            for task in pending:
                task.cancel()
            
            # 如果有任务完成，返回相应的选择器
            if done:
                result = done.pop().result()
                if result:
                    index = tasks.index(next(t for t in done))
                    return selectors[index]
            
            return ""
        except Exception as e:
            logger.error(f"等待任意选择器失败: {str(e)}")
            return ""
