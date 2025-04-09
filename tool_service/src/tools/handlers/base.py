# tool_service/src/tools/handlers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class BaseHandler:
    """通用处理器，处理基本的浏览器操作"""
    
    def __init__(self, browser_context):
        self.browser_context = browser_context
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用请求"""
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 基础操作映射
        action_map = {
            "go_to_url": self.go_to_url,
            "click_element": self.click_element,
            "input_text": self.input_text,
            "extract_content": self.extract_content,
            "scroll": self.scroll,
            "wait": self.wait,
        }
        
        handler = action_map.get(action)
        if not handler:
            return {"status": "error", "message": f"未知的操作: {action}"}
        
        try:
            return await handler(parameters)
        except Exception as e:
            logger.error(f"执行操作失败: {str(e)}")
            return {"status": "error", "message": f"执行操作失败: {str(e)}"}
    
    async def go_to_url(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """导航到URL"""
        url = parameters.get('url')
        if not url:
            return {"status": "error", "message": "未指定URL"}
        
        try:
            await self.browser_context.go_to_url(url)
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
        """点击元素"""
        index = parameters.get('index')
        if index is None:
            return {"status": "error", "message": "未指定元素索引"}
        
        try:
            # 获取元素信息
            state = await self.browser_context.get_state()
            element_info = state.selector_map.get(index)
            element_text = element_info.get_all_text_till_next_clickable_element() if element_info else "未知元素"
            
            # 点击元素
            await self.browser_context.click_element(index)
            
            # 等待页面加载
            await self.browser_context._wait_for_page_and_frames_load()
            
            # 获取新状态
            new_state = await self.browser_context.get_state()
            
            return {
                "status": "success",
                "message": f"成功点击元素: {element_text}",
                "element_index": index,
                "element_text": element_text,
                "url": new_state.url,
                "title": new_state.title,
                "elements_count": len(new_state.selector_map) if new_state.selector_map else 0
            }
        except Exception as e:
            return {"status": "error", "message": f"点击元素失败: {str(e)}"}
    
    async def input_text(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """输入文本"""
        index = parameters.get('index')
        text = parameters.get('text')
        
        if index is None:
            return {"status": "error", "message": "未指定元素索引"}
        if text is None:
            return {"status": "error", "message": "未指定输入文本"}
        
        try:
            # 获取元素信息
            state = await self.browser_context.get_state()
            element_info = state.selector_map.get(index)
            element_type = element_info.tag_name if element_info else "未知类型"
            
            # 输入文本
            await self.browser_context.input_text(index, text)
            
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
        """提取页面内容"""
        goal = parameters.get('goal')
        if not goal:
            return {"status": "error", "message": "未指定提取目标"}
        
        try:
            state = await self.browser_context.get_state()
            
            # 这里简化处理，实际应用中可能需要更复杂的内容提取逻辑
            # 例如使用LLM或其他模型来理解页面内容
            
            # 提取页面标题和URL
            extracted_info = {
                "url": state.url,
                "title": state.title,
                "extraction_goal": goal
            }
            
            # 获取可能包含目标信息的文本
            text_content = []
            for element in state.selector_map.values():
                text = element.get_all_text_till_next_clickable_element()
                if text and len(text.strip()) > 0:
                    text_content.append(text)
            
            extraction_summary = f"""从页面提取了{len(text_content)}个文本块，可能包含"{goal}"相关信息"""
            
            return {
                "status": "success",
                "message": extraction_summary,
                "extracted_info": extracted_info,
                "text_blocks_count": len(text_content),
                "extraction_goal": goal
            }
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
        time_seconds = parameters.get('time', 2)
        
        try:
            await asyncio.sleep(time_seconds)
            return {
                "status": "success",
                "message": f"成功等待{time_seconds}秒",
                "wait_time": time_seconds
            }
        except Exception as e:
            return {"status": "error", "message": f"等待失败: {str(e)}"}
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理通用处理器资源")