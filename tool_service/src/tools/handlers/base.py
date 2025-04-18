# tool_service/src/tools/handlers/base.py
from typing import Dict, Any, List, Optional, Tuple, Union
import logging
import asyncio
import json
from browser_use.dom.service import DomService
from browser_use.dom.views import DOMElementNode, SelectorMap
from browser_use.utils import time_execution_sync
from ..utils.script_templates import ScriptTemplates
logger = logging.getLogger(__name__)

class BaseHandler:
    """
    通用的浏览器操作处理器
    提供一系列基础与高级工具，用于构建特定场景的处理器
    """
    
    def __init__(self, browser_context):
        """初始化处理器"""
        self.browser_context = browser_context
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用请求"""
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 基础操作映射
        action_map = {
            # 基础操作
            "go_to_url": self.go_to_url,
            "click_element": self.click_element,
            "input_text": self.input_text,
            "extract_content": self.extract_content,
            "scroll": self.scroll,
            "wait": self.wait,
            
            # 标签页操作
            "get_tabs": self.get_tabs,
            "create_tab": self.create_tab,
            "switch_tab": self.switch_tab,
            "close_tab": self.close_tab,
            
            # 元素查找与操作
            "highlight_elements": self.highlight_elements,
            "find_element_by_text": self.find_element_by_text,
            "find_element_by_attribute": self.find_element_by_attribute,
            
            # 高级操作
            "inject_script": self.inject_script,
            "input_by_selector": self.input_by_selector,
            
            # 组合工具
            "get_or_create_tab": self.get_or_create_tab_with_url,
            "input_text_and_search":self.input_text_and_search,
            "find_and_click": self.find_and_click_element_by_text,
            "create_mask_interceptor": self.create_mask_interceptor,
            "search_and_navigate":self.search_and_navigate,

            # 用户交互操作
            "request_user_action":self.request_user_action,
            "evaluate_state":self.evaluate_state,
            
            # 条件操作
            "check_condition_and_execute": self.check_condition_and_execute,
        }
        handler = action_map.get(action)
        if not handler:
            return {"status": "error", "message": f"未知的操作: {action}"}
        
        try:
            return await handler(parameters)
        except Exception as e:
            logger.error(f"执行操作失败: {str(e)}")
            return {"status": "error", "message": f"执行操作失败: {str(e)}"}

    # ==================== 基础操作 ====================
    
    async def go_to_url(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """导航到URL"""
        url = parameters.get('url')
        if not url:
            return {"status": "error", "message": "未指定URL"}
        
        try:
            page = await self.browser_context.get_current_page()
            await page.goto(url)
            await self.browser_context._wait_for_page_and_frames_load()
            
            state = await self.browser_context.get_state()
            return {
                "status": "success",
                "message": f"成功导航到 {url}",
                "url": state.url,
                "title": state.title
            }
        except Exception as e:
            return {"status": "error", "message": f"导航失败: {str(e)}"}
    
    async def click_element(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """点击元素，并自动检测是否有新标签页被创建"""
        index = parameters.get('index')
        auto_switch_tab = parameters.get('auto_switch_tab', True)  # 新参数，默认为True
        
        if index is None:
            return {"status": "error", "message": "未指定元素索引"}
        
        try:
            await self.highlight_elements({"viewport_expansion": 500})
            # 获取点击前的标签页信息
            tabs_before = await self.browser_context.get_tabs_info()
            # 获取元素信息
            dom_element = await self.browser_context.get_dom_element_by_index(index)
            element_text = dom_element.get_all_text_till_next_clickable_element() if dom_element else "未知元素"
            
            # 点击元素
            await self.browser_context._click_element_node(dom_element)
            
            # 等待页面加载和可能的新标签页创建
            await asyncio.sleep(0.5)  # 给新标签页一点创建时间
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 获取点击后的标签页信息
            tabs_after = await self.browser_context.get_tabs_info()
            
            # 检查是否有新标签页创建
            new_tabs = [tab for tab in tabs_after if tab.page_id not in [t.page_id for t in tabs_before]]
            
            # 如果有新标签页并且auto_switch_tab为True，则自动切换到新标签页
            if new_tabs and auto_switch_tab:
                new_tab = new_tabs[0]
                await self.browser_context.switch_to_tab(new_tab.page_id)
                await self.browser_context._wait_for_page_and_frames_load()
                
                return {
                    "status": "success",
                    "message": f"成功点击元素并切换到新标签页: {element_text}",
                    "element_index": index,
                    "element_text": element_text,
                    "new_tab_created": True,
                    "new_tab_id": new_tab.page_id,
                    "url": new_tab.url,
                    "title": new_tab.title,
                    "elements_count": len(await self.browser_context.get_selector_map())
                }
            
            # 获取新状态
            new_state = await self.browser_context.get_state()
            
            # 如果有新标签页但没有自动切换，也报告这一情况
            has_new_tabs = len(new_tabs) > 0
            
            return {
                "status": "success",
                "message": f"成功点击元素: {element_text}" + (" (已创建新标签页但未切换)" if has_new_tabs and not auto_switch_tab else ""),
                "element_index": index,
                "element_text": element_text,
                "new_tab_created": has_new_tabs,
                "new_tab_ids": [tab.page_id for tab in new_tabs] if has_new_tabs else [],
                "url": new_state.url,
                "title": new_state.title,
                "elements_count": len(new_state.selector_map) if new_state.selector_map else 0
            }
        except Exception as e:
            return {"status": "error", "message": f"点击元素失败: {str(e)}"}
    
    async def input_text(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """点击指定元素并输入文本"""
        index = parameters.get('index')
        text = parameters.get('text')
        
        if index is None:
            return {"status": "error", "message": "未指定元素索引"}
        if text is None:
            return {"status": "error", "message": "未指定输入文本"}
        
        try:
            await self.highlight_elements({"viewport_expansion": 500})
            # 获取元素信息
            dom_element = await self.browser_context.get_dom_element_by_index(index)
            element_type = dom_element.tag_name if dom_element else "未知类型"

            # 输入文本
            await self.browser_context._input_text_element_node(dom_element, text)
            
            return {
                "status": "success",
                "message": f"成功在{element_type}元素中输入文本",
                "element_index": index,
                "element_type": element_type,
                "text": text
            }
        except Exception as e:
            return {"status": "error", "message": f"输入文本失败: {str(e)}"}
    
    async def extract_content(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """提取页面内容并可选择性地高亮元素"""
        goal = parameters.get('goal')
        highlight_elements = parameters.get('highlight_elements', True)  # 新增参数，默认为True
        viewport_expansion = parameters.get('viewport_expansion', 500)   # 新增参数
        max_elements = parameters.get('max_elements', 150)               # 新增参数，限制返回元素数量
        
        if not goal:
            return {"status": "error", "message": "未指定提取目标"}
        
        try:
            page = await self.browser_context.get_current_page()
            
            # 如果需要高亮元素，先执行高亮
            if highlight_elements:
                dom_service = DomService(page)
                all_elements_state = await time_execution_sync('get_all_elements')(dom_service.get_clickable_elements)(
                    highlight_elements=True, 
                    viewport_expansion=viewport_expansion
                )
            
            # 获取当前页面状态
            state = await self.browser_context.get_state()
            
            # 提取页面标题和URL
            extracted_info = {
                "url": state.url,
                "title": state.title,
                "extraction_goal": goal
            }
            
            # 获取可能包含目标信息的文本内容
            text_content = []
            for element in state.selector_map.values():
                text = element.get_all_text_till_next_clickable_element()
                if text and len(text.strip()) > 0:
                    text_content.append(text)
            
            # 如果启用了高亮，提取元素的详细信息
            elements_info = []
            if highlight_elements and state.selector_map:
                for index, element in list(state.selector_map.items())[:max_elements]:
                    # 提取关键属性
                    key_attributes = {k: v for k, v in element.attributes.items() 
                                    if k in ['id', 'class', 'name', 'type', 'placeholder', 'href', 'role', 'title', 'aria-label']}
                    
                    # 获取元素文本内容
                    element_text = element.get_all_text_till_next_clickable_element()
                    
                    elements_info.append({
                        "index": index,
                        "tag_name": element.tag_name,
                        "text": element_text[:50] if element_text else "",  # 限制文本长度
                        "attributes": key_attributes,
                        #"is_visible": element.is_visible,
                        #"is_interactive": element.is_interactive,
                        #"is_in_viewport": element.is_in_viewport
                    })
            
            extraction_summary = f"""从页面提取了{len(text_content)}个文本块，可能包含"{goal}"相关信息"""
            if highlight_elements:
                extraction_summary += f"，并高亮了{len(state.selector_map)}个可交互元素"
            
            result = {
                "status": "success",
                #"message": extraction_summary,
                #"extracted_info": extracted_info,
                "text_blocks": text_content[:100],  # 增加返回的文本块数量
                #"text_blocks_count": len(text_content),
                "extraction_goal": goal
            }
            
            # 如果高亮了元素，添加元素信息
            if highlight_elements:
                result["elements_count"] = len(state.selector_map)
                result["elements"] = elements_info
                result["has_more_elements"] = len(state.selector_map) > max_elements
                
            return result
        except Exception as e:
            return {"status": "error", "message": f"提取内容失败: {str(e)}"}
    
    async def scroll(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """滚动页面"""
        direction = parameters.get('direction', 'down')
        amount = parameters.get('amount', 'medium')
        
        # 转换滚动量为像素值
        amount_map = {
            "small": 200,
            "medium": 500,
            "large": 1000,
            "page": 1500
        }
        pixel_amount = amount_map.get(amount, 500)
        
        # 根据方向调整滚动值
        if direction == "up":
            pixel_amount = -pixel_amount
        
        try:
            page = await self.browser_context.get_current_page()
            await page.evaluate(f"window.scrollBy(0, {pixel_amount})")
            
            # 等待滚动完成
            await asyncio.sleep(0.5)
            
            # 刷新元素状态
            await self.browser_context.get_state()
            
            return {
                "status": "success",
                "message": f"成功向{direction}滚动页面({amount})",
                "direction": direction,
                "amount": amount,
                "pixels": pixel_amount
            }
        except Exception as e:
            return {"status": "error", "message": f"滚动页面失败: {str(e)}"}
    
    async def wait(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """等待一段时间或元素出现"""
        time_seconds = parameters.get('time', 0.5)
        selector = parameters.get('selector')
        
        try:
            if selector:
                page = await self.browser_context.get_current_page()
                try:
                    await page.wait_for_selector(selector, timeout=time_seconds * 1000)
                    return {
                        "status": "success",
                        "message": f"元素 {selector} 已出现",
                        "wait_type": "selector"
                    }
                except Exception as e:
                    return {
                        "status": "error", 
                        "message": f"等待元素 {selector} 超时: {str(e)}",
                    }
            else:
                await asyncio.sleep(time_seconds)
                return {
                    "status": "success",
                    "message": f"成功等待{time_seconds}秒",
                    "wait_type": "time",
                    "wait_time": time_seconds
                }
        except Exception as e:
            return {"status": "error", "message": f"等待失败: {str(e)}"}
    
    # ==================== 标签页操作 ====================
    
    async def get_tabs(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取所有标签页信息"""
        try:
            tabs_info = await self.browser_context.get_tabs_info()
            
            return {
                "status": "success",
                "message": f"成功获取{len(tabs_info)}个标签页信息",
                "tabs": [tab.dict() for tab in tabs_info]
            }
        except Exception as e:
            return {"status": "error", "message": f"获取标签页信息失败: {str(e)}"}
    
    async def create_tab(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """创建新标签页"""
        url = parameters.get('url', 'about:blank')
        
        try:
            # 保存当前标签页信息
            tabs_before = await self.browser_context.get_tabs_info()
            
            # 创建新标签页
            await self.browser_context.create_new_tab(url)
            
            # 等待页面加载
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 获取新标签页信息
            tabs_after = await self.browser_context.get_tabs_info()
            new_tabs = [tab for tab in tabs_after if tab.page_id not in [t.page_id for t in tabs_before]]
            
            if not new_tabs:
                return {"status": "error", "message": "无法识别新创建的标签页"}
            
            new_tab = new_tabs[0]
            
            return {
                "status": "success",
                "message": f"成功创建新标签页并导航到 {url}",
                "tab_id": new_tab.page_id,
                "tab_title": new_tab.title,
                "tab_url": new_tab.url
            }
        except Exception as e:
            return {"status": "error", "message": f"创建新标签页失败: {str(e)}"}
    
    async def switch_tab(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """切换标签页"""
        tab_id = parameters.get('tab_id')
        if tab_id is None:
            return {"status": "error", "message": "未指定标签页ID"}
        
        try:
            await self.browser_context.switch_to_tab(tab_id)
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 获取当前标签页信息
            tabs_info = await self.browser_context.get_tabs_info()
            current_tab = next((tab for tab in tabs_info if tab.page_id == tab_id), None)
            
            return {
                "status": "success",
                "message": f"成功切换到标签页 {tab_id}",
                "tab_id": tab_id,
                "tab_title": current_tab.title if current_tab else "未知",
                "tab_url": current_tab.url if current_tab else "未知"
            }
        except Exception as e:
            return {"status": "error", "message": f"切换标签页失败: {str(e)}"}
    
    async def close_tab(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """关闭标签页"""
        try:
            await self.browser_context.close_current_tab()
            
            # 获取关闭后的标签页信息
            tabs_info = await self.browser_context.get_tabs_info()
            
            return {
                "status": "success",
                "message": "成功关闭当前标签页",
                "remaining_tabs_count": len(tabs_info)
            }
        except Exception as e:
            return {"status": "error", "message": f"关闭标签页失败: {str(e)}"}
    
    # ==================== 元素查找与操作 ====================
    
    async def highlight_elements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """高亮并获取页面上的可点击元素"""
        viewport_expansion = parameters.get('viewport_expansion', 500)
        
        try:
            page = await self.browser_context.get_current_page()
            
            # 创建DOM服务并高亮元素
            dom_service = DomService(page)
            all_elements_state = await time_execution_sync('get_all_elements')(dom_service.get_clickable_elements)(
                highlight_elements=True, 
                viewport_expansion=viewport_expansion
            )
            
            # 更新浏览器状态
            state = await self.browser_context.get_state()
            
            return {
                "status": "success",
                "message": f"成功高亮{len(state.selector_map)}个元素",
                "elements_count": len(state.selector_map),
                "page_url": state.url,
                "page_title": state.title
            }
        except Exception as e:
            return {"status": "error", "message": f"高亮元素失败: {str(e)}"}
    
    async def find_element_by_text(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """通过文本内容查找元素"""
        text = parameters.get('text')
        partial_match = parameters.get('partial_match', True)
        highlight_elements = parameters.get('highlight_elements', True)
        
        if not text:
            return {"status": "error", "message": "未指定要查找的文本"}
        
        try:
            # 确保页面元素已加载并高亮
            if highlight_elements:
                await self.highlight_elements({"viewport_expansion": 500})
            
            # 获取选择器映射
            selector_map = await self.browser_context.get_selector_map()
            
            # 查找匹配文本的元素
            found_elements = []
            for index, element in selector_map.items():
                # 获取元素的所有文本内容
                element_text = element.get_all_text_till_next_clickable_element() or ""
                
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
                        found_elements.append({
                            "index": index,
                            "text": element_text[:100] + ("..." if len(element_text) > 100 else ""),
                            "tag_name": element.tag_name,
                            "attributes": {k: v for k, v in element.attributes.items() if k in ['id', 'class', 'name', 'type']}
                        })
                else:
                    if text.lower() == all_text.lower():
                        found_elements.append({
                            "index": index,
                            "text": element_text[:100] + ("..." if len(element_text) > 100 else ""),
                            "tag_name": element.tag_name,
                            "attributes": {k: v for k, v in element.attributes.items() if k in ['id', 'class', 'name', 'type']}
                        })
            
            return {
                "status": "success",
                "message": f"找到{len(found_elements)}个匹配文本'{text}'的元素",
                "found_elements": found_elements,
                "match_type": "partial" if partial_match else "exact"
            }
        except Exception as e:
            return {"status": "error", "message": f"查找元素失败: {str(e)}"}
    
    async def find_element_by_attribute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """通过属性查找元素"""
        attribute = parameters.get('attribute')
        value = parameters.get('value')
        partial_match = parameters.get('partial_match', True)
        highlight_elements = parameters.get('highlight_elements', True)
        
        if not attribute or value is None:
            return {"status": "error", "message": "未指定要查找的属性或值"}
        
        try:
            # 确保页面元素已加载并高亮
            if highlight_elements:
                await self.highlight_elements({"viewport_expansion": 500})
            
            # 获取选择器映射
            selector_map = await self.browser_context.get_selector_map()
            
            # 查找匹配属性的元素
            found_elements = []
            for index, element in selector_map.items():
                # 检查元素属性
                attr_value = element.attributes.get(attribute)
                if attr_value is not None:
                    # 进行属性值匹配
                    if partial_match:
                        if str(value).lower() in str(attr_value).lower():
                            found_elements.append({
                                "index": index,
                                "tag_name": element.tag_name,
                                "attribute": attribute,
                                "value": attr_value,
                                "text": element.get_all_text_till_next_clickable_element()[:100]
                            })
                    else:
                        if str(value).lower() == str(attr_value).lower():
                            found_elements.append({
                                "index": index,
                                "tag_name": element.tag_name,
                                "attribute": attribute,
                                "value": attr_value,
                                "text": element.get_all_text_till_next_clickable_element()[:100]
                            })
            
            return {
                "status": "success",
                "message": f"找到{len(found_elements)}个属性{attribute}匹配'{value}'的元素",
                "found_elements": found_elements,
                "match_type": "partial" if partial_match else "exact"
            }
        except Exception as e:
            return {"status": "error", "message": f"查找元素失败: {str(e)}"}
    
    # ==================== 高级操作 ====================
    
    async def inject_script(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """注入JavaScript脚本到页面"""
        script = parameters.get('script')
        if not script:
            return {"status": "error", "message": "未指定要注入的脚本"}
        
        try:
            page = await self.browser_context.get_current_page()
            result = await page.evaluate(script)
            
            return {
                "status": "success",
                "message": "成功注入并执行脚本",
                "execution_result": str(result) if result is not None else "无返回值"
            }
        except Exception as e:
            return {"status": "error", "message": f"注入脚本失败: {str(e)}"}
    
    async def input_by_selector(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """通过CSS选择器或XPath直接输入文本"""
        selector = parameters.get('selector')
        text = parameters.get('text')
        
        if not selector or text is None:
            return {"status": "error", "message": "未指定选择器或文本"}
        
        try:
            page = await self.browser_context.get_current_page()
            
            # 尝试找到元素
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "message": f"未找到匹配选择器 {selector} 的元素"}
            
            # 清空当前值
            await element.fill("")
            
            # 输入新值
            await element.type(text)
            
            return {
                "status": "success",
                "message": f"成功通过选择器 {selector} 输入文本",
                "selector": selector,
                "text": text
            }
        except Exception as e:
            return {"status": "error", "message": f"输入文本失败: {str(e)}"}

    # ==================== 组合工具方法 ====================
    
    async def get_or_create_tab_with_url(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查是否已有包含指定URL的标签页，如果有则切换到该页面，
        如果没有则创建新标签页并导航到指定URL
        """
        base_url = parameters.get('url')
        if not base_url:
            return {"status": "error", "message": "未指定URL"}
            
        try:
            # 获取所有标签页信息
            tabs_info = await self.browser_context.get_tabs_info()
            
            # 查找是否有匹配URL的标签页
            matching_tab = None
            for tab in tabs_info:
                if base_url in tab.url:
                    matching_tab = tab
                    break
            
            # 如果找到匹配的标签页，则切换到该页面
            if matching_tab:
                logger.info(f"找到包含URL'{base_url}'的标签页，ID为: {matching_tab.page_id}")
                await self.browser_context.switch_to_tab(matching_tab.page_id)
                await self.browser_context._wait_for_page_and_frames_load()
                
                return {
                    "status": "success",
                    "message": f"成功切换到包含'{base_url}'的现有标签页",
                    "tab_id": matching_tab.page_id,
                    "tab_url": matching_tab.url,
                    "tab_title": matching_tab.title,
                    "action": "switched"
                }
            else:
                # 如果没有找到，创建新标签页并导航
                logger.info(f"未找到包含URL'{base_url}'的标签页，创建新标签页...")
                await self.browser_context.create_new_tab(base_url)
                await self.browser_context._wait_for_page_and_frames_load()
                
                # 获取新标签页信息
                new_tabs = await self.browser_context.get_tabs_info()
                new_tab = new_tabs[-1]  # 假设最新的标签页是刚创建的
                
                return {
                    "status": "success",
                    "message": f"成功创建并导航到包含'{base_url}'的新标签页",
                    "tab_id": new_tab.page_id,
                    "tab_url": new_tab.url,
                    "tab_title": new_tab.title,
                    "action": "created"
                }
        except Exception as e:
            logger.error(f"获取或创建标签页失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取或创建标签页失败: {str(e)}"
            }
    
    async def find_and_click_element_by_text(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        查找并点击包含指定文本的元素，自动检测新标签页
        
        Args:
            parameters: 参数字典
                - text: 要查找的文本内容
                - partial_match: 是否使用部分匹配（默认为True）
                - auto_switch_tab: 是否自动切换到新标签页（默认为True）
        Returns:
            操作结果
        """
        text = parameters.get('text')
        partial_match = parameters.get('partial_match', True)
        auto_switch_tab = parameters.get('auto_switch_tab', True)
        
        if not text:
            return {"status": "error", "message": "未指定要查找的文本"}
            
        try:
            # 确保元素已高亮
            await self.highlight_elements({"viewport_expansion": 500})
            
            # 通过文本查找元素
            find_result = await self.find_element_by_text({
                "text": text,
                "partial_match": partial_match,
                "highlight_elements": False
            })
            
            if find_result["status"] != "success" or not find_result.get("found_elements"):
                return {
                    "status": "error",
                    "message": f"未找到包含文本'{text}'的元素",
                    "find_result": find_result
                }
            
            # 点击找到的第一个元素
            first_element = find_result["found_elements"][0]
            element_index = first_element["index"]
            
            # 记录点击前的标签页信息
            tabs_before = await self.browser_context.get_tabs_info()
            
            # 点击元素（按照原代码逻辑，先禁用自动切换）
            click_result = await self.click_element({
                "index": element_index,
                "auto_switch_tab": False
            })
            
            # 等待可能的新标签页创建完成
            await asyncio.sleep(1.5)
            
            # 获取点击后的标签页信息
            tabs_after = await self.browser_context.get_tabs_info()
            new_tabs = [tab for tab in tabs_after if tab.page_id not in [t.page_id for t in tabs_before]]
            
            # 检查是否有新标签页创建
            if new_tabs:
                new_tab = new_tabs[0]
                new_tab_id = new_tab.page_id
                
                # 如果需要自动切换
                if auto_switch_tab:
                    logger.info(f"切换到新标签页 {new_tab_id}")
                    await self.browser_context.switch_to_tab(new_tab_id)
                    await self.browser_context._wait_for_page_and_frames_load()
                    
                    return {
                        "status": "success",
                        "message": f"成功查找并点击包含文本'{text}'的元素，已切换到新标签页",
                        "element_index": element_index,
                        "element_text": first_element["text"],
                        "new_tab_created": True,
                        "new_tab_id": new_tab_id,
                        "url": new_tab.url,
                        "title": new_tab.title
                    }
                else:
                    return {
                        "status": "success",
                        "message": f"成功查找并点击包含文本'{text}'的元素，已创建新标签页但未切换",
                        "element_index": element_index,
                        "element_text": first_element["text"],
                        "new_tab_created": True,
                        "new_tab_id": new_tab_id,
                        "url": new_tab.url,
                        "title": new_tab.title
                    }
            else:
                # 没有创建新标签页
                return {
                    "status": "success",
                    "message": f"成功查找并点击包含文本'{text}'的元素，未创建新标签页",
                    "element_index": element_index,
                    "element_text": first_element["text"],
                    "new_tab_created": False,
                    "click_result": click_result
                }
        except Exception as e:
            logger.error(f"查找并点击元素失败: {str(e)}")
            return {"status": "error", "message": f"查找并点击元素失败: {str(e)}"}

    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("清理处理器资源")
            await self.browser_context.remove_highlights()
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")


    async def create_mask_interceptor(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建一个带有数据遮罩的标签页
        
        Args:
            parameters: 参数字典
                - target_url: 要导航到的URL
        Returns:
            操作结果
        """
        target_url = parameters.get('target_url')
        if not target_url:
            return {"status": "error", "message": "未指定目标URL"}

        try:
            # 记录当前标签页信息
            tabs_before = await self.browser_context.get_tabs_info()
            
            # 创建新标签页
            await self.browser_context.create_new_tab("about:blank")
            
            # 等待标签页创建完成
            await asyncio.sleep(1)
            
            # 获取新标签页信息并切换
            tabs_after = await self.browser_context.get_tabs_info()
            new_tabs = [tab for tab in tabs_after if tab.page_id not in [t.page_id for t in tabs_before]]
            
            if not new_tabs:
                return {"status": "error", "message": "无法创建新标签页"}
            
            new_tab = new_tabs[0]
            await self.browser_context.switch_to_tab(new_tab.page_id)
            
            # 获取当前页面
            page = await self.browser_context.get_current_page()
            
            # 创建带有特定参数的路由处理函数
            add_mask_handler = lambda route, request: self._add_mask_to_response(route, request)
            
            # 设置路由拦截器
            await page.route("**/*", add_mask_handler)
            
            # 导航到目标URL
            await page.goto(target_url)
            
            # 等待页面加载
            await self.browser_context._wait_for_page_and_frames_load()
            
            return {
                "status": "success",
                "message": f"成功创建带遮罩的标签页并导航到 {target_url}",
                "tab_id": new_tab.page_id,
                "url": target_url
            }
        except Exception as e:
            return {"status": "error", "message": f"创建带遮罩标签页失败: {str(e)}"}
    

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
                mask_script = ScriptTemplates.data_mask_overlay()
                
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

    async def input_text_and_search(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        简单通用的搜索功能：查找搜索框、输入文本并执行搜索
        
        Args:
            parameters: 参数字典
                - search_text: 要搜索的文本
                - input_index: 可选，直接指定输入框索引
        
        Returns:
            操作结果
        """
        search_text = parameters.get('search_text')
        input_index = parameters.get('input_index')
        
        if not search_text:
            return {"status": "error", "message": "未指定搜索文本"}
        
        try:
            # 1. 高亮所有元素
            await self.highlight_elements({"viewport_expansion": 500})
            
            # 2. 如果没有指定输入框索引，则自动查找输入框
            if input_index is None:
                # 查找输入框 (通常是带有placeholder的input元素)
                input_result = await self.find_element_by_attribute({
                    "attribute": "type", 
                    "value": "text",
                    "highlight_elements": False
                })
                
                # 如果找不到type=text的元素，尝试查找任何input元素
                if not input_result.get("found_elements"):
                    input_result = await self.find_element_by_attribute({
                        "attribute": "tag_name", 
                        "value": "input",
                        "highlight_elements": False
                    })
                
                if not input_result.get("found_elements"):
                    return {"status": "error", "message": "未找到搜索输入框"}
                
                # 使用找到的第一个输入框
                input_index = input_result["found_elements"][0]["index"]
            
            # 3. 点击输入框并输入文本（直接使用BaseHandler的方法）
            await self.click_element({"index": input_index})
            input_result = await self.input_text({"index": input_index, "text": search_text})
            
            # 4. 尝试多种方式触发搜索
            script = """
            // 1. 尝试提交表单
            const activeElement = document.activeElement;
            let searchTriggered = false;
            
            if (activeElement && activeElement.form) {
                activeElement.form.submit();
                searchTriggered = true;
                console.log('搜索表单已提交');
            }
            
            // 2. 如果没有表单，尝试查找并点击搜索按钮
            if (!searchTriggered) {
                const searchButton = document.querySelector('button[type="submit"], input[type="submit"], button[aria-label*="search" i], button.search-button');
                if (searchButton) {
                    searchButton.click();
                    searchTriggered = true;
                    console.log('搜索按钮已点击');
                }
            }
            
            // 3. 如果以上方法都失败，尝试发送Enter键事件
            if (!searchTriggered && activeElement) {
                ['keydown', 'keypress', 'keyup'].forEach(eventType => {
                    activeElement.dispatchEvent(new KeyboardEvent(eventType, {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true,
                        cancelable: true
                    }));
                });
                console.log('Enter键事件已分发');
            }
            """
            
            await self.inject_script({"script": script})
            await self.wait({"time": 1})  # 等待搜索结果加载
            await self.highlight_elements({"viewport_expansion": 500})
            
            return {
                "status": "success",
                "message": f"成功执行搜索: {search_text}",
                "search_text": search_text,
                "input_index": input_index,
                "input_result": input_result
            }
        
        except Exception as e:
            return {"status": "error", "message": f"搜索操作失败: {str(e)}"}
            
    async def search_and_navigate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        在指定网站搜索关键词并导航到相关结果页面
        
        Args:
            parameters: 参数字典
                - base_url: 要搜索的网站URL
                - search_keyword: 搜索关键词
                - search_button_text: 搜索按钮的文本标识（默认为"搜索"）
                - result_keyword: 结果页面中要查找的关键词
                - wait_after_search: 搜索后等待时间（秒）
        Returns:
            操作结果
        """
        base_url = parameters.get('base_url')
        search_keyword = parameters.get('search_keyword')
        search_button_text = parameters.get('search_button_text', '搜索')
        result_keyword = parameters.get('result_keyword')
        wait_after_search = parameters.get('wait_after_search', 0.5)
        
        if not base_url or not search_keyword or not result_keyword:
            return {"status": "error", "message": "缺少必要参数：base_url、search_keyword或result_keyword"}
        
        try:
            # 获取或创建目标网站标签页
            await self.get_or_create_tab_with_url({"url": base_url})
            
            # 高亮页面元素
            await self.highlight_elements({"viewport_expansion": 500})
            
            search_box_found = await self.find_element_by_attribute({
                "attribute": "placeholder", 
                "value": "请输入您要办理的事项",
                "partial_match": True
            })
            
            search_box_index = None
            if search_box_found.get("found_elements"):
                search_box_index = search_box_found["found_elements"][0]["index"]
            
            # 查找搜索按钮
            search_button = await self.find_element_by_text({
                "text": search_button_text, 
                "partial_match": True
            })
            await self.highlight_elements({"viewport_expansion": 500})
            search_button_index = None
            if search_button.get("found_elements"):
                search_button_index = search_button["found_elements"][0]["index"]
                        
            if not search_box_index:
                return {"status": "error", "message": "未找到搜索输入框"}

            # 点击搜索框并输入关键词
            await self.click_element({"index": search_box_index})
            #await self.wait({"time": 1})
            await self.input_text({"index": search_box_index, "text": search_keyword})
            await self.wait({"time": 1})
            
            # 点击搜索按钮或按回车
            if search_button_index:
                await self.click_element({"index": search_button_index})
            else:
                await self.inject_script({
                    "script": """
                    const event = new KeyboardEvent('keydown', {
                        'key': 'Enter',
                        'code': 'Enter',
                        'keyCode': 13,
                        'which': 13,
                        'bubbles': true
                    });
                    document.activeElement.dispatchEvent(event);
                    """
                })
            
            # 等待搜索结果
            await self.wait({"time": wait_after_search})
            
            # 重新高亮元素获取搜索结果
            await self.highlight_elements({"viewport_expansion": 500})
            
            # 查找并点击目标结果
            result_links = await self.find_element_by_text({
                "text": result_keyword, 
                "partial_match": True
            })
            
            if result_links.get("found_elements"):
                # 点击第一个相关链接
                first_link = result_links["found_elements"][0]
                link_result = await self.click_element({
                    "index": first_link["index"],
                    "auto_switch_tab": True
                })
                
                # 等待页面加载
                await self.wait({"time": 0.3})
                
                # 在新页面中高亮元素
                await self.highlight_elements({"viewport_expansion": 500})
                
                return {
                    "status": "success", 
                    "message": f"成功搜索并导航到'{result_keyword}'相关页面",
                    "new_tab_created": link_result.get("new_tab_created", False),
                    "url": link_result.get("url", "未知")
                }
            else:
                return {
                    "status": "warning",
                    "message": f"已完成搜索，但未找到包含'{result_keyword}'的链接",
                    "url": (await self.browser_context.get_state()).url
                }
        
        except Exception as e:
            logger.error(f"搜索并导航失败: {str(e)}")
            return {
                "status": "error",
                "message": f"搜索并导航失败: {str(e)}"
            }
    # ==================== 用户交互操作 ====================

    async def request_user_action(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        请求用户手动执行操作
        
        Args:
            parameters: 参数字典
                - type: 交互类型 (login|select|verify|input|decision)
                - message: 给用户的提示消息
                - description: 详细说明
                - options: 可选的选项列表
        Returns:
            操作结果
        """
        action_type = parameters.get('type', 'generic')
        message = parameters.get('message', '请执行操作')
        description = parameters.get('description', '')
        options = parameters.get('options', [])
        
        # 获取当前页面状态以便返回
        current_state = await self.browser_context.get_state()
        input("请确认登录系统，登录完成Enter继续...")
        return {
            "status": "success",
            "message": f"已请求用户进行{action_type}操作",
            "user_action_type": action_type,
            "user_action_message": message,
            "user_action_description": description,
            "options": options,
            "url": current_state.url,
            "title": current_state.title,
            "elements_count": len(current_state.selector_map) if current_state.selector_map else 0
        }

    async def evaluate_state(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估当前页面状态
        
        Args:
            parameters: 参数字典
                - description: 状态描述
        Returns:
            当前页面状态
        """
        description = parameters.get('description', '评估当前状态')
        
        # 刷新元素高亮以获取最新的页面元素
        await self.highlight_elements({"viewport_expansion": 500})
        
        # 获取当前页面状态
        current_state = await self.browser_context.get_state()
        
        # 尝试提取页面上的关键文本
        text_content = []
        if current_state.selector_map:
            for element in current_state.selector_map.values():
                text = element.get_all_text_till_next_clickable_element()
                if text and len(text.strip()) > 0:
                    text_content.append(text)
        
        return {
            "status": "success",
            "message": f"状态评估: {description}",
            "url": current_state.url,
            "title": current_state.title,
            "elements_count": len(current_state.selector_map) if current_state.selector_map else 0,
            "text_blocks": text_content[:10] if text_content else [],  # 只返回前10个文本块避免数据过大
            "text_blocks_count": len(text_content) if text_content else 0
        }

    async def check_condition_and_execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查条件并根据条件执行或跳过特定操作
        
        参数:
            parameters: 参数字典
                - condition_check: 条件检查配置
                    - type: 检查类型 (element_exists|element_not_exists|text_exists|text_not_exists)
                    - parameters: 检查参数，根据检查类型而定
                - action_if_true: 条件为真时执行的操作
                - action_if_false: 条件为假时执行的操作（可选）
                - default_result: 默认结果，当conditions不满足且没有action_if_false时返回（可选）
        返回:
            操作结果
        """
        condition_check = parameters.get('condition_check')
        action_if_true = parameters.get('action_if_true')
        action_if_false = parameters.get('action_if_false')
        default_result = parameters.get('default_result', {"status": "success", "message": "条件不满足，已跳过操作"})
        
        if not condition_check or not action_if_true:
            return {"status": "error", "message": "未指定条件检查或条件为真时的操作"}
        
        try:
            # 根据不同类型的条件检查执行不同的检查逻辑
            check_type = condition_check.get('type')
            check_params = condition_check.get('parameters', {})
            
            condition_result = False
            
            # 检查元素是否存在
            if check_type == 'element_exists':
                text = check_params.get('text')
                partial_match = check_params.get('partial_match', True)
                
                if text:
                    find_result = await self.find_element_by_text({
                        "text": text,
                        "partial_match": partial_match,
                        "highlight_elements": True
                    })
                    
                    condition_result = find_result.get("status") == "success" and len(find_result.get("found_elements", [])) > 0
            
            # 检查元素是否不存在
            elif check_type == 'element_not_exists':
                text = check_params.get('text')
                partial_match = check_params.get('partial_match', True)
                
                if text:
                    find_result = await self.find_element_by_text({
                        "text": text,
                        "partial_match": partial_match,
                        "highlight_elements": True
                    })
                    
                    condition_result = find_result.get("status") == "success" and len(find_result.get("found_elements", [])) == 0
            
            # 检查页面是否包含特定文本
            elif check_type == 'text_exists':
                text = check_params.get('text')
                
                if text:
                    extract_result = await self.extract_content({"goal": f"查找文本 '{text}'"})
                    
                    text_blocks = extract_result.get("text_blocks", [])
                    condition_result = any(text in block for block in text_blocks)
            
            # 检查页面是否不包含特定文本
            elif check_type == 'text_not_exists':
                text = check_params.get('text')
                
                if text:
                    extract_result = await self.extract_content({"goal": f"查找文本 '{text}'"})
                    
                    text_blocks = extract_result.get("text_blocks", [])
                    condition_result = not any(text in block for block in text_blocks)
            
            # 检查用户是否已登录（可以通过检查页面上是否存在"登录"按钮或是否存在用户名等方式）
            elif check_type == 'is_logged_in':
                login_text = check_params.get('login_button_text', '登录')
                user_element_text = check_params.get('user_element_text', '我的')
                
                # 检查登录按钮是否不存在
                login_button_result = await self.find_element_by_text({
                    "text": login_text,
                    "partial_match": True,
                    "highlight_elements": True
                })
                
                login_button_not_exists = len(login_button_result.get("found_elements", [])) == 0
                
                # 检查用户元素是否存在
                user_element_result = await self.find_element_by_text({
                    "text": user_element_text,
                    "partial_match": True,
                    "highlight_elements": True
                })
                
                user_element_exists = len(user_element_result.get("found_elements", [])) > 0
                
                # 如果登录按钮不存在或用户元素存在，则认为已登录
                condition_result = login_button_not_exists or user_element_exists
            
            # 根据条件结果执行相应的操作
            if condition_result:
                logger.info(f"条件检查结果为真，执行action_if_true")
                
                action_name = list(action_if_true.keys())[0]
                action_params = action_if_true[action_name]
                
                return await self.process_query({
                    "action": action_name,
                    **action_params
                })
            else:
                logger.info(f"条件检查结果为假")
                
                if action_if_false:
                    action_name = list(action_if_false.keys())[0]
                    action_params = action_if_false[action_name]
                    
                    return await self.process_query({
                        "action": action_name,
                        **action_params
                    })
                else:
                    return default_result
        
        except Exception as e:
            logger.error(f"条件检查执行失败: {str(e)}")
            return {"status": "error", "message": f"条件检查执行失败: {str(e)}"}