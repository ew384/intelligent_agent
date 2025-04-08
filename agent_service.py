import os
import json
import asyncio
import logging
import requests
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from pathlib import Path
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig

# 导入各种处理器
from tool_service.src.tools.handlers.tax_handler import TaxHandler
# 以下是示例导入，实际使用时需要实现这些处理器
# from education_handler import EducationHandler
# from housing_fund_handler import HousingFundHandler
# from jd_handler import JDHandler
# from wechat_handler import WeChatHandler

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HandlerRegistry:
    """处理器注册表，用于管理和获取不同类型的处理器"""
    
    def __init__(self):
        """初始化处理器注册表"""
        self.handlers = {}
        self.instances = {}
        
    def register(self, handler_name: str, handler_class: Type):
        """注册处理器类"""
        self.handlers[handler_name] = handler_class
        logger.info(f"注册处理器: {handler_name}")
    
    def get_handler(self, handler_name: str, browser_context):
        """获取处理器实例"""
        if handler_name not in self.handlers:
            raise ValueError(f"未知的处理器类型: {handler_name}")
        
        # 如果实例不存在，创建新实例
        if handler_name not in self.instances:
            handler_class = self.handlers[handler_name]
            self.instances[handler_name] = handler_class(browser_context)
            logger.info(f"创建处理器实例: {handler_name}")
        
        return self.instances[handler_name]
    
    def cleanup_all(self):
        """清理所有处理器实例"""
        for name, instance in self.instances.items():
            if hasattr(instance, 'cleanup'):
                asyncio.create_task(instance.cleanup())
        self.instances = {}
        logger.info("清理所有处理器实例")

class GeneralHandler:
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
            # 例如使用Claude或其他模型来理解页面内容
            
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

