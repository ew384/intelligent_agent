# tool_service/src/tools/browser/chromedriver_browser_service.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    WebDriverException
)

import socket
import time
import random
import asyncio
import logging
import json
import os
import threading
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from ..common.cookies_manager import CookiesManager

logger = logging.getLogger(__name__)

class BrowserSession:
    """管理浏览器会话的类，对外提供与Playwright相似的API"""
    
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
            
            # 模拟人类行为
            await self._random_scroll()
            
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
            
            # 模拟人类点击行为
            await self._humanlike_click(element)
            await asyncio.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"点击选择器 {selector} 失败: {str(e)}")
            return False
    
    async def click_xpath(self, xpath: str, wait_time: float = 0.5) -> bool:
        """
        点击XPath元素
        
        Args:
            xpath: XPath表达式
            wait_time: 点击后等待时间（秒）
            
        Returns:
            是否成功点击
        """
        try:
            element = await self.wait_for_xpath(xpath)
            if not element:
                return False
            
            # 模拟人类点击行为
            await self._humanlike_click(element)
            await asyncio.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"点击XPath {xpath} 失败: {str(e)}")
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
    
    async def fill_xpath(self, xpath: str, text: str, delay: float = 0.1) -> bool:
        """
        填充XPath输入框
        
        Args:
            xpath: XPath表达式
            text: 要输入的文本
            delay: 输入延迟（秒）
            
        Returns:
            是否成功填充
        """
        try:
            element = await self.wait_for_xpath(xpath)
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
            logger.error(f"填充XPath {xpath} 失败: {str(e)}")
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
    
    async def get_text_xpath(self, xpath: str) -> Optional[str]:
        """
        获取XPath元素文本
        
        Args:
            xpath: XPath表达式
            
        Returns:
            元素文本或None
        """
        try:
            element = await self.wait_for_xpath(xpath)
            if not element:
                return None
            
            return element.text
        except Exception as e:
            logger.error(f"获取XPath {xpath} 文本失败: {str(e)}")
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
    
    async def query_xpath(self, xpath: str) -> Any:
        """
        查询XPath
        
        Args:
            xpath: XPath表达式
            
        Returns:
            找到的元素或None
        """
        try:
            return self.driver.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            return None
        except Exception as e:
            logger.error(f"查询XPath {xpath} 失败: {str(e)}")
            return None
    
    async def query_xpath_all(self, xpath: str) -> List[Any]:
        """
        查询所有匹配的XPath
        
        Args:
            xpath: XPath表达式
            
        Returns:
            找到的元素列表
        """
        try:
            return self.driver.find_elements(By.XPATH, xpath)
        except Exception as e:
            logger.error(f"查询所有XPath {xpath} 失败: {str(e)}")
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
    
    async def _humanlike_click(self, element) -> None:
        """
        模拟人类点击行为
        
        Args:
            element: 要点击的元素
        """
        try:
            # 使用JavaScript执行点击，比较难被检测
            self.driver.execute_script("arguments[0].click();", element)
        except:
            # 如果JavaScript点击失败，尝试常规点击
            element.click()
    
    async def _random_scroll(self) -> None:
        """随机滚动页面以模拟真实用户行为"""
        try:
            # 获取页面高度
            height = self.driver.execute_script("return document.body.scrollHeight")
            if height <= 100:  # 太小的页面不需要滚动
                return
            
            # 随机选择1-3次滚动
            scroll_times = random.randint(1, 3)
            
            for _ in range(scroll_times):
                # 随机选择滚动位置
                scroll_y = random.randint(100, min(height, 1000))
                
                # 平滑滚动
                self.driver.execute_script(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}});")
                
                # 随机等待
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # 随机上下抖动（更像人类行为）
                if random.random() > 0.7:
                    jitter = random.randint(-100, 100)
                    self.driver.execute_script(f"window.scrollBy(0, {jitter});")
                    await asyncio.sleep(random.uniform(0.1, 0.5))
        except Exception as e:
            logger.warning(f"随机滚动失败: {str(e)}")


