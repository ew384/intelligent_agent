# 在 tool_service/src/tools/common/cookies_manager.py 中整合
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class CookiesManager:
    """Manages browser cookies for different domains"""
    
    def __init__(self, data_dir: Path):
        """
        Initialize cookies manager
        
        Args:
            data_dir: Directory to store cookie files
        """
        self.data_dir = data_dir / 'cookies'
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)
        
    def get_cookies_path(self, domain: str) -> Path:
        """
        Get the file path for cookies of a specific domain
        
        Args:
            domain: Domain for the cookies
            
        Returns:
            Path to the cookie file
        """
        # Convert domain to a safe filename
        safe_name = domain.replace(".", "_").replace("/", "_").replace(":", "_")
        return self.data_dir / f"{safe_name}_cookies.json"
        
    def load_cookies(self, browser_context, domain: str) -> bool:
        """
        Load cookies for a domain and add them to the browser context
        
        Args:
            browser_context: The browser context to add cookies to
            domain: Domain to load cookies for
            
        Returns:
            Boolean indicating success
        """
        cookies_path = self.get_cookies_path(domain)
        
        try:
            if os.path.exists(cookies_path):
                with open(cookies_path, 'r') as f:
                    cookies = json.load(f)
                    
                # Check if cookies have expired
                current_time = datetime.now().timestamp()
                valid_cookies = [
                    cookie for cookie in cookies
                    if not cookie.get('expires') or cookie.get('expires', 0) > current_time
                ]
                
                if len(valid_cookies) < len(cookies):
                    logger.info(f"Removed {len(cookies) - len(valid_cookies)} expired cookies for {domain}")
                
                if valid_cookies:
                    browser_context.add_cookies(valid_cookies)
                    logger.info(f"加载了 {len(valid_cookies)} 个 cookies 用于 {domain}")
                    return True
                else:
                    logger.info(f"没有有效的 cookies 用于 {domain}")
                    return False
            else:
                logger.info(f"没有找到保存的 cookies: {cookies_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to load cookies for {domain}: {str(e)}")
            return False
            
    async def save_cookies(self, browser_context, domain: str) -> bool:
        """
        Save cookies from browser context for a domain
        
        Args:
            browser_context: The browser context to get cookies from
            domain: Domain the cookies belong to
            
        Returns:
            Boolean indicating success
        """
        cookies_path = self.get_cookies_path(domain)
        
        try:
            cookies = await browser_context.cookies()
            if not cookies:
                logger.warning(f"No cookies found to save for {domain}")
                return False
                
            with open(cookies_path, 'w') as f:
                json.dump(cookies, f, indent=2)
                
            logger.info(f"保存了 {len(cookies)} 个 cookies 到 {cookies_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies for {domain}: {str(e)}")
            return False
            
    def clear_cookies(self, domain: Optional[str] = None) -> bool:
        """
        Clear cookies for a domain or all domains
        
        Args:
            domain: Domain to clear cookies for, or None for all domains
            
        Returns:
            Boolean indicating success
        """
        try:
            if domain:
                cookie_path = self.get_cookies_path(domain)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
                    logger.info(f"已删除 {domain} 的 cookies")
            else:
                # Clear all cookie files
                for filename in os.listdir(self.data_dir):
                    if filename.endswith("_cookies.json"):
                        os.remove(os.path.join(self.data_dir, filename))
                logger.info("已删除所有 cookies")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cookies: {str(e)}")
            return False
