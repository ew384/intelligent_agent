# tool_service/src/tools/handlers/browser_operations.py
from .base import BaseHandler
from typing import Dict, Any, List, Optional
import logging
import asyncio
import time
from pathlib import Path
import json

logger = logging.getLogger(__name__)
"""
浏览器操作处理器模块
职责:
1. 实现具体的浏览器操作逻辑
2. 使用浏览器会话API执行操作
3. 处理操作结果和错误
4. 返回结构化的操作结果
"""
class BrowserOperations(BaseHandler):  # 注意类名也改了
    """
    处理通用浏览器操作的处理器
    职责:
    1. 提供通用的浏览器交互操作
    2. 封装底层BrowserSession调用
    3. 处理操作结果和错误
    """
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理浏览器操作请求的业务逻辑"""
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 业务逻辑路由
        action_map = {
            "navigate": self.navigate,
            "wait_for_selector": self.wait_for_selector,
            "wait_for_login": self.wait_for_login,
            "click": self.click,
            "fill": self.fill,
            "extract_text": self.extract_element_text,
            "extract_elements": self.extract_elements,
            "execute_script": self.execute_script,
            "screenshot": self.take_screenshot,
        }
        # 调用具体的业务逻辑方法
        handler = action_map.get(action)
        if not handler:
            return {"status": "error", "message": f"未知的action: {action}"}
        
        return await handler(parameters)

    async def navigate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        导航到指定URL
        
        Args:
            parameters: 应包含url字段
            
        Returns:
            导航结果
        """
        url = parameters.get('url')
        if not url:
            return {"status": "error", "message": "缺少URL参数"}
        
        timeout = parameters.get('timeout', 300)  # 默认60秒超时
        
        try:
            logger.info(f"导航到URL: {url}")
            
            # 执行导航
            result = await self.session.goto(url, timeout=timeout)
            
            # 等待页面完全加载
            await self.session.wait_for_load_state('domcontentloaded')
            await self.session.wait_for_load_state('networkidle')
            
            return {
                "status": "success",
                "message": f"成功导航到 {url}",
                "url": url
            }
        except Exception as e:
            logger.error(f"导航到 {url} 时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"导航失败: {str(e)}"
            }
    
    async def wait_for_selector(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        等待选择器出现
        
        Args:
            parameters: 应包含selector字段和可选的timeout字段
            
        Returns:
            等待结果
        """
        selector = parameters.get('selector')
        if not selector:
            return {"status": "error", "message": "缺少selector参数"}
        
        timeout = parameters.get('timeout', 30000)  # 默认30秒超时
        
        try:
            logger.info(f"等待选择器: {selector}")
            
            element = await self.session.wait_for_selector(selector, timeout=timeout)
            
            if element:
                return {
                    "status": "success",
                    "message": f"选择器 {selector} 已出现"
                }
            else:
                return {
                    "status": "error",
                    "message": f"等待选择器 {selector} 超时"
                }
        except Exception as e:
            logger.error(f"等待选择器 {selector} 时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"等待选择器失败: {str(e)}"
            }
    
    async def wait_for_login(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        等待登录完成 - 使用登录指示器或文本指示
        
        Args:
            parameters: 应包含login_indicators和可选的timeout字段
            
        Returns:
            等待结果
        """
        pass
    
    async def click(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        点击元素
        
        Args:
            parameters: 应包含selector字段和可选的wait_time字段
            
        Returns:
            点击结果
        """
        selector = parameters.get('selector')
        if not selector:
            return {"status": "error", "message": "缺少selector参数"}
        
        wait_time = parameters.get('wait_time', 0.5)  # 默认点击后等待0.5秒
        
        try:
            logger.info(f"点击选择器: {selector}")
            
            result = await self.session.click(selector, wait_time=wait_time)
            
            if result:
                return {
                    "status": "success",
                    "message": f"成功点击 {selector}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"点击 {selector} 失败"
                }
        except Exception as e:
            logger.error(f"点击选择器 {selector} 时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"点击失败: {str(e)}"
            }
    
    async def fill(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        填充输入框
        
        Args:
            parameters: 应包含selector和text字段，以及可选的delay字段
            
        Returns:
            填充结果
        """
        selector = parameters.get('selector')
        text = parameters.get('text')
        
        if not selector:
            return {"status": "error", "message": "缺少selector参数"}
        if text is None:
            return {"status": "error", "message": "缺少text参数"}
        
        delay = parameters.get('delay', 0.1)  # 默认输入延迟0.1秒
        
        try:
            logger.info(f"填充选择器: {selector}")
            
            result = await self.session.fill(selector, text, delay=delay)
            
            if result:
                return {
                    "status": "success",
                    "message": f"成功填充 {selector}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"填充 {selector} 失败"
                }
        except Exception as e:
            logger.error(f"填充选择器 {selector} 时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"填充失败: {str(e)}"
            }
    
    async def extract_element_text(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取元素文本
        
        Args:
            parameters: 应包含selector字段和可选的default字段
            
        Returns:
            提取结果
        """
        selector = parameters.get('selector')
        if not selector:
            return {"status": "error", "message": "缺少selector参数"}
        
        default = parameters.get('default', "")
        
        try:
            logger.info(f"提取选择器文本: {selector}")
            
            text = await self.session.get_text(selector) or default
            
            return {
                "status": "success",
                "message": f"成功提取文本",
                "text": text
            }
        except Exception as e:
            logger.error(f"提取选择器 {selector} 文本时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"提取文本失败: {str(e)}",
                "text": default
            }
    
    async def extract_elements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取多个元素的信息
        
        Args:
            parameters: 应包含selectors字段，是一个字典，键为名称，值为选择器
            
        Returns:
            提取结果
        """
        selectors = parameters.get('selectors', {})
        if not selectors:
            return {"status": "error", "message": "缺少selectors参数"}
        
        try:
            logger.info(f"提取元素信息: {selectors}")
            
            results = {}
            
            # 使用提供的选择器提取信息
            for key, selector in selectors.items():
                try:
                    text = await self.session.get_text(selector)
                    if text:
                        results[key] = text.strip()
                except Exception as e:
                    logger.warning(f"提取 {key} ({selector}) 时出错: {str(e)}")
                    results[key] = None
            
            return {
                "status": "success",
                "message": "成功提取元素信息",
                "results": results
            }
        except Exception as e:
            logger.error(f"提取元素信息时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"提取元素信息失败: {str(e)}"
            }
    
    async def execute_script(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行JavaScript脚本
        
        Args:
            parameters: 应包含script字段，以及可选的args字段
            
        Returns:
            执行结果
        """
        script = parameters.get('script')
        if not script:
            return {"status": "error", "message": "缺少script参数"}
        
        args = parameters.get('args', [])
        
        try:
            logger.info("执行JavaScript脚本")
            
            result = await self.session.execute_script(script, *args)
            
            return {
                "status": "success",
                "message": "成功执行脚本",
                "result": result
            }
        except Exception as e:
            logger.error(f"执行脚本时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"执行脚本失败: {str(e)}"
            }
    
    async def take_screenshot(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        截图
        
        Args:
            parameters: 可选的path字段
            
        Returns:
            截图结果
        """
        path = parameters.get('path')
        
        try:
            logger.info("拍摄页面截图")
            
            screenshot_path = await self.session.screenshot(path=path)
            
            return {
                "status": "success",
                "message": "成功截图",
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            logger.error(f"截图时出错: {str(e)}")
            return {
                "status": "error",
                "message": f"截图失败: {str(e)}"
            }