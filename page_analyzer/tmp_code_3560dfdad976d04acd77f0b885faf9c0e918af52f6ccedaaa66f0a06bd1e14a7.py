import os
import sys
from pathlib import Path
import json
import time
import shutil
import re
import asyncio
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Fix the import path issue by adding the parent directory to sys.path
current_path = Path(__file__).parent.parent
sys.path.append(str(current_path))
print(f"Added to path: {current_path}")

# Now use an absolute import instead of relative
try:
    from tool_service.src.tools.browser.browser_session import BrowserSession
    print("Successfully imported BrowserSession")
except ImportError as e:
    print(f"Import error: {e}")
    # If the first import fails, try another possible path structure
    try:
        # Adjust this path based on the actual location of browser_session.py
        sys.path.append(str(current_path / "tool_service"))
        from src.tools.browser.browser_session import BrowserSession
        print("Successfully imported BrowserSession from alternative path")
    except ImportError as e:
        print(f"Second import attempt failed: {e}")
        # If all imports fail, you can copy the BrowserSession class here as a last resort
        # or use the code separately

async def get_tab_by_url_pattern(browser_session, url_pattern):
    """
    获取包含指定URL模式的标签页句柄
    
    Args:
        browser_session: 浏览器会话实例
        url_pattern: URL模式（如'chatgpt.com'）
        
    Returns:
        str: 匹配URL模式的第一个标签页句柄，如果没有找到则返回None
    """
    try:
        # 获取所有标签页
        handles = await browser_session.get_all_tabs()
        if not handles:
            return None
            
        # 保存当前标签页句柄，以便之后恢复
        current_handle = await browser_session.get_current_tab()
        
        # 遍历所有标签页查找匹配的URL
        matching_handle = None
        
        for handle in handles:
            # 切换到标签页
            await browser_session.switch_to_tab(handle)
            
            # 获取当前URL
            current_url = browser_session.driver.current_url
            
            # 检查URL是否包含指定模式
            if url_pattern in current_url:
                matching_handle = handle
                break
        
        # 恢复到原来的标签页
        if current_handle:
            await browser_session.switch_to_tab(current_handle)
            
        return matching_handle
    except Exception as e:
        print(f"获取匹配URL标签页失败: {str(e)}")
        return None

def main(url_pattern="chatgpt.com"):
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:54805")
    service = Service("/home/endian/.local/share/undetected_chromedriver/undetected_chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 创建BrowserService模拟对象
    class SimpleBrowserService:
        def __init__(self):
            self.screenshots_dir = None
            self.cookies_manager = None
    
    browser_service = SimpleBrowserService()
    browser_session = BrowserSession(driver, service, browser_service)
    
    # 异步查找并切换标签页
    async def find_and_switch():
        print(f"正在查找包含 {url_pattern} 的标签页...")
        handle = await get_tab_by_url_pattern(browser_session, url_pattern)
        
        if handle:
            print(f"找到包含 {url_pattern} 的标签页: {handle}")
            # 切换到该标签页
            await browser_session.switch_to_tab(handle)
            return handle
        else:
            print(f"未找到包含 {url_pattern} 的标签页")
            return None
    
    # 运行异步函数
    loop = asyncio.get_event_loop()
    target_handle = loop.run_until_complete(find_and_switch())
    
    # 打印当前所有标签页信息（用于调试）
    all_handles = loop.run_until_complete(browser_session.get_all_tabs())
    print(f"当前所有标签页: {all_handles}")
    
    return target_handle

if __name__ == "__main__":
    # 您可以从命令行传递URL模式，或使用默认值
    if len(sys.argv) > 1:
        url_pattern = sys.argv[1]
    else:
        url_pattern = "chatgpt.com"
    
    handle = main(url_pattern)
    print(f"目标标签页句柄: {handle}")