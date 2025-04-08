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
    
    def __init__(self, browser_context):
        """初始化处理器"""
        super().__init__(browser_context)
        self.browser_context = browser_context
        self.BASE_URL = "https://etax.chinatax.gov.cn/"

    
    async def cleanup(self):
        """
        安全地清理浏览器上下文
        这个方法应该在使用完毕后被明确调用
        """
        if hasattr(self, 'browser_context') and self.browser_context:
            try:
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
            # 其他操作可在此添加
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


    async def highlight_and_get_elements(self, page=None, viewport_expansion=100):
        """
        高亮并获取页面上的可点击元素
        
        Args:
            page: 页面对象，如未提供则获取当前页面
            viewport_expansion: 视口扩展范围
            
        Returns:
            元素选择器映射和DOM服务对象
        """
        if page is None:
            page = await self.browser_context.get_current_page()
            
        # 检查页面兼容模式
        compat_mode = await page.evaluate("document.compatMode")
        logger.info(f"获取元素前检查兼容模式: {compat_mode}")
        
        # 创建DOM服务并高亮元素
        dom_service = DomService(page)
        logger.info('获取页面所有元素')
        all_elements_state = await time_execution_sync('get_all_elements')(dom_service.get_clickable_elements)(
            highlight_elements=True, viewport_expansion=viewport_expansion
        )
        
        # 等待高亮元素显示
        await asyncio.sleep(1)
        
        return all_elements_state.selector_map, dom_service, all_elements_state.element_tree

    def find_element_by_text(self, selector_map, text, partial_match=True):
        """
        通过文本内容查找元素
        
        Args:
            selector_map: 元素选择器映射
            text: 要查找的文本
            partial_match: 是否允许部分匹配
            
        Returns:
            匹配的元素或None
        """
        for index, element in selector_map.items():
            # 获取元素的所有文本内容
            element_text = element.get_all_text_till_next_clickable_element()
            
            # 检查元素属性中是否包含该文本
            attributes_text = ""
            for attr_name, attr_value in element.attributes.items():
                if attr_value and isinstance(attr_value, str):
                    attributes_text += attr_value + " "
            
            # 合并文本内容和属性文本
            all_text = (element_text + " " + attributes_text).strip()
            
            # 进行文本匹配
            if partial_match:
                if text.lower() in all_text.lower():
                    logger.info(f"找到匹配文本'{text}'的元素，ID为: {index}")
                    return element
            else:
                if text.lower() == all_text.lower():
                    logger.info(f"找到完全匹配文本'{text}'的元素，ID为: {index}")
                    return element
        
        logger.warning(f"未找到包含文本'{text}'的元素")
        return None


    async def navigate_to_main(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        导航到电子税务局主页，然后直接打开纳税清单打印页面
        
        Args:
            parameters: 操作参数
                    
        Returns:
            导航结果
        """
        try:
            logger.info("导航到电子税务局主页")
            
            # 获取或创建税务网站标签页
            page = await self.get_or_create_tax_tab()
            
            # 步骤1: 高亮并获取主页元素
            selector_map, _, _ = await self.highlight_and_get_elements(page)
            
            # 步骤2: 通过文本查找并点击"特色应用"按钮
            target_element = self.find_element_by_text(selector_map, "特色应用")
            if not target_element:
                # 如果找不到精确匹配，尝试部分匹配
                target_element = self.find_element_by_text(selector_map, "特色")
                
            if not target_element:
                return {"status": "error", "message": "未找到特色应用按钮"}
            
            # 使用原始的点击方法点击"特色应用"
            await self.browser_context._click_element_node(target_element)
            await self.browser_context.remove_highlights()
            await self.browser_context._wait_for_page_and_frames_load()
            selector_map, _, _ = await self.highlight_and_get_elements()
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 步骤3: 不再尝试点击"纳税清单打印"按钮，而是直接创建新标签页并导航到目标URL
            logger.info("直接创建新标签页并导航到纳税清单打印页面")
            target_url = "https://its.shenzhen.chinatax.gov.cn:4433/gkpt/#/taxChecklist"
            
            # 保存当前标签页信息
            tabs_info_before = await self.browser_context.get_tabs_info()
            
            # 创建新标签页
            await self.browser_context.create_new_tab("about:blank")  # 先创建空白页
            
            # 获取新标签页信息
            await asyncio.sleep(1)
            tabs_after = await self.browser_context.get_tabs_info()
            new_tabs = [tab for tab in tabs_after if tab.page_id not in [t.page_id for t in tabs_info_before]]
            
            if not new_tabs:
                return {"status": "error", "message": "无法打开新标签页"}
            
            # 切换到新标签页
            new_tab = new_tabs[0]
            logger.info(f"切换到新标签页: {new_tab.title} (ID: {new_tab.page_id})")
            await self.browser_context.switch_to_tab(new_tab.page_id)
            
            # 获取当前页面
            new_page = await self.browser_context.get_current_page()
            
            # 设置页面路由拦截器，注入自动应用遮罩的脚本
            await new_page.route("**/*", self._add_mask_to_response)
            
            # 现在导航到目标URL
            logger.info("在预设遮罩后导航到目标URL")
            await new_page.goto(target_url)
            
            # 等待页面加载
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 获取新页面上的元素
            new_selector_map, _, _ = await self.highlight_and_get_elements(new_page)
            
            return {
                "status": "success", 
                "message": "成功打开纳税记录开具页面并分析元素",
                "new_tab_id": new_tab.page_id,
                "new_tab_title": new_tab.title,
                "elements_count": len(new_selector_map),
                "url": target_url
            }
            
        except Exception as e:
            logger.error(f"导航到电子税务局主页失败: {str(e)}")
            return {
                "status": "error",
                "message": f"导航到电子税务局主页失败: {str(e)}"
            }

    async def _add_mask_to_response(self, route, request):
        """
        拦截响应并注入遮罩脚本
        """
        # 继续正常的请求
        response = await route.fetch()
        
        # 只处理HTML响应
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            try:
                # 获取响应体
                body = await response.text()
                
                # 注入遮罩脚本到页面头部
                mask_script = """
                <script>
                document.addEventListener('DOMContentLoaded', function() {
                    // 创建遮罩层
                    const overlay = document.createElement('div');
                    
                    // 设置样式
                    overlay.id = 'data-mask-overlay';
                    overlay.style.position = 'fixed';
                    overlay.style.left = '0';
                    overlay.style.width = '100%';
                    overlay.style.height = '66.7%';  // 页面下三分之二
                    overlay.style.bottom = '0';  // 从底部开始
                    overlay.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';  // 半透明白色
                    overlay.style.backdropFilter = 'blur(4px)';  // 添加模糊效果
                    overlay.style.zIndex = '9999';  // 确保在最上层
                    overlay.style.pointerEvents = 'none';  // 允许点击穿透
                    
                    // 添加到页面
                    document.body.appendChild(overlay);
                    
                    console.log("响应拦截器已添加遮罩层");
                }, { once: true });
                </script>
                """
                
                # 寻找合适的位置注入脚本
                if "<head>" in body:
                    modified_body = body.replace("<head>", "<head>" + mask_script)
                elif "<html>" in body:
                    modified_body = body.replace("<html>", "<html>" + mask_script)
                else:
                    modified_body = mask_script + body
                
                # 使用修改后的响应体继续
                await route.fulfill(
                    status=response.status,
                    headers=response.headers,
                    body=modified_body
                )
                logger.info("成功拦截响应并注入遮罩脚本")
                return
            except Exception as e:
                logger.error(f"拦截响应失败: {str(e)}")
        
        # 对于非HTML内容或出错情况，使用原始响应继续
        await route.continue_()
