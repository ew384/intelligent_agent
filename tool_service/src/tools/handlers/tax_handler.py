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
    """
    电子税务局操作处理器
    职责:
    1. 提供税务局网站的各种操作功能
    2. 处理与税务相关的查询和操作
    3. 提供访问税务系统的通用接口
    """
    
    #"电子税务局主页"
    
    def __init__(self, browser_context):
        """初始化处理器"""
        super().__init__(browser_context)
        self.browser_context = browser_context
        self.BASE_URL = "https://etax.chinatax.gov.cn/?dmnHafHu=PjsK_AlqEcjiznWby.IiK0HJJjtvv2sEb9vKivTd7NQWVM2Yw_viEDziYJMLSN7en2q62vKkn6a2iCkoB5kAReUrPM34mSb_"
    
    async def cleanup(self):
        """
        安全地清理浏览器上下文
        这个方法应该在使用完毕后被明确调用
        """
        if hasattr(self, 'browser_context') and self.browser_context:
            try:
                # 使用 asyncio.create_task 而不是直接运行
                # 这样可以在当前事件循环中安排协程执行
                await self.browser_context.close()
            except Exception as e:
                logger.error(f"清理浏览器上下文失败: {str(e)}")
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理税务操作请求"""
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 业务逻辑路由
        action_map = {
            "navigate_to_main": self.navigate_to_main,
        }
        
        # 调用具体的业务逻辑方法
        handler = action_map.get(action)
        if not handler:
            return {"status": "error", "message": f"未知的税务操作: {action}"}
        
        try:
            return await handler(parameters)
        finally:
            # 如果参数中指示关闭会话，则执行清理
            if parameters.get('close_session', False):
                await self.cleanup()
    
    async def get_or_create_tax_tab(self):
        """
        检查是否已有税务网站的标签页，如果有则切换到该页面，
        如果没有则创建新标签页并导航到税务网站
        
        Returns:
            当前页面对象
        """
        try:
            # 获取所有标签页信息
            tabs_info = await self.browser_context.get_tabs_info()
            
            # 查找是否有税务网站的标签页
            tax_tab_id = None
            for tab in tabs_info:
                if "etax.chinatax.gov.cn" in tab.url:
                    tax_tab_id = tab.page_id
                    break
            
            # 如果找到税务网站标签页，则切换到该页面
            if tax_tab_id is not None:
                logger.info(f"找到已有的税务网站标签页，ID为: {tax_tab_id}")
                await self.browser_context.switch_to_tab(tax_tab_id)
            else:
                # 如果没有找到，创建新标签页并导航
                logger.info("未找到税务网站标签页，创建新标签页...")
                await self.browser_context.create_new_tab(self.BASE_URL)
                
            # 等待页面加载完成
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 获取当前页面
            page = await self.browser_context.get_current_page()
            return page
            
        except Exception as e:
            logger.error(f"获取或创建税务标签页失败: {str(e)}")
            raise e

    async def navigate_to_main(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        导航到电子税务局主页
        
        Args:
            parameters: 操作参数
                
        Returns:
            导航结果
        """
        try:
            logger.info("导航到电子税务局主页")
            
            # 获取或创建税务网站标签页
            page = await self.get_or_create_tax_tab()
            
            # 使用DomService分析页面元素
            dom_service = DomService(page)
            
            # 获取所有可点击元素
            logger.info('获取页面所有元素')
            all_elements_state = await time_execution_sync('get_all_elements')(dom_service.get_clickable_elements)(
                highlight_elements=True, viewport_expansion=100
            )
            await asyncio.sleep(2)
            # 获取选择器映射
            selector_map = all_elements_state.selector_map
            total_elements = len(selector_map.keys())
            logger.info(f'总元素数量: {total_elements}')
             # Find the element with highlight_index 12 (特色应用)
            target_element = selector_map.get(12)
            if not target_element:
                return {"status": "error", "message": "特色应用 button (element #12) not found"}
            
            # Click the element
            result=await self.browser_context._click_element_node(target_element)
            await self.browser_context.remove_highlights()
            # Wait for page/frame to load after click
            await self.browser_context._wait_for_page_and_frames_load()
            
            await asyncio.sleep(1)
            all_elements_state = await time_execution_sync('get_all_elements')(dom_service.get_clickable_elements)(
                highlight_elements=True, viewport_expansion=100
            )
            await asyncio.sleep(1)
            selector_map = all_elements_state.selector_map
            target_element = selector_map.get(14) #纳税记录开具
            result=await self.browser_context._click_element_node(target_element)
            await self.browser_context.remove_highlights()
            await self.browser_context._wait_for_page_and_frames_load()

            tabs_info_before = await self.browser_context.get_tabs_info()
            
            # Click the element that will open a new tab
            logger.info("点击纳税记录开具按钮")
            await self.browser_context._click_element_node(target_element)
            
            # Wait a moment for the new tab to open
            await asyncio.sleep(1)
            
            # Get updated tab info
            tabs_info_after = await self.browser_context.get_tabs_info()
            
            # Find the new tab that wasn't there before
            new_tabs = [tab for tab in tabs_info_after if tab.page_id not in [t.page_id for t in tabs_info_before]]
            
            if not new_tabs:
                return {"status": "error", "message": "No new tab was opened after clicking"}
            
            # Switch to the new tab
            new_tab = new_tabs[0]
            logger.info(f"切换到新的标签页: {new_tab.title} (ID: {new_tab.page_id})")
            await self.browser_context.switch_to_tab(new_tab.page_id)
            
            # Wait for the page to load
            await self.browser_context._wait_for_page_and_frames_load()
            
            # Now analyze the new page
            new_page = await self.browser_context.get_current_page()
            new_dom_service = DomService(new_page)
            
            logger.info('分析新标签页的页面元素')
            new_page_elements = await time_execution_sync('get_all_elements')(new_dom_service.get_clickable_elements)(
                highlight_elements=True, viewport_expansion=100
            )
            
            # Get the selector map for the new page
            new_selector_map = new_page_elements.selector_map
            
            return {
                "status": "success", 
                "message": "成功打开纳税记录开具页面并分析元素",
                "new_tab_id": new_tab.page_id,
                "new_tab_title": new_tab.title,
                "elements_count": len(new_selector_map)
            }
        
            
        except Exception as e:
            logger.error(f"导航到电子税务局主页失败: {str(e)}")
            return {
                "status": "error",
                "message": f"导航到电子税务局主页失败: {str(e)}"
            }