class ChromeDriverBrowserService:
    """基于ChromeDriver的浏览器服务，替代Playwright"""
    
    def __init__(self, headless: bool = False, config: Dict[str, Any] = None):
        """
        初始化浏览器服务
        
        Args:
            headless: 是否使用无头模式
            config: 配置选项
        """
        self.headless = headless
        self.config = config or {
            'data_dir': os.environ.get('BROWSER_DATA_DIR', './browser_data'),
            'timeout': int(os.environ.get('BROWSER_TIMEOUT', 30000)),
            'user_agent': os.environ.get(
                'BROWSER_USER_AGENT', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            ),
            'chrome_binary': os.environ.get('CHROME_BINARY', None),
            'debug_port': int(os.environ.get('CHROME_DEBUG_PORT', 9222))
        }
        
        # 创建数据目录
        self.data_dir = Path(self.config['data_dir'])
        self.screenshots_dir = self.data_dir / 'screenshots'
        self.user_data_dir = self.data_dir / 'user_data'
        
        self._ensure_directories()
        
        # 初始化Cookies管理器
        self.cookies_manager = CookiesManager(self.data_dir)
        
        # 状态变量
        self.driver = None
        self.service = None
        self.debug_process = None
        self.sessions = []
    
    def _ensure_directories(self) -> None:
        """确保所需目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> BrowserSession:
        """
        初始化浏览器并创建新会话
        
        Returns:
            BrowserSession对象
        """
        try:
            # 检查是否有已运行的Chrome调试实例
            has_running_chrome = self._is_debug_port_in_use()
            
            if not has_running_chrome:
                # 启动Chrome调试实例
                await self._start_chrome_debug()
            
            # 连接到正在运行的调试实例
            driver, service = await self._connect_to_chrome()
            
            if not driver:
                raise Exception("无法连接到Chrome浏览器")
            
            # 创建会话对象
            session = BrowserSession(driver, service, self)
            self.sessions.append(session)
            
            logger.info("浏览器会话初始化成功")
            return session
        except Exception as e:
            logger.error(f"浏览器初始化失败: {str(e)}")
            await self.cleanup()
            return None
    
    async def new_page(self) -> BrowserSession:
        """
        创建新的浏览器页面（会话）
        
        Returns:
            BrowserSession对象
        """
        return await self.initialize()
    
    async def cleanup(self) -> None:
        """清理浏览器资源"""
        # 关闭所有会话
        for session in self.sessions[:]:
            try:
                await session.close()
                self.sessions.remove(session)
            except:
                pass
        
        # 如果我们启动了调试进程，也关闭它
        if self.debug_process and hasattr(self.debug_process, 'terminate'):
            try:
                self.debug_process.terminate()
                self.debug_process = None
                logger.info("Chrome调试进程已终止")
            except:
                pass
    
    def _is_debug_port_in_use(self) -> bool:
        """
        检查调试端口是否被使用
        
        Returns:
            端口是否被使用
        """
        port = self.config['debug_port']
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    async def _start_chrome_debug(self) -> None:
        """启动带有调试端口的Chrome浏览器"""
        import subprocess
        import platform
        
        port = self.config['debug_port']
        user_data_dir = str(self.user_data_dir.absolute())
        
        try:
            # 根据操作系统查找Chrome可执行文件
            chrome_binary = self.config.get('chrome_binary')
            
            if not chrome_binary:
                system = platform.system()
                if system == "Windows":
                    chrome_paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    ]
                elif system == "Darwin":
                    chrome_paths = [
                        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                        "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
                    ]
                else:
                    chrome_paths = [
                        "/usr/local/bin/chrome-for-testing",
                        "/usr/bin/chromium-browser",
                    ]
                
                # 查找第一个存在的路径
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_binary = path
                        break
            
            if not chrome_binary:
                raise Exception("找不到Chrome可执行文件")
            
            # 启动Chrome并带有调试端口 - 使用简化命令参数，与成功示例保持一致
            cmd = [
                chrome_binary,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "--window-size=1920,1080"  # 在启动时设置窗口大小
            ]
            
            # 仅添加必要的参数
            if self.headless:
                cmd.append("--headless=new")
            
            logger.info(f"启动Chrome调试实例: {' '.join(cmd)}")
            
            # 以非阻塞方式启动Chrome
            self.debug_process = subprocess.Popen(cmd)
            
            # 等待Chrome启动并监听端口
            max_wait = 30  # 最多等待30秒
            for _ in range(max_wait):
                if self._is_debug_port_in_use():
                    logger.info(f"Chrome调试端口 {port} 已就绪")
                    return
                await asyncio.sleep(1)
            
            raise Exception(f"等待Chrome调试端口 {port} 超时")
        
        except Exception as e:
            logger.error(f"启动Chrome调试实例失败: {str(e)}")
            raise

    
    async def _connect_to_chrome(self) -> tuple:
        """
        连接到正在运行的Chrome实例
        
        Returns:
            (driver, service)元组
        """
        try:
            port = self.config['debug_port']
            
            # 使用与成功示例相同的方式创建ChromeOptions
            chrome_options = Options()
            # 仅添加debuggerAddress选项，不添加其他可能导致问题的选项
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            
            # 创建Service对象
            driver_path = self._find_chromedriver()
            service = Service(driver_path)
            
            logger.info(f"正在连接到Chrome debug端口: {port}, 使用driver: {driver_path}")
            
            # 创建WebDriver - 与成功示例保持一致的配置方式
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 成功连接后添加CDP命令进行反检测
            try:
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        
                        // 防止检测 Automation Controller
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    '''
                })
            except Exception as script_error:
                logger.warning(f"添加反检测脚本失败: {str(script_error)}")
            
            return driver, service
        
        except Exception as e:
            logger.error(f"连接到Chrome失败: {str(e)}")
            traceback.print_exc()
            return None, None
    
    def _find_chromedriver(self) -> str:
        """
        查找chromedriver可执行文件
        
        Returns:
            chromedriver路径
        """
        import shutil
        import platform
        
        # 首先检查系统路径
        chromedriver = shutil.which("chromedriver")
        if chromedriver:
            return chromedriver
        
        # 然后检查常见路径
        system = platform.system()
        if system == "Windows":
            common_paths = [
                r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
                r"C:\chromedriver\chromedriver.exe",
            ]
        elif system == "Darwin":
            common_paths = [
                "/usr/local/bin/chromedriver",
                "/usr/bin/chromedriver",
                "/Applications/chromedriver",
            ]
        else:
            common_paths = [
                "/usr/local/bin/chromedriver",
                "/usr/bin/chromedriver",
            ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # 如果找不到，尝试在data_dir中查找
        local_chromedriver = self.data_dir / "chromedriver"
        if system == "Windows":
            local_chromedriver = local_chromedriver.with_suffix(".exe")
        
        if local_chromedriver.exists():
            return str(local_chromedriver)
        
        raise Exception("找不到chromedriver可执行文件，请安装它并确保它在PATH中")
