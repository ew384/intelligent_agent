# tool_service/src/tools/handlers/tax_handler.py
from .base import BaseHandler
from typing import Dict, Any, Optional, List
import logging
import asyncio
import time
from urllib.parse import urljoin, urlparse
import os
from datetime import datetime
import json
from browser_use.dom.service import DomService
from browser_use.utils import time_execution_sync
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig


logger = logging.getLogger(__name__)
class TaxHandler(BaseHandler):
    """电子税务局操作处理器"""
    
    def __init__(self, browser_context):
        super().__init__(browser_context)
        self.BASE_URL = "https://etax.chinatax.gov.cn/"
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 业务逻辑路由
        action_map = {
            "navigate_to_main": self.navigate_to_main,
            # 其他税务特定操作...
        }
        
        handler = action_map.get(action)
        if not handler:
            return await super().process_query(parameters)
            
        try:
            return await handler(parameters)
        finally:
            if parameters.get('close_session', False):
                await self.cleanup()
                
    async def navigate_to_main(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """导航到电子税务局主页并打开纳税清单打印页面"""
        try:
            # 获取或创建税务网站标签页
            await self.get_or_create_tab_with_url({"url": self.BASE_URL})
            
            # 查找并点击"特色应用"按钮
            await self.find_and_click_element_by_text({"text": "特色应用"})
            
            # 查询纳税清单
            target_url = "https://its.shenzhen.chinatax.gov.cn:4433/gkpt/#/taxChecklist"
            result = await self.create_mask_interceptor({"target_url": target_url,})
            await self.highlight_elements({"viewport_expansion":500})
            
            return {
                "status": "success", 
                "message": "成功打开纳税记录开具页面",
                "tab_id": result.get("tab_id"),
                "url": target_url
            }
            
        except Exception as e:
            logger.error(f"导航到电子税务局主页失败: {str(e)}")
            return {
                "status": "error",
                "message": f"导航到电子税务局主页失败: {str(e)}"
            }