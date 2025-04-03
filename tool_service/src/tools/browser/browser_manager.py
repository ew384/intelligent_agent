# tool_service/src/tools/browser/browser_manager.py
import os
import logging
import atexit
import tempfile
import shutil
import json
import uuid
import os
from typing import Dict, Any, Optional, List, Union
import sys
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import zipfile
import socket
import asyncio
TAB_STATE_FILE = "tabs_state.json"
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

    def save_tab_state(self, tab_id: str, url: str, handle: str, service_id: str, 
                    tab_type: str = "general", provider: str = None, user_id: str = None):
        """Save tab to shared state file"""
        try:
            # Load existing state
            state = {}
            if os.path.exists("tabs_state.json"):
                with open("tabs_state.json", "r") as f:
                    state = json.load(f)
            
            if "tabs" not in state:
                state["tabs"] = {}
            
            # Add/update tab
            state["tabs"][tab_id] = {
                "url": url,
                "handle": handle,
                "type": tab_type,
                "provider": provider,
                "service_id": service_id,
                "user_id": user_id
            }
            
            # Save state
            with open("tabs_state.json", "w") as f:
                json.dump(state, f)
            
            logger.info(f"Tab {tab_id} saved to state")
            return True
        except Exception as e:
            logger.error(f"Failed to save tab state: {str(e)}")
            return False

    def load_tab_state(self) -> Dict[str, Any]:
        """Load tab state from file"""
        try:
            if not os.path.exists("tabs_state.json"):
                return {}
            
            with open("tabs_state.json", "r") as f:
                state = json.load(f)
            
            return state.get("tabs", {})
        except Exception as e:
            logger.error(f"Failed to load tab state: {str(e)}")
            return {}

    def get_tab_handle_by_id(self, tab_id: str) -> Optional[str]:
        """Get tab handle from tab ID"""
        tabs_state = self.load_tab_state()
        if tab_id in tabs_state:
            return tabs_state[tab_id]["handle"]
        return None

    async def switch_to_tab_by_id(self, session, tab_id: str) -> bool:
        """Switch to tab by ID using existing session.switch_to_tab"""
        handle = self.get_tab_handle_by_id(tab_id)
        if handle:
            return await session.switch_to_tab(handle)
        return False

    def find_tab_id_by_handle(self, handle: str) -> Optional[str]:
        """Find tab ID by handle"""
        tabs_state = self.load_tab_state()
        for tab_id, info in tabs_state.items():
            if info["handle"] == handle:
                return tab_id
        return None

    async def get_or_create_service_tab(self, service_id: str, url: str = None):
        """
        获取或创建浏览器标签页。
        优先检查URL匹配，然后使用专用标签页，避免使用LLM服务占用的标签页。
        
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
        
        # 步骤1: 首先，检查是否有标记为当前service_id的标签页
        existing_tab = None
        for tab, tab_service in self.tab_services.items():
            if tab_service == service_id:
                try:
                    if tab in all_tabs:
                        success = await session.switch_to_tab(tab)
                        if success:
                            existing_tab = tab
                            logger.info(f"找到服务 {service_id} 对应的标签页: {tab}")
                            break
                        else:
                            logger.warning(f"标签页 {tab} 切换失败，将从映射中移除")
                            del self.tab_services[tab]
                    else:
                        logger.warning(f"标签页 {tab} 不存在，从映射中移除")
                        del self.tab_services[tab]
                except Exception as e:
                    logger.warning(f"切换到标签页 {tab} 失败: {str(e)}")
                    if tab in self.tab_services:
                        del self.tab_services[tab]
        
        # 如果找到现有标签页并且需要导航
        if existing_tab and url:
            try:
                await session.goto(url)
                return browser_service, session, existing_tab
            except Exception as e:
                logger.error(f"导航到 {url} 失败: {str(e)}")
        elif existing_tab:
            # 找到标签页且不需要导航
            return browser_service, session, existing_tab
        
        # 步骤2: 检测哪些标签页是LLM服务在使用的
        llm_tabs = set()
        llm_domains = ["claude.ai", "chatgpt.com", "chat.qwen.ai", "chat.deepseek.com"]
        
        for tab in all_tabs:
            try:
                success = await session.switch_to_tab(tab)
                if not success:
                    continue
                    
                current_url = await session.execute_script("return window.location.href")
                logger.info(f"检查标签页 {tab} 的URL: {current_url}")
                
                # 检查是否是LLM域名
                is_llm_tab = False
                for llm_domain in llm_domains:
                    if llm_domain in current_url:
                        llm_tabs.add(tab)
                        is_llm_tab = True
                        logger.info(f"标签页 {tab} 是LLM服务标签页 (URL: {current_url})")
                        break
                        
                # 同时检查标题，某些LLM可能有特定标题
                if not is_llm_tab:
                    title = await session.execute_script("return document.title")
                    llm_titles = ["Claude", "ChatGPT", "Qwen", "DeepSeek Chat"]
                    for llm_title in llm_titles:
                        if llm_title in title:
                            llm_tabs.add(tab)
                            logger.info(f"标签页 {tab} 是LLM服务标签页 (标题: {title})")
                            break
            except Exception as e:
                logger.warning(f"检查标签页 {tab} 时出错: {str(e)}")
        
        # 步骤3: 如果有URL参数，查找是否有已打开该URL的非LLM标签页
        url_matched_tab = None
        if url:
            from urllib.parse import urlparse
            target_domain = urlparse(url).netloc
            
            for tab in all_tabs:
                # 跳过LLM标签页
                if tab in llm_tabs:
                    continue
                    
                try:
                    success = await session.switch_to_tab(tab)
                    if not success:
                        continue
                    
                    current_url = await session.execute_script("return window.location.href")
                    current_domain = urlparse(current_url).netloc
                    
                    # 检查是否匹配目标URL
                    if (current_domain and target_domain in current_domain) or (current_url and url in current_url):
                        url_matched_tab = tab
                        logger.info(f"找到匹配URL的非LLM标签页: {tab}, URL: {current_url}")
                        break
                except Exception as e:
                    logger.warning(f"检查标签页 {tab} 的URL失败: {str(e)}")
        
        # 如果找到匹配URL的非LLM标签页
        if url_matched_tab:
            # 标记此标签页
            self.tab_services[url_matched_tab] = service_id
            return browser_service, session, url_matched_tab
        
        # 步骤4: 寻找一个非LLM的、未被标记的标签页
        unused_tab = None
        for tab in all_tabs:
            # 跳过LLM标签页和已标记的标签页
            if tab in llm_tabs or tab in self.tab_services:
                continue
                
            try:
                success = await session.switch_to_tab(tab)
                if success:
                    unused_tab = tab
                    logger.info(f"找到非LLM的未使用标签页: {tab}")
                    break
            except Exception as e:
                logger.warning(f"切换到标签页 {tab} 失败: {str(e)}")
        
        # 如果找到非LLM未使用的标签页
        if unused_tab:
            # 标记此标签页
            self.tab_services[unused_tab] = service_id
            
            # 如果需要导航
            if url:
                try:
                    await session.goto(url)
                except Exception as e:
                    logger.error(f"导航到 {url} 失败: {str(e)}")
                    # 错误处理：移除标记并继续尝试创建新标签页
                    del self.tab_services[unused_tab]
                    unused_tab = None
            
            if unused_tab:
                return browser_service, session, unused_tab
        
        # 步骤5: 如果以上方法都失败，创建新标签页
        logger.info(f"未找到合适的非LLM标签页，创建新标签页")
        try:
            # 创建新标签页 - 使用更可靠的方法
            session.driver.switch_to.new_window('tab')
            await asyncio.sleep(1)
            
            # 获取所有标签页
            new_handles = await session.get_all_tabs()
            
            # 找出新创建的标签页
            new_tabs = [h for h in new_handles if h not in all_tabs]
            
            if new_tabs:
                tab_handle = new_tabs[0]
                logger.info(f"成功创建新标签页: {tab_handle}")
            else:
                # 如果无法确定新标签页，获取当前标签页
                tab_handle = await session.get_current_tab()
                
                # 确保不是LLM标签页
                if tab_handle in llm_tabs:
                    logger.error("当前标签页是LLM标签页，无法重用")
                    # 再次尝试创建标签页
                    session.driver.switch_to.new_window('tab')
                    await asyncio.sleep(1)
                    tab_handle = await session.get_current_tab()
                    if tab_handle in llm_tabs:
                        logger.error("无法创建非LLM标签页")
                        return browser_service, session, None
                
                logger.info(f"使用当前标签页作为新标签页: {tab_handle}")
            
            # 确保切换到新标签页
            await session.switch_to_tab(tab_handle)
            
            # 标记此标签页
            self.tab_services[tab_handle] = service_id
            
            # 如果提供了URL，导航到该URL
            if url:
                success = await session.goto(url)
                if not success:
                    logger.error(f"导航到 {url} 失败")
                    # 错误处理：移除标记
                    del self.tab_services[tab_handle]
                    return browser_service, session, None
            
            return browser_service, session, tab_handle
        except Exception as e:
            logger.error(f"创建新标签页失败: {str(e)}")
            return browser_service, session, None

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

    def save_tab_state(self, tab_id, url, handle, service_id, tab_type="general", provider=None, user_id=None):
        """Save tab state to shared state file"""
        try:
            # Load existing state
            state = {}
            if os.path.exists("tabs_state.json"):
                with open("tabs_state.json", "r") as f:
                    state = json.load(f)
            
            # Initialize tabs dict if not exists
            if "tabs" not in state:
                state["tabs"] = {}
            
            # Update tab info
            state["tabs"][tab_id] = {
                "url": url,
                "handle": handle,
                "type": tab_type,
                "provider": provider,
                "service_id": service_id,
                "user_id": user_id
            }
            
            # Save state
            with open("tabs_state.json", "w") as f:
                json.dump(state, f)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save tab state: {str(e)}")
            return False
            
    def load_tab_state(self):
        """Load tab state from shared state file"""
        try:
            if not os.path.exists("tabs_state.json"):
                return {}
            
            with open("tabs_state.json", "r") as f:
                state = json.load(f)
            
            return state.get("tabs", {})
        except Exception as e:
            logger.error(f"Failed to load tab state: {str(e)}")
            return {}

    def _get_next_port(self) -> int:
        """
        获取下一个可用端口
        
        Returns:
            可用的端口号
        """
        pass
    
    def download_chromedriver(self, force: bool = False) -> str:
        pass
    
    def _get_chrome_version(self) -> Optional[str]:
        """
        获取当前安装的Chrome版本
        
        Returns:
            Chrome版本号或None
        """
        pass
    
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
        pass
    
    def cleanup(self) -> None:
        """清理所有资源"""
        pass
