# tool_service/src/tools/common/cookies_manager.py
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class CookiesManager:
    """管理浏览器cookies的类"""
    
    def __init__(self, data_dir: Path):
        """
        初始化cookies管理器
        
        Args:
            data_dir: 存储cookie文件的目录
        """
        self.data_dir = data_dir / 'cookies'
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        
    def get_cookies_path(self, domain: str) -> Path:
        """
        获取特定域的cookie文件路径
        
        Args:
            domain: cookie的域名
            
        Returns:
            cookie文件的路径
        """
        # 将域名转换为安全的文件名
        safe_name = domain.replace(".", "_").replace("/", "_").replace(":", "_")
        return self.data_dir / f"{safe_name}_cookies.json"
        
    def load_cookies(self, domain: str) -> List[Dict[str, Any]]:
        """
        加载域的cookie
        
        Args:
            domain: 加载cookie的域名
            
        Returns:
            cookie字典列表
        """
        cookies_path = self.get_cookies_path(domain)
        
        try:
            if os.path.exists(cookies_path):
                with open(cookies_path, 'r') as f:
                    cookies = json.load(f)
                    
                # 检查cookie是否已过期
                current_time = datetime.now().timestamp()
                valid_cookies = [
                    cookie for cookie in cookies
                    if not cookie.get('expires') or cookie.get('expires', 0) > current_time
                ]
                
                if len(valid_cookies) < len(cookies):
                    logger.info(f"移除了 {len(cookies) - len(valid_cookies)} 个已过期的 {domain} cookie")
                
                if valid_cookies:
                    logger.info(f"加载了 {len(valid_cookies)} 个 {domain} cookie")
                    return valid_cookies
                else:
                    logger.info(f"{domain} 没有有效的cookie")
                    return []
            else:
                logger.info(f"没有找到保存的cookie: {cookies_path}")
                return []
        except Exception as e:
            logger.error(f"加载 {domain} cookie失败: {str(e)}")
            return []
    
    def save_cookies_data(self, domain: str, cookies: List[Dict[str, Any]]) -> bool:
        """
        保存cookies数据到文件
        
        Args:
            domain: cookies所属的域名
            cookies: cookies数据列表
            
        Returns:
            是否成功保存
        """
        cookies_path = self.get_cookies_path(domain)
        
        try:
            if not cookies:
                logger.warning(f"没有要保存的cookies")
                return False
                
            with open(cookies_path, 'w') as f:
                json.dump(cookies, f, indent=2)
                
            logger.info(f"已保存 {len(cookies)} 个cookies到 {cookies_path}")
            return True
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            return False
    
    def add_cookies_to_driver(self, driver, domain: str) -> bool:
        """
        将cookies添加到Selenium WebDriver
        
        Args:
            driver: Selenium WebDriver实例
            domain: 域名
            
        Returns:
            是否成功添加
        """
        try:
            cookies = self.load_cookies(domain)
            if not cookies:
                return False
            
            # 确保我们在正确的域上设置cookie
            current_url = driver.current_url
            domain_url = f"https://{domain}" if not domain.startswith(("http://", "https://")) else domain
            
            # 如果我们不在正确的域上，先导航到该域
            if domain not in current_url:
                driver.get(domain_url)
            
            # 添加每个cookie
            for cookie in cookies:
                # Selenium需要的格式与存储格式可能有所不同
                cookie_dict = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'path': cookie.get('path', '/'),
                    'domain': cookie.get('domain'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                
                # 移除无效键
                cookie_dict = {k: v for k, v in cookie_dict.items() if v is not None}
                
                try:
                    driver.add_cookie(cookie_dict)
                except Exception as cookie_error:
                    logger.warning(f"添加单个cookie失败: {str(cookie_error)}")
            
            logger.info(f"已向WebDriver添加 {len(cookies)} 个cookie")
            return True
        except Exception as e:
            logger.error(f"向WebDriver添加cookie失败: {str(e)}")
            return False
    
    def save_cookies(self, driver, domain: str) -> bool:
        """
        从WebDriver保存cookie
        
        Args:
            driver: Selenium WebDriver实例
            domain: cookie所属的域名
            
        Returns:
            是否成功保存
        """
        cookies_path = self.get_cookies_path(domain)
        
        try:
            cookies = driver.get_cookies()
            if not cookies:
                logger.warning(f"没有找到要保存的 {domain} cookie")
                return False
                
            with open(cookies_path, 'w') as f:
                json.dump(cookies, f, indent=2)
                
            logger.info(f"已保存 {len(cookies)} 个 {domain} cookie到 {cookies_path}")
            return True
        except Exception as e:
            logger.error(f"保存 {domain} cookie失败: {str(e)}")
            return False
    
    def clear_cookies(self, domain: Optional[str] = None) -> bool:
        """
        清除域名的cookie或所有cookie
        
        Args:
            domain: 要清除cookie的域名，None表示所有域名
            
        Returns:
            是否成功清除
        """
        try:
            if domain:
                cookie_path = self.get_cookies_path(domain)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
                    logger.info(f"已删除 {domain} 的cookie")
            else:
                # 清除所有cookie文件
                for filename in os.listdir(self.data_dir):
                    if filename.endswith("_cookies.json"):
                        os.remove(os.path.join(self.data_dir, filename))
                logger.info("已删除所有cookie")
            return True
        except Exception as e:
            logger.error(f"清除cookie失败: {str(e)}")
            return False
    
    def get_domain_from_url(self, url: str) -> str:
        """
        从URL提取域名
        
        Args:
            url: 完整URL
            
        Returns:
            域名部分
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # 移除端口号如果存在
            if ":" in domain:
                domain = domain.split(":")[0]
            return domain
        except Exception as e:
            logger.error(f"从URL提取域名失败: {str(e)}")
            return ""
