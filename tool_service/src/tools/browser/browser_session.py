# tool_service/src/tools/browser/browser_session.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import time
import random
import asyncio
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

class BrowserSession:
    """
    浏览器会话：提供高级浏览器交互API
    职责:
    1. 封装Selenium WebDriver API
    2. 提供更简单、更一致的浏览器交互方法
    3. 抽象底层实现细节
    """
    
    def __init__(self, driver, service, browser_service):
        """初始化浏览器会话"""
        self.driver = driver
        self.service = service
        self.browser_service = browser_service
        self.wait = WebDriverWait(self.driver, 30)
        self.screenshots_dir = self.browser_service.screenshots_dir
    
    async def goto(self, url: str, timeout: int = 60000) -> bool:
        """
        导航到指定URL
        
        Args:
            url: 要访问的URL
            timeout: 超时时间（毫秒）
            
        Returns:
            是否成功导航
        """
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            logger.info(f"正在导航到: {url}")
            self.driver.get(url)
            
            # 等待页面加载完成
            timeout_seconds = timeout / 1000
            end_time = time.time() + timeout_seconds
            
            # 等待页面加载
            while time.time() < end_time:
                state = self.driver.execute_script("return document.readyState")
                if state == "complete":
                    break
                await asyncio.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"导航到 {url} 失败: {str(e)}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> Any:
        """
        等待选择器出现
        
        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）
            
        Returns:
            找到的元素或None
        """
        try:
            timeout_seconds = timeout / 1000
            element = WebDriverWait(self.driver, timeout_seconds).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"等待选择器 {selector} 超时")
            return None
        except Exception as e:
            logger.error(f"等待选择器 {selector} 出错: {str(e)}")
            return None
    
    async def wait_for_xpath(self, xpath: str, timeout: int = 30000) -> Any:
        """
        等待XPath出现
        
        Args:
            xpath: XPath表达式
            timeout: 超时时间（毫秒）
            
        Returns:
            找到的元素或None
        """
        try:
            timeout_seconds = timeout / 1000
            element = WebDriverWait(self.driver, timeout_seconds).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element
        except TimeoutException:
            logger.warning(f"等待XPath {xpath} 超时")
            return None
        except Exception as e:
            logger.error(f"等待XPath {xpath} 出错: {str(e)}")
            return None
    
    async def click(self, selector: str, wait_time: float = 0.5) -> bool:
        """
        点击元素
        
        Args:
            selector: CSS选择器
            wait_time: 点击后等待时间（秒）
            
        Returns:
            是否成功点击
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return False
            
            # 执行点击
            element.click()
            await asyncio.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"点击选择器 {selector} 失败: {str(e)}")
            return False
    
    async def fill(self, selector: str, text: str, delay: float = 0.1) -> bool:
        """
        填充输入框
        
        Args:
            selector: CSS选择器
            text: 要输入的文本
            delay: 输入延迟（秒）
            
        Returns:
            是否成功填充
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return False
            
            # 先清空输入框
            element.clear()
            
            # 模拟人类输入
            for char in text:
                element.send_keys(char)
                await asyncio.sleep(random.uniform(delay * 0.5, delay * 1.5))
            
            return True
        except Exception as e:
            logger.error(f"填充选择器 {selector} 失败: {str(e)}")
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """
        获取元素文本
        
        Args:
            selector: CSS选择器
            
        Returns:
            元素文本或None
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return None
            
            return element.text
        except Exception as e:
            logger.error(f"获取选择器 {selector} 文本失败: {str(e)}")
            return None
    
    async def get_attribute(self, selector: str, attr: str) -> Optional[str]:
        """
        获取元素属性
        
        Args:
            selector: CSS选择器
            attr: 属性名
            
        Returns:
            属性值或None
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return None
            
            return element.get_attribute(attr)
        except Exception as e:
            logger.error(f"获取选择器 {selector} 属性 {attr} 失败: {str(e)}")
            return None
    
    async def query_selector(self, selector: str) -> Any:
        """
        查询选择器
        
        Args:
            selector: CSS选择器
            
        Returns:
            找到的元素或None
        """
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            return None
        except Exception as e:
            logger.error(f"查询选择器 {selector} 失败: {str(e)}")
            return None
    
    async def query_selector_all(self, selector: str) -> List[Any]:
        """
        查询所有匹配的选择器
        
        Args:
            selector: CSS选择器
            
        Returns:
            找到的元素列表
        """
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            logger.error(f"查询所有选择器 {selector} 失败: {str(e)}")
            return []
    
    async def execute_script(self, script: str, *args) -> Any:
        """
        执行JavaScript
        
        Args:
            script: JavaScript代码
            args: 传递给脚本的参数
            
        Returns:
            脚本执行结果
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"执行脚本失败: {str(e)}")
            return None
    
    async def wait_for_load_state(self, state: str = "networkidle", timeout: int = 30000) -> bool:
        """
        等待页面加载状态
        
        Args:
            state: 加载状态，可选值为"load"、"domcontentloaded"、"networkidle"
            timeout: 超时时间（毫秒）
            
        Returns:
            是否成功等待
        """
        try:
            timeout_seconds = timeout / 1000
            end_time = time.time() + timeout_seconds
            
            if state == "load" or state == "domcontentloaded":
                while time.time() < end_time:
                    document_state = self.driver.execute_script("return document.readyState")
                    if document_state == "complete":
                        return True
                    await asyncio.sleep(0.5)
            
            elif state == "networkidle":
                # 等待网络请求完成
                script = """
                    return window.performance.getEntriesByType('resource').length;
                """
                last_resources_count = self.driver.execute_script(script)
                
                await asyncio.sleep(1)  # 初始等待
                
                while time.time() < end_time:
                    current_resources_count = self.driver.execute_script(script)
                    if current_resources_count == last_resources_count:
                        return True
                    
                    last_resources_count = current_resources_count
                    await asyncio.sleep(1)
            
            return False
        except Exception as e:
            logger.error(f"等待加载状态 {state} 失败: {str(e)}")
            return False
    
    async def screenshot(self, path: str = None) -> str:
        """
        截图
        
        Args:
            path: 保存路径，如果为None则自动生成
            
        Returns:
            截图保存路径
        """
        try:
            if path is None:
                timestamp = int(time.time())
                path = str(self.screenshots_dir / f"screenshot_{timestamp}.png")
            
            self.driver.save_screenshot(path)
            logger.info(f"截图已保存到: {path}")
            return path
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return ""
    
    async def close(self) -> None:
        """关闭会话"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("会话已关闭")
        except Exception as e:
            logger.error(f"关闭会话失败: {str(e)}")
    
    async def wait_for_timeout(self, timeout: int) -> None:
        """
        等待指定时间
        
        Args:
            timeout: 等待时间（毫秒）
        """
        await asyncio.sleep(timeout / 1000)