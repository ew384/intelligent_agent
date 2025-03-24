# tool_service/src/tools/browser/browser_manager.py
import os
import logging
import atexit
import tempfile
import shutil
import sys
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import zipfile
import socket
import asyncio

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    浏览器管理器：负责管理浏览器实例和驱动程序
    职责:
    1. 管理浏览器服务实例
    2. 下载和管理驱动程序
    3. 处理资源清理
    4. 分配端口号
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化浏览器管理器"""
        if self._initialized:
            return
            
        self.config = config or {}
        self.browser_services = {}
        self.running_processes = []
        
        # 默认配置
        self.default_config = {
            'data_dir': os.environ.get('BROWSER_DATA_DIR', './browser_data'),
            'chrome_binary': os.environ.get('CHROME_BINARY', None),
            'debug_port_start': int(os.environ.get('CHROME_DEBUG_PORT_START', 9222)),
            'max_instances': int(os.environ.get('MAX_BROWSER_INSTANCES', 5)),
            'headless': os.environ.get('BROWSER_HEADLESS', 'false').lower() == 'true'
        }
        
        # 合并配置
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
        
        # 确保数据目录存在
        self.data_dir = Path(self.config['data_dir'])
        #self.data_dir.mkdir(parents=True, exist_ok=True)
        # 记录标签页到服务的映射关系
        self.tab_services = {}  # 格式：{tab_handle: service_name}
        # 注册退出时的清理函数
        atexit.register(self.cleanup)
        
        self._initialized = True

    
    async def get_or_create_service_tab(self, service_id: str, url: str = None):
        """
        获取服务对应的标签页，如果不存在则创建
        
        Args:
            service_id: 服务ID
            url: 如果创建新标签页，要导航到的URL
            
        Returns:
            元组: (browser_service, session, tab_handle)
        """
        # 获取浏览器服务
        browser_service = await self.get_browser_service(service_id)
        
        # 获取会话
        session = await browser_service.initialize()
        
        # 获取所有当前标签页
        all_tabs = await session.get_all_tabs()
        logger.info(f"发现 {len(all_tabs)} 个标签页")
        
        # 基于URL查找匹配的标签页
        found_tab = None
        if url:
            from urllib.parse import urlparse
            target_domain = urlparse(url).netloc
            
            # 遍历所有标签页寻找匹配的URL
            for tab in all_tabs:
                try:
                    # 尝试切换到这个标签页
                    success = await session.switch_to_tab(tab)
                    if not success:
                        continue
                        
                    # 获取当前URL
                    current_url = await session.execute_script("return window.location.href")
                    current_domain = urlparse(current_url).netloc
                    
                    logger.info(f"检查标签页 {tab}: URL={current_url}, 域名={current_domain}")
                    
                    # 检查是否为匹配的域名
                    if current_domain and (target_domain in current_domain or current_domain in target_domain):
                        logger.info(f"找到匹配域名的标签页: {tab}, 域名: {current_domain}")
                        # 记录标签页服务映射
                        self.tab_services[tab] = service_id
                        found_tab = tab
                        break
                except Exception as e:
                    logger.warning(f"检查标签页 {tab} 时出错: {str(e)}")
                    continue
        
        # 如果找到匹配的标签页，直接返回
        if found_tab:
            return browser_service, session, found_tab
        
        # 查找已有的服务标签页（根据服务ID映射）
        existing_tab = None
        for tab, tab_service in self.tab_services.items():
            if tab_service == service_id:
                try:
                    # 切换到已存在的标签页
                    success = await session.switch_to_tab(tab)
                    if success:
                        existing_tab = tab
                        logger.info(f"找到服务 {service_id} 对应的标签页: {tab}")
                        break
                    else:
                        # 清理无效的标签页引用
                        logger.warning(f"标签页 {tab} 切换失败，将从映射中移除")
                        if tab in self.tab_services:
                            del self.tab_services[tab]
                except Exception as e:
                    logger.warning(f"切换到标签页 {tab} 失败: {str(e)}")
                    # 清理无效的标签页引用
                    if tab in self.tab_services:
                        del self.tab_services[tab]
        
        # 如果没有现有标签页或切换失败，创建新标签页
        if not existing_tab:
            try:
                # 创建新标签页
                tab_handle = await session.create_new_tab()
                
                if not tab_handle:
                    # 如果创建失败，尝试使用当前标签页
                    tab_handle = await session.get_current_tab()
                    logger.info(f"无法创建新标签页，使用当前标签页: {tab_handle}")
                
                # 记录标签页服务映射
                if tab_handle:
                    self.tab_services[tab_handle] = service_id
                    
                    # 如果提供了URL，导航到该URL
                    if url:
                        await session.goto(url)
                    
                    return browser_service, session, tab_handle
                else:
                    logger.error("无法获取有效的标签页句柄")
                    return browser_service, session, None
            except Exception as e:
                logger.error(f"创建新标签页失败: {str(e)}")
                # 尝试使用当前标签页作为后备
                try:
                    tab_handle = await session.get_current_tab()
                    if tab_handle:
                        self.tab_services[tab_handle] = service_id
                        if url:
                            await session.goto(url)
                        return browser_service, session, tab_handle
                except Exception as backup_error:
                    logger.error(f"使用当前标签页作为后备失败: {str(backup_error)}")
                
                return browser_service, session, None
        
        # 返回现有标签页
        return browser_service, session, existing_tab


    async def get_browser_service(self, service_id: str = "default"):
        """
        获取或创建浏览器服务
        
        Args:
            service_id: 服务标识符
            
        Returns:
            浏览器服务实例
        """
        # 导入放在这里避免循环导入
        from .chromedriver_browser_service import ChromeDriverBrowserService
        
        # 如果服务已存在，直接返回
        if service_id in self.browser_services:
            return self.browser_services[service_id]
        
        # 检查是否达到最大实例数
        if len(self.browser_services) >= self.config['max_instances']:
            raise Exception(f"已达到最大浏览器实例数: {self.config['max_instances']}")
        
        # 为新服务分配端口
        debug_port = self._get_next_port()
        
        # 创建服务配置
        service_config = dict(self.config)
        service_config['debug_port'] = debug_port
        service_config['data_dir'] = str(self.data_dir / service_id)
        
        # 创建浏览器服务
        browser_service = ChromeDriverBrowserService(
            headless=self.config['headless'],
            config=service_config
        )
        
        # 存储服务
        self.browser_services[service_id] = browser_service
        
        return browser_service
    
    def _get_next_port(self) -> int:
        """
        获取下一个可用端口
        
        Returns:
            可用的端口号
        """
        # 从配置的起始端口开始查找
        start_port = self.config['debug_port_start']
        
        # 寻找未被占用的端口
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        
        raise Exception("无法找到可用端口")
    
    def download_chromedriver(self, force: bool = False) -> str:
        pass
    
    def _get_chrome_version(self) -> Optional[str]:
        """
        获取当前安装的Chrome版本
        
        Returns:
            Chrome版本号或None
        """
        system = platform.system()
        
        # 如果配置了Chrome路径，则使用该路径
        chrome_binary = self.config.get('chrome_binary')
        
        try:
            if system == "Windows":
                # 如果没有提供路径，使用默认路径
                if not chrome_binary:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                    version, _ = winreg.QueryValueEx(key, "version")
                    return version
                
                # 使用提供的路径
                from win32com.client import Dispatch
                parser = Dispatch("Scripting.FileSystemObject")
                version = parser.GetFileVersion(chrome_binary)
                return version
                
            elif system == "Darwin":
                # macOS
                if not chrome_binary:
                    chrome_binary = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                
                if not os.path.exists(chrome_binary):
                    chrome_binary = "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
                
                if not os.path.exists(chrome_binary):
                    return None
                
                # 获取版本信息
                import subprocess
                cmd = [chrome_binary, "--version"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                out, _ = proc.communicate()
                version = out.decode('utf-8').strip().split()[-1]
                return version
                
            else:
                # Linux
                if not chrome_binary:
                    for path in ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/local/bin/chrome-for-testing"]:
                        if os.path.exists(path):
                            chrome_binary = path
                            break
                
                if not chrome_binary or not os.path.exists(chrome_binary):
                    return None
                
                # 获取版本信息
                import subprocess
                cmd = [chrome_binary, "--version"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                out, _ = proc.communicate()
                version = out.decode('utf-8').strip().split()[-1]
                return version
                
        except Exception as e:
            logger.error(f"获取Chrome版本失败: {str(e)}")
            return None
    
    def list_browser_services(self):
        """列出所有运行中的浏览器服务"""
        return list(self.browser_services.keys())
    
    async def close_browser_service(self, service_id: str) -> bool:
        """
        关闭指定的浏览器服务
        
        Args:
            service_id: 服务标识符
            
        Returns:
            是否成功关闭
        """
        if service_id not in self.browser_services:
            return False
        
        try:
            service = self.browser_services[service_id]
            await service.cleanup()
            del self.browser_services[service_id]
            return True
        except Exception as e:
            logger.error(f"关闭浏览器服务 {service_id} 失败: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """清理所有资源"""
        logger.info("清理浏览器资源...")
        
        # 关闭所有浏览器服务
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        for service_id in list(self.browser_services.keys()):
            try:
                service = self.browser_services[service_id]
                loop.run_until_complete(service.cleanup())
            except Exception as e:
                logger.error(f"清理浏览器服务 {service_id} 失败: {str(e)}")
        
        self.browser_services.clear()
        
        # 终止所有子进程
        for proc in self.running_processes:
            try:
                proc.terminate()
                logger.info(f"终止进程 {proc.pid}")
            except:
                pass
        
        self.running_processes.clear()
