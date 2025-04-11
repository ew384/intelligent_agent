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
from tool_service.src.tools.handlers.social_security_handler import SocialSecurityHandler
from tool_service.src.tools.handlers.base import BaseHandler
# 以下是示例导入，实际使用时需要实现这些处理器
# from education_handler import EducationHandler
# from jd_handler import JDHandler
# from wechat_handler import WeChatHandler

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        logger.info(f"当前注册的处理器: {list(self.handlers.keys())}")
        logger.info(f"尝试获取处理器: {handler_name}")
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


class UniversalAgent:
    """
    通用Agent，集成LLM API与各种处理器，处理各类网络任务。
    负责处理对话流程并将LLM的响应转换为操作。
    """
    
    def __init__(self, LLM_api_url: str, api_key: str, tab_id: str = None):
        """
        初始化助手
        
        参数:
            LLM_api_url: LLM API的URL
            api_key: API密钥
        """
        self.LLM_api_url = LLM_api_url
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
        self.handler_registry.register("SocialSecurityHandler", SocialSecurityHandler)
        self.handler_registry.register("BaseHandler", BaseHandler)
        # 在导入之后添加
        #logger.info(f"SocialSecurityHandler imported successfully: {SocialSecurityHandler}")
        # 注册其他处理器（示例，实际使用时需要实现）
        # self.handler_registry.register("EducationHandler", EducationHandler)
        # self.handler_registry.register("HousingFundHandler", HousingFundHandler)
        # self.handler_registry.register("JDHandler", JDHandler)
        # self.handler_registry.register("WeChatHandler", WeChatHandler)
    
    async def initialize_browser(self, chrome_debug_port=54905):
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
    
    def format_state_for_LLM(self, state: Dict[str, Any]) -> str:
        """
        格式化当前状态信息供LLM使用，确保不截断关键信息
        """
        formatted_text = "[当前状态开始]\n"
        
        if "url" in state:
            formatted_text += f"当前URL: {state['url']}\n"
        
        if "title" in state:
            formatted_text += f"页面标题: {state['title']}\n"
        
        if "elements_count" in state:
            formatted_text += f"交互元素数量: {state['elements_count']}\n"
        
        # 添加状态和消息信息
        if "status" in state:
            status = "✅ 成功" if state["status"] == "success" else "❌ 错误"
            formatted_text += f"状态: {status}\n"
        
        if "message" in state:
            formatted_text += f"消息: {state['message']}\n"
        
        # 特别标注新标签页创建信息
        if state.get("new_tab_created", False):
            formatted_text += f"⚠️ 提示: 点击操作创建了新标签页\n"
            if "new_tab_id" in state:
                formatted_text += f"新标签页ID: {state['new_tab_id']}\n"
        
        # 对于found_elements这类关键数据，完整传递而不截断
        if "found_elements" in state:
            formatted_text += f"找到的元素: {json.dumps(state['found_elements'], ensure_ascii=False)}\n"
        
        # 添加可能有用的额外细节，不截断关键操作数据
        for key, value in state.items():
            if key not in ["url", "title", "elements_count", "status", "message", "found_elements", 
                        "new_tab_created", "new_tab_id"]:
                # 保留更多的文本块信息
                if key == "text_blocks":
                    formatted_text += f"{key}: {json.dumps(value[:20], ensure_ascii=False)}\n"
                # 对于其他大型数据，适当截断但保留更多内容
                elif isinstance(value, dict) or isinstance(value, list):
                    formatted_text += f"{key}: {json.dumps(value, ensure_ascii=False)[:1000]}...\n"
                else:
                    formatted_text += f"{key}: {value}\n"
        
        formatted_text += "[当前状态结束]"
        return formatted_text
    
    def query_LLM(self, message: str, is_new_chat: bool = False) -> Dict[str, Any]:
        """
        向LLM API发送查询
        
        参数:
            message: 要发送的消息
            is_new_chat: 是否开始新对话
            
        返回:
            LLM的响应
        """
        try:
            payload = {
                "tab-id": self.tab_id,
                "prompt": message,
                "file_paths": None,
                "new_chat": is_new_chat
            }

            response = requests.post(
                self.LLM_api_url,
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
            logger.error(f"查询LLM API时出错: {str(e)}")
            return {"error": str(e)}
    
    def extract_action(self, LLM_response: str) -> Optional[Dict[str, Any]]:
        """
        从LLM的响应中提取动作细节
        
        参数:
            LLM_response: LLM的格式化响应
            
        返回:
            提取的动作或None（如果解析失败）
        """
        try:
            # 查找响应中的JSON
            print(LLM_response)
            start_index = LLM_response.find("{")
            end_index = LLM_response.rfind("}")
            
            if start_index == -1 or end_index == -1:
                logger.warning("LLM的响应中未找到JSON")
                return None
            
            json_str = LLM_response[start_index:end_index+1]
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
            action_data: 来自LLM的动作详情
            
        返回:
            动作结果
        """
        if not action_data or "action" not in action_data:
            return {"status": "error", "message": "无效的动作数据"}
        
        # 获取指定的处理器类型
        handler_name = action_data.get("handler", "BaseHandler")
        actions = action_data["action"]
        
        if not actions:
            return {"status": "error", "message": "未指定动作"}
        
        # 获取处理器实例
        try:
            handler = self.handler_registry.get_handler(handler_name, self.browser_context)
        except ValueError as e:
            logger.error(str(e))
            # 如果指定的处理器不存在，使用通用处理器
            handler = self.handler_registry.get_handler("BaseHandler", self.browser_context)
        
        results = []
        new_tab_created = False  # 跟踪是否有新标签页被创建
        
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
                
            # 处理新增的用户交互请求操作
            if action_name == "request_user_action":
                action_type = action_params.get("type", "generic")
                message = action_params.get("message", "请执行操作")
                description = action_params.get("description", "")
                options = action_params.get("options", [])
                
                # 显示给用户的消息
                print("\n" + "-" * 50)
                print(f"⚠️ 需要用户操作: {message}")
                if description:
                    print(f"📝 说明: {description}")
                if options:
                    print("🔢 可选操作:")
                    for i, option in enumerate(options, 1):
                        print(f"  {i}. {option}")
                print("\n⏳ 请在浏览器中完成操作，然后按Enter键继续...")
                
                # 等待用户确认操作完成
                input()
                
                # 用户确认完成后，获取当前页面状态
                current_state = await self.browser_context.get_state()
                
                results.append({
                    "status": "success",
                    "message": f"用户已完成{action_type}操作",
                    "user_action_type": action_type,
                    "url": current_state.url,
                    "title": current_state.title,
                    "elements_count": len(current_state.selector_map) if current_state.selector_map else 0
                })
                continue
                
            # 处理评估状态操作
            if action_name == "evaluate_state":
                description = action_params.get("description", "评估当前状态")
                
                # 获取当前页面状态
                current_state = await self.browser_context.get_state()
                
                results.append({
                    "status": "success",
                    "message": f"状态评估: {description}",
                    "url": current_state.url,
                    "title": current_state.title,
                    "elements_count": len(current_state.selector_map) if current_state.selector_map else 0
                })
                continue
            
            # 将动作参数传递给处理器
            try:
                action_result = await handler.process_query({
                    "action": action_name,
                    **action_params  # 展开动作参数
                })
                
                # 检查是否有新标签页被创建
                if action_result.get("new_tab_created", False):
                    new_tab_created = True
                    logger.info(f"检测到新标签页被创建并已切换: {action_result.get('new_tab_id', 'unknown')}")
                
                results.append(action_result)
            except Exception as e:
                results.append({
                    "status": "error",
                    "message": f"执行动作失败: {str(e)}"
                })
        
        # 在结果中添加标签页创建信息
        final_result = results[-1] if results else {"status": "error", "message": "未执行任何动作"}
        if new_tab_created and "new_tab_created" not in final_result:
            final_result["new_tab_created"] = True
        
        return final_result

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
            
            # 启动与LLM的对话
            logger.info(f"开始处理用户请求: {user_request}")
            response = self.query_LLM(system_message, is_new_chat=True)
            
            if "error" in response:
                return f"开始对话时出错: {response['error']}"
            
            # 提取LLM的响应
            LLM_message = response['messages'][-1]['content']["response"]
            LLM_action = response['messages'][-1]['content']["codeBlocks"][-1]['code']
            print(LLM_message)
            action_data = self.extract_action(LLM_action)
            
            if not action_data:
                return "无法解析助手的初始响应。"
            
            # 执行动作并继续对话直到完成
            is_done = False
            step_count = 0
            final_result = None
            
            while not is_done and step_count < 20:  # 增加步骤限制以允许更多交互
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
                
                # 为LLM格式化结果状态
                state_message = self.format_state_for_LLM(result)
                
                # 判断是否刚刚完成了用户交互
                user_interaction_completed = "user_action_type" in result
                
                # 从LLM生成下一个动作
                if user_interaction_completed:
                    next_prompt = f"""用户已完成交互操作，当前状态如下:

{state_message}

请分析当前状态，确定下一步操作。基于用户刚刚的交互，现在应该执行什么操作来继续完成用户的请求: "{user_request}"？

请注意操作的正确顺序：
1. 搜索信息时，先点击搜索框，然后输入文本，最后点击搜索按钮
2. 使用具体的元素索引号，而不是使用-1这样的通用索引
3. 每个操作后添加适当的等待时间
4. 使用有效的JSON对象，遵循要求的格式，并选择合适的handler"""
                else:
                    next_prompt = f"""以下是您上次动作的结果:

{state_message}

基于此结果，下一步应该执行什么动作来完成用户的请求: "{user_request}"？

请记住：
1. 使用合理的操作顺序：对于搜索功能，应先点击搜索框，然后输入文本，最后点击搜索按钮
2. 使用highlight_elements后，可以看到每个元素都有索引编号，请使用这些具体的索引编号
3. 如果遇到需要登录、选择或输入敏感信息的情况，使用request_user_action操作让用户手动操作
4. 确保每个操作后都等待适当时间以确保页面响应
5. 使用有效的JSON对象，遵循要求的格式，并选择合适的handler

执行搜索时，如果页面包含一个搜索框和一个搜索按钮，请先对搜索框执行click_element，然后对同一索引执行input_text，最后对搜索按钮执行click_element。"""
                
                response = self.query_LLM(next_prompt, is_new_chat=False)
                
                if "error" in response:
                    return f"对话过程中出错: {response['error']}"
                
                # 提取LLM的下一个响应
                try:
                    LLM_message = response['messages'][-1]['content']["response"]
                except:
                    LLM_message="No Response"
                try:
                    LLM_action = response['messages'][-1]['content']["codeBlocks"][-1]['code']
                except:
                    LLM_action=None
                print(LLM_message)
                if LLM_action==None:
                    return f"步骤{step_count}没有提供动作"
                action_data = self.extract_action(LLM_action)
                
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
    LLM={"provider": "claude"}
    LLM_api_url = f"http://localhost:8005/chat/{LLM["provider"]}"
    user_api_key={"api-key": "wangendian"}
    response = requests.post(
        "http://localhost:8005/tabs",
        headers=user_api_key,
        json=LLM
    )
    tab_id = response.json()["tab_id"]
    agent = UniversalAgent(LLM_api_url, user_api_key, tab_id)
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