class UniversalAgent:
    """
    通用Agent，集成Claude API与各种处理器，处理各类网络任务。
    负责处理对话流程并将Claude的响应转换为操作。
    """
    
    def __init__(self, claude_api_url: str, api_key: str, tab_id: str = None):
        """
        初始化助手
        
        参数:
            claude_api_url: Claude API的URL
            api_key: API密钥
        """
        self.claude_api_url = claude_api_url
        self.tab_id = tab_id
        self.api_key = api_key
        self.chat_history = []
        self.browser = None
        self.browser_context = None
        self.conversation_id = None
        
        # 初始化处理器注册表
        self.handler_registry = HandlerRegistry()
        
        # 注册各种处理器
        self.handler_registry.register("TaxHandler", TaxHandler)
        self.handler_registry.register("GeneralHandler", GeneralHandler)
        # 注册其他处理器（示例，实际使用时需要实现）
        # self.handler_registry.register("EducationHandler", EducationHandler)
        # self.handler_registry.register("HousingFundHandler", HousingFundHandler)
        # self.handler_registry.register("JDHandler", JDHandler)
        # self.handler_registry.register("WeChatHandler", WeChatHandler)
    
    async def initialize_browser(self, chrome_debug_port=54805):
        """初始化浏览器和上下文，连接到已有的Chrome实例"""
        logger.info("初始化浏览器，连接到已有的Chrome实例...")
        
        # 配置连接到已有的Chrome
        browser_config = BrowserConfig(
            cdp_url=f"http://localhost:{chrome_debug_port}"
        )
        
        # 创建Browser实例
        self.browser = Browser(config=browser_config)

        
        # 创建BrowserContext
        self.browser_context = BrowserContext(browser=self.browser)
        # 创建BrowserContext
        
        # 初始化会话
        await self.browser_context._initialize_session()
        
        logger.info("浏览器和上下文初始化完成，已连接到Chrome实例")
    
    async def cleanup(self):
        """清理资源"""
        self.handler_registry.cleanup_all()
        
        if self.browser_context:
            await self.browser_context.close()
        
        if self.browser:
            await self.browser.close()
        
        logger.info("资源清理完成")
    
    def format_state_for_claude(self, state: Dict[str, Any]) -> str:
        """
        格式化当前状态信息供Claude使用
        
        参数:
            state: 当前状态信息
            
        返回:
            格式化的状态文本
        """
        formatted_text = "[当前状态开始]\n"
        
        if "url" in state:
            formatted_text += f"当前URL: {state['url']}\n"
        
        if "elements_count" in state:
            formatted_text += f"交互元素数量: {state['elements_count']}\n"
        
        # 添加状态和消息信息
        if "status" in state:
            status = "✅ 成功" if state["status"] == "success" else "❌ 错误"
            formatted_text += f"状态: {status}\n"
        
        if "message" in state:
            formatted_text += f"消息: {state['message']}\n"
            
        # 添加可能有用的额外细节
        for key, value in state.items():
            if key not in ["url", "elements_count", "status", "message"]:
                formatted_text += f"{key}: {value}\n"
        
        formatted_text += "[当前状态结束]"
        return formatted_text
    
    def query_claude(self, message: str, is_new_chat: bool = False) -> Dict[str, Any]:
        """
        向Claude API发送查询
        
        参数:
            message: 要发送的消息
            is_new_chat: 是否开始新对话
            
        返回:
            Claude的响应
        """
        try:
            payload = {
                "tab-id": self.tab_id,
                "prompt": message,
                "file_paths": None,
                "new_chat": is_new_chat
            }

            response = requests.post(
                self.claude_api_url,
                headers=self.api_key,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"API错误: {response.status_code}, {response.text}")
                return {"error": f"API错误: {response.status_code}"}
            
            response_data = response.json()
            # 存储对话ID（如果是新对话）
            if is_new_chat and "conversation_id" in response_data:
                self.conversation_id = response_data["conversation_id"]
                
            return response_data
        
        except Exception as e:
            logger.error(f"查询Claude API时出错: {str(e)}")
            return {"error": str(e)}
    
    def extract_action(self, claude_response: str) -> Optional[Dict[str, Any]]:
        """
        从Claude的响应中提取动作细节
        
        参数:
            claude_response: Claude的格式化响应
            
        返回:
            提取的动作或None（如果解析失败）
        """
        try:
            # 查找响应中的JSON
            start_index = claude_response.find("{")
            end_index = claude_response.rfind("}")
            
            if start_index == -1 or end_index == -1:
                logger.warning("Claude的响应中未找到JSON")
                return None
            
            json_str = claude_response[start_index:end_index+1]
            action_data = json.loads(json_str)
            
            # 验证必需字段
            if "current_state" not in action_data or "action" not in action_data:
                logger.warning(f"动作数据中缺少必需字段: {action_data}")
                return None
                
            return action_data
        except json.JSONDecodeError as e:
            logger.error(f"解析动作JSON失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"提取动作时出错: {str(e)}")
            return None
    
    async def execute_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指定的动作
        
        参数:
            action_data: 来自Claude的动作详情
            
        返回:
            动作结果
        """
        if not action_data or "action" not in action_data:
            return {"status": "error", "message": "无效的动作数据"}
        
        # 获取指定的处理器类型
        handler_name = action_data.get("handler", "GeneralHandler")
        actions = action_data["action"]
        
        if not actions:
            return {"status": "error", "message": "未指定动作"}
        
        # 获取处理器实例
        try:
            handler = self.handler_registry.get_handler(handler_name, self.browser_context)
        except ValueError as e:
            logger.error(str(e))
            # 如果指定的处理器不存在，使用通用处理器
            handler = self.handler_registry.get_handler("GeneralHandler", self.browser_context)
        
        results = []
        
        for action in actions:
            # 获取第一个键作为动作名称
            action_name = list(action.keys())[0]
            action_params = action[action_name]
            
            logger.info(f"执行动作: {action_name}, 参数: {action_params}, 使用处理器: {handler_name}")
            
            # 处理"done"动作
            if action_name == "done":
                success = action_params.get("success", False)
                text = action_params.get("text", "任务完成")
                
                results.append({
                    "status": "success" if success else "partial",
                    "message": text,
                    "is_done": True,
                    "task_success": success
                })
                continue
            
            # 将动作参数传递给处理器
            try:
                action_result = await handler.process_query({
                    "action": action_name,
                    **action_params  # 展开动作参数
                })
                results.append(action_result)
            except Exception as e:
                results.append({
                    "status": "error",
                    "message": f"执行动作失败: {str(e)}"
                })
        
        # 返回最后一个结果，或者组合结果
        return results[-1] if results else {"status": "error", "message": "未执行任何动作"}

    async def process_user_request(self, user_request: str) -> str:
        """
        从始至终处理用户请求
        
        参数:
            user_request: 用户的请求
            
        返回:
            给用户的最终响应
        """
        try:
            # 如果尚未初始化浏览器，则初始化
            if not self.browser or not self.browser_context:
                await self.initialize_browser()
            
            # 包含任务信息的初始系统消息
            # 从文件加载系统提示
            system_prompt_path = Path("universal_system_prompt.md")
            if system_prompt_path.exists():
                with open(system_prompt_path, "r", encoding="utf-8") as f:
                    system_message = f.read()
            else:
                system_message = """你是一个AI助手，负责帮助用户完成各种在线任务。你将分析用户的请求，决定使用哪个功能处理器，并确定接下来要执行的操作。

请用JSON格式响应，包含current_state、handler和action字段。

用户请求: """
            
            system_message = system_message + "\n\n用户请求: " + user_request
            
            # 启动与Claude的对话
            logger.info(f"开始处理用户请求: {user_request}")
            response = self.query_claude(system_message, is_new_chat=True)
            
            if "error" in response:
                return f"开始对话时出错: {response['error']}"
            
            # 提取Claude的响应
            claude_message = response['messages'][-1]['content']
            print(claude_message)
            action_data = self.extract_action(claude_message)
            
            if not action_data:
                return "无法解析助手的初始响应。"
            
            # 执行动作并继续对话直到完成
            is_done = False
            step_count = 0
            final_result = None
            
            while not is_done and step_count < 15:  # 限制为15步以防止无限循环
                step_count += 1
                logger.info(f"执行步骤 {step_count}")
                
                # 执行动作
                result = await self.execute_action(action_data)
                is_done = result.get("is_done", False)
                final_result = result
                
                # 如果完成，跳出循环
                if is_done:
                    logger.info(f"任务完成，结果: {result}")
                    break
                
                # 为Claude格式化结果状态
                state_message = self.format_state_for_claude(result)
                
                # 从Claude生成下一个动作
                next_prompt = f"""以下是您上次动作的结果:

{state_message}

基于此结果，下一步应该执行什么动作来完成用户的请求: "{user_request}"？

请记住使用有效的JSON对象，遵循要求的格式，并选择合适的handler。"""
                
                response = self.query_claude(next_prompt, is_new_chat=False)
                
                if "error" in response:
                    return f"对话过程中出错: {response['error']}"
                
                # 提取Claude的下一个响应
                claude_message = response['messages'][-1]['content']
                action_data = self.extract_action(claude_message)
                
                if not action_data:
                    return f"无法在步骤{step_count}解析助手响应。"
            
            # 给用户的最终响应
            if is_done:
                summary = final_result.get("message", "任务完成")
                success = final_result.get("task_success", False)
                status = "成功" if success else "未完全完成"
                
                return f"您的请求已{status}处理。{summary}"
            else:
                return "由于步骤过多，无法完成您的请求。请尝试更具体的指令或联系客服人员。"
        
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            return f"处理请求时出错: {str(e)}"
        finally:
            # 除非明确要求，否则不清理资源
            # 这样可以让浏览器保持打开状态以便查看
            pass

# 示例用法
async def main():
    claude_api_url = "http://localhost:8005/chat/claude"
    user_api_key={"api-key": "wangendian"}
    response = requests.post(
        "http://localhost:8005/tabs",
        headers=user_api_key,
        json={"provider": "claude"}
    )
    tab_id = response.json()["tab_id"]
    agent = UniversalAgent(claude_api_url, user_api_key, tab_id)
    
    try:
        while True:
            user_request = input("\n请输入您的请求 (输入'退出'结束): ")
            if user_request.lower() in ['退出', 'exit', 'quit']:
                break
                
            print("-" * 80)
            response = await agent.process_user_request(user_request)
            print(f"最终响应: {response}")
    finally:
        await agent.cleanup()
if __name__ == "__main__":
    asyncio.run(main())