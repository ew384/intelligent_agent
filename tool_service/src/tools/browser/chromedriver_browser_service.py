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
            #await self._random_scroll()
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
            #await self._humanlike_click(element)
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
        模拟真实人类点击行为，使用生成的鼠标轨迹
        
        Args:
            element: 要点击的元素
        """
        try:
            # 获取元素的位置和尺寸
            rect = await self.driver.execute_script("""
                const rect = arguments[0].getBoundingClientRect();
                return {
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height
                };
            """, element)
            
            # 获取当前鼠标位置
            current_mouse = await self.driver.execute_script("""
                return {
                    x: window.mouseX || 100,
                    y: window.mouseY || 100
                };
            """)
            
            # 计算目标点 - 元素内的随机位置
            target_x = rect['left'] + (0.1 + Math.random() * 0.8) * rect['width']
            target_y = rect['top'] + (0.1 + Math.random() * 0.8) * rect['height']
            
            # 生成人类轨迹
            path_script = f"""
                const start = {{ x: {current_mouse['x']}, y: {current_mouse['y']} }};
                const end = {{ x: {target_x}, y: {target_y} }};
                const points = window._humanMouseTracker.generatePath(start, end, {30 + int(random.random() * 30)});
                return points;
            """
            
            mouse_path = await self.driver.execute_script(path_script)
            
            # 使用Actions API来模拟鼠标移动
            actions = webdriver.ActionChains(self.driver)
            
            # 移动鼠标到起始位置
            actions.move_by_offset(
                mouse_path[0]['x'] - current_mouse['x'], 
                mouse_path[0]['y'] - current_mouse['y']
            )
            
            # 跟随生成的路径移动鼠标
            last_x, last_y = mouse_path[0]['x'], mouse_path[0]['y']
            for point in mouse_path[1:]:
                actions.move_by_offset(point['x'] - last_x, point['y'] - last_y)
                
                # 在某些点添加停顿
                if random.random() < 0.3:
                    actions.pause(random.random() * 0.05)
                    
                last_x, last_y = point['x'], point['y']
                
                # 应用移动
                await asyncio.sleep(point['delay'] / 1000)
            
            # 鼠标悬停很短时间
            await asyncio.sleep(random.uniform(0.05, 0.2))
            
            # 执行点击
            actions.click()
            actions.perform()
            
            # 更新页面上的鼠标位置记录
            await self.driver.execute_script(f"""
                window.mouseX = {target_x};
                window.mouseY = {target_y};
            """)
            
            # 点击后短暂等待，更像人类操作
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            logger.warning(f"人类点击模拟失败，回退到基本点击: {str(e)}")
            try:
                # 如果高级点击失败，尝试JavaScript点击
                self.driver.execute_script("arguments[0].click();", element)
            except:
                # 如果JavaScript点击失败，使用最基本的点击
                element.click()
    
    
    async def fill(self, selector: str, text: str, delay: float = 0.1) -> bool:
        """
        以更像人类的方式填充输入框
        
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
            
            # 先点击元素获取焦点（使用人类般的点击）
            #await self._humanlike_click(element)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # 先清空输入框 - 但不使用clear()方法（容易被检测）
            current_value = await self.driver.execute_script("return arguments[0].value", element)
            if current_value:
                for _ in range(len(current_value)):
                    element.send_keys(webdriver.Keys.BACKSPACE)
                    # 有时会有短暂停顿，像人类思考或检查
                    if random.random() < 0.2:
                        await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # 输入文本前可能短暂停顿
            await asyncio.sleep(random.uniform(0.2, 0.7))
            
            # 模拟人类输入 - 有变速和错误修正
            for i, char in enumerate(text):
                # 随机输入错误并修正 (很小概率)
                if random.random() < 0.02 and i < len(text) - 1:
                    wrong_char = chr(ord(char) + random.randint(1, 5))
                    element.send_keys(wrong_char)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    element.send_keys(webdriver.Keys.BACKSPACE)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # 发送正确的字符
                element.send_keys(char)
                
                # 输入速度变化，模拟人类打字
                if i > 0 and char in ".,!? ":
                    # 标点符号后通常会有更长的停顿
                    await asyncio.sleep(random.uniform(delay * 1.5, delay * 3.0))
                elif random.random() < 0.3:
                    # 随机有些字符输入得更慢
                    await asyncio.sleep(random.uniform(delay * 1.2, delay * 2.0))
                else:
                    # 正常延迟
                    await asyncio.sleep(random.uniform(delay * 0.5, delay * 1.5))
                
                # 中途可能短暂停顿，像在思考
                if random.random() < 0.05:
                    await asyncio.sleep(random.uniform(0.3, 1.0))
            
            # 输入完成后，可能有些停顿
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            return True
        except Exception as e:
            logger.error(f"填充选择器 {selector} 失败: {str(e)}")
            return False
    
    

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
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # 使用常见用户代理
                "--disable-automation",  # 更通用的禁用自动化标志
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
        连接到正在运行的Chrome实例，并增强反检测能力
        
        Returns:
            (driver, service)元组
        """
        try:
            port = self.config['debug_port']
            
            # 创建ChromeOptions - 当连接到已运行的Chrome实例时只能使用debuggerAddress选项
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            
            # 创建Service对象
            driver_path = self._find_chromedriver()
            service = Service(driver_path)
            
            logger.info(f"正在连接到Chrome debug端口: {port}, 使用driver: {driver_path}")
            
            # 创建WebDriver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 成功连接后添加CDP命令进行反检测
            try:
                # 更全面的反检测脚本
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        // 隐藏 webdriver 属性
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        
                        // 修改 userAgent 中的 HeadlessChrome 字符串
                        const userAgent = navigator.userAgent;
                        if (userAgent.indexOf("HeadlessChrome") !== -1) {
                            Object.defineProperty(navigator, 'userAgent', {
                                get: () => userAgent.replace("HeadlessChrome", "Chrome")
                            });
                        }
                        
                        // 添加假的浏览器插件数据
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => {
                                // 这会创建一个看起来有几个插件的伪造插件列表
                                const plugins = {
                                    length: 5,
                                    item: i => plugins[i],
                                    0: {
                                        name: 'Chrome PDF Plugin',
                                        description: 'Portable Document Format',
                                        filename: 'internal-pdf-viewer'
                                    },
                                    1: {
                                        name: 'Chrome PDF Viewer',
                                        description: 'Portable Document Format',
                                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'
                                    },
                                    2: {
                                        name: 'Native Client',
                                        description: '',
                                        filename: 'internal-nacl-plugin'
                                    },
                                    3: {
                                        name: 'Chrome Web Store',
                                        description: 'Inline installation for Chrome',
                                        filename: 'inlineinstall'
                                    },
                                    4: {
                                        name: 'Widevine Content Decryption Module',
                                        description: 'Enables Widevine licenses for playback',
                                        filename: 'widevinecdmadapter.dll'
                                    }
                                };
                                return plugins;
                            }
                        });
                        
                        // 修改语言为更自然的配置
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['zh-CN', 'zh', 'en-US', 'en']
                        });
                        
                        // 阻止已知的检测方法
                        if (window.navigator.permissions) {
                            const originalQuery = window.navigator.permissions.query;
                            window.navigator.permissions.query = (parameters) => {
                                if (parameters.name === 'notifications') {
                                    return Promise.resolve({state: Notification.permission});
                                }
                                // 对 Chrome 检测关键点返回已授予权限
                                if (parameters.name === 'clipboard-read' || parameters.name === 'clipboard-write') {
                                    return Promise.resolve({state: 'granted'});
                                }
                                return originalQuery(parameters);
                            };
                        }
                        
                        // 防止检测 Automation Controller
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                        
                        // 添加假的WebGL配置
                        if (window.WebGLRenderingContext) {
                            const getParameter = WebGLRenderingContext.prototype.getParameter;
                            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                                // 处理常见的用于指纹识别的WebGL参数
                                if (parameter === 37445) {
                                    return 'Intel Inc.';
                                }
                                if (parameter === 37446) {
                                    return 'Intel(R) Iris(TM) Graphics 6100';
                                }
                                return getParameter.apply(this, arguments);
                            };
                        }
                        
                        // 篡改 console.debug
                        const oldConsoleDebug = console.debug;
                        console.debug = function() {
                            // 过滤某些可能用于检测的调试消息
                            const args = Array.from(arguments);
                            if (args.some(arg => String(arg).includes('webdriver'))) {
                                return;
                            }
                            return oldConsoleDebug.apply(console, arguments);
                        };
                    '''
                })
                
                # 模拟时区位置等信息
                try:
                    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
                        'timezoneId': 'Asia/Shanghai'
                    })
                except Exception as e:
                    logger.warning(f"设置时区失败: {str(e)}")
                
                # 添加指纹伪装，隐藏自动化特征
                try:
                    driver.execute_cdp_cmd('Network.enable', {})
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'platform': 'Windows',
                        'acceptLanguage': 'zh-CN,zh;q=0.9,en;q=0.8'
                    })
                except Exception as e:
                    logger.warning(f"设置用户代理失败: {str(e)}")
                
            except Exception as script_error:
                logger.warning(f"添加反检测脚本失败: {str(script_error)}")
            
            # 添加真实鼠标轨迹库
            #await self._add_mouse_tracking_helpers(driver)
            
            return driver, service
        
        except Exception as e:
            logger.error(f"连接到Chrome失败: {str(e)}")
            import traceback
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
