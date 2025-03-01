# tool_service/src/tools/browser/chromedriver_browser_service.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import logging
import os
import socket
import subprocess
import time
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ChromeDriverBrowserService:
    """
    ChromeDriver浏览器服务：负责创建和管理Chrome浏览器实例
    职责:
    1. 启动Chrome实例
    2. 创建浏览器会话
    3. 管理浏览器配置
    4. 处理浏览器资源清理
    """
    
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
        
        # 导入cookie管理器
        from ..common.cookies_manager import CookiesManager
        self.cookies_manager = CookiesManager(self.data_dir)
        
        # 状态变量
        self.debug_process = None
        self.sessions = []
    
    def _ensure_directories(self) -> None:
        """确保所需目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """
        初始化浏览器并创建新会话
        
        Returns:
            BrowserSession对象
        """
        try:
            # 导入在这里避免循环导入
            from .browser_session import BrowserSession
            
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
    
    async def new_page(self):
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
            
            # 启动Chrome并带有调试端口 - 使用简化命令参数
            cmd = [
                chrome_binary,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # 使用常见用户代理
                "--disable-automation",  # 禁用自动化标志
                "--disable-logging",
                "--log-level=3",
                "--window-size=1920,1080"  # 在启动时设置窗口大小
            ]
            
            # 仅在需要时添加无头模式
            if self.headless:
                cmd.append("--headless=new")
            
            logger.info(f"启动Chrome调试实例: {' '.join(cmd)}")
            
            # 以非阻塞方式启动Chrome
            if not self._is_debug_port_in_use():
                self.debug_process = subprocess.Popen(cmd)
                # 等待Chrome启动并监听端口
                for _ in range(30):
                    if self._is_debug_port_in_use():
                        logger.info(f"Chrome调试端口 {port} 已就绪")
                        return
                    import asyncio
                    await asyncio.sleep(1)
                    
                raise Exception(f"等待Chrome调试端口 {port} 超时")
            else:
                logger.info(f"Chrome调试端口 {port} 已经在使用中")
        
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
            
            # 创建ChromeOptions - 当连接到已运行的Chrome实例时只能使用debuggerAddress选项
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            
            # 创建Service对象
            from .browser_manager import BrowserManager
            driver_path = BrowserManager().download_chromedriver()
            service = Service(driver_path)
            
            logger.info(f"正在连接到Chrome debug端口: {port}, 使用driver: {driver_path}")
            
            # 创建WebDriver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 添加反检测脚本
            self._apply_anti_detection(driver)
            
            return driver, service
        
        except Exception as e:
            logger.error(f"连接到Chrome失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def _apply_anti_detection(self, driver):
        """应用反自动化检测措施"""
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
                            // 创建一个看起来有几个插件的伪造插件列表
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