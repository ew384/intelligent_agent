# tool_service/src/tools/browser/chromedriver_browser_service.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import logging
import os
import json
import socket
import subprocess
import time
import re

import platform
from pathlib import Path
from typing import Dict, Any, Optional, List
from ..common.cookies_manager import CookiesManager
#from .browser_manager import BrowserManager
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
        self.config = {
            'data_dir': os.environ.get('BROWSER_DATA_DIR', './browser_data'),
            'timeout': int(os.environ.get('BROWSER_TIMEOUT', 30000)),
            'user_agent': os.environ.get(
                'BROWSER_USER_AGENT', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            ),
            'chrome_binary': os.environ.get('CHROME_BINARY', None),
            'debug_port': int(54805)
        }
        
        # 创建数据目录
        self.data_dir = Path(self.config['data_dir'])
        self.screenshots_dir = self.data_dir / 'screenshots'
        self.user_data_dir = Path('./browser_data/claude')#self.data_dir / 'user_data' #
        self.user_agent=self.config['user_agent'] 
        #self._ensure_directories()
        
        # 导入cookie管理器
  
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
            has_running_chrome = True# self._is_debug_port_in_use()
            logger.info(f"has_running_chrome: {str(has_running_chrome)} ")
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
        port = 54805#self.config['debug_port']
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
                        #"/usr/local/bin/chrome-for-testing",
                        #"/usr/bin/chromium-browser",
                        "/usr/bin/google-chrome",
                    ]
                
                # 查找第一个存在的路径
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_binary = path
                        break
            
            if not chrome_binary:
                raise Exception("找不到Chrome可执行文件")
            
            # 创建默认首选项目录（如果不存在）
            preferences_dir = self.user_data_dir / "Default"
            preferences_dir.mkdir(exist_ok=True, parents=True)
            preferences_file = preferences_dir / "Preferences"
            
            # 设置反指纹检测的首选项
            preferences = {
                "profile": {
                    "default_content_setting_values": {
                        "images": 1,
                        "javascript": 1,
                        "cookies": 1
                    }
                },
                "webkit": {
                    "webprefs": {
                        "default_fixed_font_size": 15,
                        "default_font_size": 16,
                        "minimumFontSize": 10,
                        "minimumLogicalFontSize": 9
                    }
                },
                "translate": {
                    "enabled": False
                },
                "credentials_enable_service": False,
                "credentials_enable_autosignin": False,
                "browser": {
                    "check_default_browser": False,
                    "custom_chrome_frame": True,
                    "pepper_flash_settings_enabled": False
                },
                "intl": {
                    "accept_languages": "zh-CN,zh,en-US,en"
                }
            }
            
            # 写入首选项文件
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f)
            
            # 准备注入的初始脚本
            initial_js_path = self.user_data_dir / "initial.js"
            with open(initial_js_path, 'w', encoding='utf-8') as f:
                f.write('''
                    // 隐藏 webdriver 属性
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // 防止检测 Automation Controller
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    
                    // 修改WebGL厂商和渲染信息
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        // UNMASKED_VENDOR_WEBGL
                        if (parameter === 37445) {
                            return 'Google Inc. (Intel)';
                        }
                        // UNMASKED_RENDERER_WEBGL
                        if (parameter === 37446) {
                            return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                        }
                        return getParameter.apply(this, arguments);
                    };
                    
                    // 更多反指纹代码...
                ''')
            
            # 启动Chrome并带有调试端口及反检测选项
            cmd = [
                chrome_binary,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "--disable-automation",
                "--disable-logging",
                "--log-level=3",
                "--window-size=1920,1080",
                "--enable-features=NetworkService,NetworkServiceInProcess",
                "--disable-features=IsolateOrigins,site-per-process",
                "--allow-running-insecure-content",
                "--disable-dev-shm-usage",
                "--disable-gpu", # 在某些环境中可能需要
                "--metrics-recording-only",
                "--password-store=basic",
                "--no-first-run", # 避免首次运行向导
                "--no-default-browser-check",
                "--force-local-ntp", # 使用本地的新标签页
                "--enable-unsafe-swiftshader" 
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
            try:
                port = 54805  
                print(f"Chrome debugging port: {port}")
                
                # Now you can use this port in your Python code
                # For example:
                # chrome_driver = webdriver.Chrome(options=options, port=port)
                
            except Exception as e:
                print(f"Error: {e}")
            # 创建ChromeOptions - 当连接到已运行的Chrome实例时只能使用debuggerAddress选项
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            
            # 创建Service对象
            driver_path = "/usr/local/bin/chromedriver"#BrowserManager().download_chromedriver()
            service = Service(driver_path)
            #service = Service()
            logger.info(f"正在连接到Chrome debug端口: {port}, 使用driver: {driver_path}")
            
            # 创建WebDriver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            #driver = webdriver.Remote(command_executor='http://localhost:4444', options=chrome_options)
            return driver, service
        
        except Exception as e:
            logger.error(f"连接到Chrome失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None