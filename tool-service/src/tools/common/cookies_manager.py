# tool-service/src/tools/common/cookies_manager.py
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CookiesManager:
    """Manages browser cookies for different domains"""
    
    def __init__(self, data_dir: str):
        """
        Initialize cookies manager
        
        Args:
            data_dir: Directory to store cookie files
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)
        
    def _get_cookie_path(self, domain: str) -> str:
        """
        Get the file path for cookies of a specific domain
        
        Args:
            domain: Domain for the cookies
            
        Returns:
            Path to the cookie file
        """
        # Convert domain to a safe filename
        safe_name = domain.replace(".", "_").replace("/", "_").replace(":", "_")
        return os.path.join(self.data_dir, f"{safe_name}_cookies.json")
        
    def load_cookies(self, domain: str) -> List[Dict[str, Any]]:
        """
        Load cookies for a domain
        
        Args:
            domain: Domain to load cookies for
            
        Returns:
            List of cookie objects or empty list if none found
        """
        cookie_path = self._get_cookie_path(domain)
        
        try:
            if os.path.exists(cookie_path):
                with open(cookie_path, 'r') as f:
                    cookies = json.load(f)
                    
                # Check if cookies have expired
                current_time = datetime.now().timestamp()
                valid_cookies = [
                    cookie for cookie in cookies
                    if not cookie.get('expires') or cookie.get('expires', 0) > current_time
                ]
                
                if len(valid_cookies) < len(cookies):
                    logger.info(f"Removed {len(cookies) - len(valid_cookies)} expired cookies for {domain}")
                
                return valid_cookies
        except Exception as e:
            logger.error(f"Failed to load cookies for {domain}: {str(e)}")
            
        return []
        
    def save_cookies(self, domain: str, cookies: List[Dict[str, Any]]) -> bool:
        """
        Save cookies for a domain
        
        Args:
            domain: Domain the cookies belong to
            cookies: List of cookie objects to save
            
        Returns:
            Boolean indicating success
        """
        cookie_path = self._get_cookie_path(domain)
        
        try:
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f, indent=2)
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
                cookie_path = self._get_cookie_path(domain)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            else:
                # Clear all cookie files
                for filename in os.listdir(self.data_dir):
                    if filename.endswith("_cookies.json"):
                        os.remove(os.path.join(self.data_dir, filename))
            return True
        except Exception as e:
            logger.error(f"Failed to clear cookies: {str(e)}")
            return False