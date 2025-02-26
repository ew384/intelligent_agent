# tool_service/src/tools/browser/browser_manager.py
import os
import logging
import subprocess
import atexit
import tempfile
import shutil
import sys
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from .chromedriver_browser_service import ChromeDriverBrowserService

logger = logging.getLogger(__name__)

class BrowserManager:
    """浏览器管理类，负责浏览器服务的创建和管理"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化浏览器管理器
        
        Args:
            config: 配置选项
        """
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
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 注册退出时的清理函数
        atexit.register(self.cleanup)
        
        self._initialized = True
    
    async def get_browser_service(self, service_id: str = "default") -> ChromeDriverBrowserService:
        """
        获取或创建浏览器服务
        
        Args:
            service_id: 服务标识符
            
        Returns:
            浏览器服务实例
        """
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
        import socket
        
        # 从配置的起始端口开始查找
        start_port = self.config['debug_port_start']
        
        # 寻找未被占用的端口
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        
        raise Exception("无法找到可用端口")
    
    def download_chromedriver(self, force: bool = False) -> str:
        """
        下载与当前Chrome版本匹配的ChromeDriver
        
        Args:
            force: 是否强制下载，即使已存在
            
        Returns:
            ChromeDriver路径
        """
        try:
            # 确定Chrome版本
            chrome_version = self._get_chrome_version()
            if not chrome_version:
                raise Exception("无法确定Chrome版本")
            
            # 确定主版本，用于下载正确的驱动
            major_version = chrome_version.split('.')[0]
            
            # 确定下载目标路径
            driver_dir = self.data_dir / "chromedriver"
            driver_dir.mkdir(parents=True, exist_ok=True)
            
            # 确定平台相关的可执行文件名
            system = platform.system()
            if system == "Windows":
                driver_filename = "chromedriver.exe"
            else:
                driver_filename = "chromedriver"
            
            driver_path = driver_dir / driver_filename
            
            # 如果已经存在并且不是强制下载，则直接返回
            if not force and driver_path.exists():
                return str(driver_path)
            
            # 下载URL基础
            base_url = f"https://chromedriver.storage.googleapis.com"
            
            # 找到与Chrome版本匹配的ChromeDriver版本
            version_url = f"{base_url}/LATEST_RELEASE_{major_version}"
            
            import urllib.request
            try:
                with urllib.request.urlopen(version_url) as response:
                    driver_version = response.read().decode('utf-8').strip()
            except Exception as e:
                logger.error(f"获取ChromeDriver版本失败: {str(e)}")
                raise
            
            # 确定平台
            if system == "Windows":
                platform_name = "win32"
            elif system == "Darwin":
                if platform.machine() == "arm64":
                    platform_name = "mac_arm64"
                else:
                    platform_name = "mac64"
            else:
                platform_name = "linux64"
            
            # 下载URL
            download_url = f"{base_url}/{driver_version}/chromedriver_{platform_name}.zip"
            
            # 下载压缩文件
            import urllib.request
            import zipfile
            
            try:
                # 创建临时目录
                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, "chromedriver.zip")
                
                # 下载文件
                logger.info(f"正在下载ChromeDriver {driver_version}...")
                urllib.request.urlretrieve(download_url, zip_path)
                
                # 解压文件
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # 移动到目标位置
                extracted_driver = os.path.join(temp_dir, driver_filename)
                shutil.copy(extracted_driver, str(driver_path))
                
                # 设置可执行权限
                os.chmod(str(driver_path), 0o755)
                
                logger.info(f"ChromeDriver {driver_version} 已下载到 {driver_path}")
                
                # 清理临时目录
                shutil.rmtree(temp_dir)
                
                return str(driver_path)
                
            except Exception as e:
                logger.error(f"下载ChromeDriver失败: {str(e)}")
                raise
        
        except Exception as e:
            logger.error(f"下载ChromeDriver过程中出错: {str(e)}")
            raise
    
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
                cmd = [chrome_binary, "--version"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                out, _ = proc.communicate()
                version = out.decode('utf-8').strip().split()[-1]
                return version
                
            else:
                # Linux
                if not chrome_binary:
                    for path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"]:
                        if os.path.exists(path):
                            chrome_binary = path
                            break
                
                if not chrome_binary or not os.path.exists(chrome_binary):
                    return None
                
                # 获取版本信息
                cmd = [chrome_binary, "--version"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                out, _ = proc.communicate()
                version = out.decode('utf-8').strip().split()[-1]
                return version
                
        except Exception as e:
            logger.error(f"获取Chrome版本失败: {str(e)}")
            return None
    
    def list_browser_services(self) -> List[str]:
        """
        列出所有运行中的浏览器服务
        
        Returns:
            服务ID列表
        """
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
        import asyncio
        
        # 获取或创建事件循环
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