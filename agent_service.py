import os
import json
import asyncio
import logging
import requests
import re
import string
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
from pathlib import Path
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig

# 导入工作流引擎
from tool_service.src.tools.workflow.engine import WorkflowEngine

# 导入基础处理器
from tool_service.src.tools.handlers.base import BaseHandler

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UniversalAgent:
    """
    通用Agent，集成LLM API与工作流引擎，处理各类网络任务。
    负责处理对话流程并将LLM的响应转换为操作。
    """
    
    def __init__(self, LLM_api_url: str, user_api_key: Dict[str, Any]):
        """
        初始化助手
        
        参数:
            LLM_api_url: LLM API的URL
            api_key: API密钥
        """
        self.LLM_api_url = LLM_api_url
        self.user_api_key = user_api_key
        self.chat_history = []
        self.browser = None
        self.browser_context = None
        self.conversation_id = None
        
        # 初始化工作流引擎
        self.workflow_engine = WorkflowEngine()
        
        # 初始化基础处理器
        self.base_handler = None
    
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
        
        # 初始化会话
        await self.browser_context._initialize_session()
        
        # 初始化基础处理器
        self.base_handler = BaseHandler(self.browser_context)
        
        # 更新工作流引擎中的浏览器上下文
        self.workflow_engine.set_browser_context(self.browser_context)
        
        logger.info("浏览器和上下文初始化完成，已连接到Chrome实例")
    
    async def cleanup(self):
        """清理资源"""
        if self.base_handler:
            await self.base_handler.cleanup()
        
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
    
    def query_LLM(self, message: str, agent_api_key: Dict, is_new_chat: bool = False, ) -> Dict[str, Any]:
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
                "tab-id": agent_api_key['tab_id'],
                "prompt": message,
                "file_paths": None,
                "new_chat": is_new_chat
            }

            response = requests.post(
                self.LLM_api_url,
                headers={'api-key':agent_api_key['api_key']},
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"API错误: {response.status_code}, {response.text}")
                return {"error": f"API错误: {response.status_code}"}
            
            response_data = response.json()
            # 存储对话ID（如果是新对话）
            if is_new_chat and "conversation_id" in response_data:
                self.conversation_id = response_data["conversation_id"]
                
            return response_data['messages'][-1]['content']
        
        except Exception as e:
            logger.error(f"查询LLM API时出错: {str(e)}")
            return {"error": str(e)}
    
    def save_action_data_to_file(self, action_data, directory="workflows"):
        """
        将action_data保存到本地文件
        
        参数:
            action_data: 要保存的数据
            directory: 保存文件的目录，默认为'action_data'
        
        返回:
            保存的文件路径
        """
        try:
            # 确保目录存在
            Path(directory).mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            file_name = f"{action_data['id']}_{action_data['version']}.json"
            file_path = os.path.join(directory, file_name)
            
            # 将数据转换为JSON字符串，并格式化为美观的输出
            json_content = json.dumps(action_data, ensure_ascii=False, indent=2)
            
            # 将内容写入到文件中
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(json_content)
            
            print(f"✅ 成功保存action_data到文件: {file_path}")
            return file_path
            
        except KeyError as e:
            print(f"❌ 错误: action_data缺少必要的键: {e}")
            return None
        except Exception as e:
            print(f"❌ 保存文件时发生错误: {str(e)}")
            return None

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
            print(json_str)
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

        actions = action_data["action"]
        
        if not actions:
            return {"status": "error", "message": "未指定动作"}
        
        results = []
        new_tab_created = False  # 跟踪是否有新标签页被创建
        
        for action in actions:
            # 获取第一个键作为动作名称
            action_name = list(action.keys())[0]
            action_params = action[action_name]
            
            logger.info(f"执行动作: {action_name}, 参数: {action_params}")
            
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
                action_result = await self.base_handler.process_query({
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
    
    def analyze_workflow_match(self, user_request: str) -> Dict[str, Any]:
        """
        分析用户请求是否匹配工作流程关键词
        只有当所有关键词都在用户请求中时，才返回匹配结果
        
        Args:
            user_request: 用户的请求文本
                
        Returns:
            Dict 包含匹配结果，如果匹配则返回workflow_id、workflow_info、workflow_name、workflow_description和置信度，否则返回空dict
        """
        result = {}
        
        # 确保用户请求不为空
        if not user_request or not isinstance(user_request, str):
            logger.warning("用户请求为空或格式不正确")
            return result
        
        # 标准化用户请求文本（转为小写，去除多余空格等）
        normalized_request = user_request.lower().strip()
        
        # 获取所有工作流信息
        all_workflows = self.workflow_engine.get_all_workflows_info()
        matching_workflows = []
        
        # 遍历所有工作流程
        for workflow_info in all_workflows:
            workflow_id = workflow_info["id"]
            workflow_name = workflow_info["name"]
            workflow_description = workflow_info["description"]
            
            # 获取完整的工作流定义以访问keywords
            workflow = self.workflow_engine.get_workflow_by_id(workflow_id)
            
            # 检查工作流是否有keywords字段
            if not workflow or "keywords" not in workflow:
                continue
                
            # 获取关键词
            keywords = workflow.get("keywords", [])
            if not keywords:
                continue
            
            # 检查所有关键词是否都在用户请求中
            all_keywords_match = True
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in normalized_request:
                    matched_keywords.append(keyword)
                else:
                    all_keywords_match = False
                    break
            
            # 只有当所有关键词都匹配时才添加到匹配列表
            if all_keywords_match and matched_keywords:
                matching_workflows.append({
                    "workflow_id": workflow_id,
                    "workflow_info": workflow_info,
                    "workflow_name": workflow_name,
                    "workflow_description": workflow_description,
                    "confidence": 1.0,  # 完全匹配时置信度为1.0
                    "matched_keywords": matched_keywords
                })
        
        # 如果有匹配的工作流，选择第一个（因为所有匹配的工作流都是完全匹配的）
        if matching_workflows:
            best_match = matching_workflows[0]
            workflow_id = best_match["workflow_id"]
            workflow_name = best_match["workflow_name"]
            matched_keywords = best_match["matched_keywords"]
            logger.info(f"找到完全匹配的工作流: {workflow_id} ({workflow_name}), 匹配关键词: {', '.join(matched_keywords)}")
            return best_match
        
        return result

    def format_workflow_status_for_LLM(self, workflow_result: Dict[str, Any], current_state) -> str:
        """
        将工作流执行状态格式化为LLM可理解的文本格式
        
        参数:
            workflow_result: 工作流执行结果
            current_state: 当前页面状态
            
        返回:
            格式化的文本
        """
        formatted_text = "[工作流执行状态开始]\n"
        
        # 添加工作流基本信息
        formatted_text += f"工作流名称: {workflow_result.get('workflow_name', '未知')}\n"
        formatted_text += f"工作流ID: {workflow_result.get('workflow_id', '未知')}\n"
        formatted_text += f"执行的动作ID: {workflow_result.get('action_id', '未知')}\n"
        
        # 添加完成度信息
        completed_percentage = workflow_result.get("completed_percentage", 0)
        formatted_text += f"完成度: {completed_percentage}%\n"
        
        # 添加执行状态
        status = "✅ 成功" if workflow_result.get("status") == "success" else "❌ 失败"
        formatted_text += f"当前状态: {status}\n"
        
        if "message" in workflow_result:
            formatted_text += f"状态消息: {workflow_result['message']}\n"
        
        # 添加已执行步骤
        executed_steps = workflow_result.get("executed_steps", [])
        if executed_steps:
            formatted_text += "\n## 已执行的步骤:\n"
            for i, step in enumerate(executed_steps, 1):
                step_id = step.get("step_id", f"步骤{i}")
                action = step.get("action", "未知操作")
                description = step.get("description", "")
                step_status = "✅ 成功" if step.get("status") == "success" else "❌ 失败"
                
                formatted_text += f"{i}. [{step_status}] {step_id}: {action} - {description}\n"
                
                # 添加步骤的详细信息（如果有）
                if "details" in step:
                    formatted_text += f"   详情: {step['details']}\n"
        
        # 添加剩余任务
        remaining_tasks = workflow_result.get("remaining_tasks", [])
        if remaining_tasks:
            formatted_text += "\n## 剩余任务:\n"
            for i, task in enumerate(remaining_tasks, 1):
                step_id = task.get("step_id", f"步骤{i}")
                action = task.get("action", "未知操作")
                description = task.get("description", "")
                
                formatted_text += f"{i}. {step_id}: {action} - {description}\n"
        
        # 添加当前页面状态
        if current_state:
            formatted_text += "\n## 当前页面状态:\n"
            if hasattr(current_state, 'url'):
                formatted_text += f"URL: {current_state.url}\n"
            if hasattr(current_state, 'title'):
                formatted_text += f"标题: {current_state.title}\n"
            if hasattr(current_state, 'selector_map'):
                formatted_text += f"可交互元素数量: {len(current_state.selector_map) if current_state.selector_map else 0}\n"
        
        formatted_text += "\n[工作流执行状态结束]"
        return formatted_text


    async def process_user_request(self, user_request: str) -> str:
        """
        从始至终处理用户请求，自动检测是否可以使用预定义工作流
        
        参数:
            user_request: 用户的请求
            
        返回:
            给用户的最终响应
        """
        try:
            # 如果尚未初始化浏览器，则初始化
            if not self.browser or not self.browser_context:
                await self.initialize_browser()
            self.workflow_engine.load_workflows()
            # 使用LLM分析是否有匹配的预定义工作流
            if self.workflow_engine.workflows:
                print(f"🔍 分析请求是否匹配预定义工作流...")
                match_result = self.analyze_workflow_match(user_request)
                
                if len(match_result) and "workflow_id" in match_result:
                    print(match_result)
                    print("*"*30)
                    workflow_id = match_result["workflow_id"]
                    print(workflow_id)
                    matched_workflow = self.workflow_engine.workflows.get(workflow_id)
                    
                    if matched_workflow:
                        confidence = match_result.get("confidence", 0)
                        logger.info(f"找到匹配的工作流: {matched_workflow['name']} (ID: {workflow_id}), 置信度: {confidence}")
                        print(f"💡 检测到请求匹配预定义工作流: {matched_workflow['name']}")

                        # 获取指定的操作或默认操作（通常是第一个操作）
                        action_id = match_result.get("action_id")
                        action_to_execute = None
                        
                        if action_id:
                            # 查找指定的操作
                            for action in matched_workflow.get("action", []):
                                if action.get("id") == action_id:
                                    action_to_execute = action
                                    break
                        
                        # 如果未找到指定操作或未指定操作，使用第一个操作
                        if not action_to_execute and matched_workflow.get("action") and len(matched_workflow["action"]) > 0:
                            action_to_execute = matched_workflow["action"][0]
                        
                        if action_to_execute:
                            # 执行工作流
                            print(f"⚙️ 执行工作流: {matched_workflow['name']}.{action_to_execute['id']}")
                            workflow_result = await self.workflow_engine.execute_workflow(workflow_id, action_to_execute['id'])
                            
                            # 如果工作流执行成功并完成，则直接返回结果
                            if workflow_result.get("is_done", False) and workflow_result.get("task_success", False):
                                success = workflow_result.get("task_success", False)
                                message = workflow_result.get("message", "任务完成")
                                status = "成功" if success else "未完全完成"
                                return f"您的请求已{status}处理。{message}"
                else:
                    print(f"没有找到匹配用户query的预定义工作流")        
            print("请求LLM-Agent规划")
            # 从文件加载系统提示
            system_prompt_path = Path("universal_system_prompt.md")
            try:
                with open(system_prompt_path, "r", encoding="utf-8") as f:
                    system_message = f.read()
            except Exception as e:
                logger.error(f"读取system_prompt出错: {str(e)}")
                return f"读取system_prompt出错: {str(e)}"
            
            # 只有在使用了工作流执行且有工作流结果的情况下，才添加工作流状态信息
            if len(match_result) and action_to_execute and workflow_result:
                print(f"🔄 工作流部分执行 ({workflow_result.get('completed_percentage', 0)}%)，切换到LLM继续...")
                
                # 获取当前浏览器状态
                current_state = await self.browser_context.get_state()
                
                # 格式化工作流状态信息
                workflow_status = self.format_workflow_status_for_LLM(workflow_result, current_state)
                
                # 将工作流状态添加到系统提示
                system_message += "\n\n# 重要：\n<已执行的工作流状态>\n"
                system_message += workflow_status
                system_message += "\n</已执行的工作流状态>\n# 重要指导\n"
                system_message += "以上是一个预定义工作流的执行状态。工作流已经部分执行，但尚未完成用户的请求。\n"
                system_message += "请分析当前状态，了解已完成和未完成的部分，继续生成后续操作以完成用户请求。\n"
                system_message += "不要重新开始整个任务，而是继续从当前状态前进。\n"
                system_message += "请确保你的响应包含合适的JSON格式操作，遵循所需格式。\n"

            # 添加用户请求
            system_message += f"\n\n用户请求: {user_request}"
            
            # 启动与LLM的对话，传递工作流状态
            response = self.query_LLM(system_message, self.user_api_key['conversation'], is_new_chat=True)
            
            if "error" in response:
                return f"开始对话时出错: {response['error']}"
            
            # 提取LLM的响应
            try:
                LLM_message = response["response"][-1]
                LLM_action = response["codeBlocks"][-1]['code']
                print(LLM_message)
                action_data = self.extract_action(LLM_action)
            except Exception as e:
                print(response)
                logger.error(f"解析LLM响应失败: {str(e)}")
                return f"无法理解AI助手的回复，请重试或使用不同的表述。错误: {str(e)}"
            
            if not action_data:
                return "无法解析助手的初始响应。"
            
            # 执行LLM动作并继续对话直到完成
            is_done = False
            step_count = 0
            final_result = None
            
            while not is_done and step_count < 100:  # 增加步骤限制以允许更多交互
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
4. 使用有效的JSON对象，遵循要求的格式，并选择合适的处理方式
"""
                else:
                    next_prompt = f"""以下是您上次动作的结果:

{state_message}

基于此结果，下一步应该执行什么动作来完成用户的请求: "{user_request}"？

请记住：
1. 使用合理的操作顺序：对于搜索功能，应先点击搜索框，然后输入文本，最后点击搜索按钮
2. 如果遇到需要登录、选择或输入敏感信息的情况，使用request_user_action操作让用户手动操作
3. 确保每个操作后都等待适当时间以确保页面响应
4. 使用有效的JSON对象，遵循要求的格式

执行输入框点击输入文本并搜索的动作，请一定使用input_text_and_search"""
                
                response = self.query_LLM(next_prompt, self.user_api_key['conversation'], is_new_chat=False)
                
                if "error" in response:
                    return f"对话过程中出错: {response['error']}"
                
                # 提取LLM的下一个响应
                try:
                    LLM_message = response["response"][-1]
                    LLM_action = response["codeBlocks"][-1]['code']
                    print(LLM_message)
                    action_data = self.extract_action(LLM_action)
                except Exception as e:
                    print(response)
                    logger.error(f"解析LLM响应失败: {str(e)}")
                    return f"无法理解AI助手的回复，请重试或使用不同的表述。错误: {str(e)}"
                
                if not action_data:
                    return f"无法在步骤{step_count}解析助手响应。"
            
            # 给用户的最终响应
            if is_done:
                summary = final_result.get("message", "任务完成")
                success = final_result.get("task_success", False)
                status = "成功" if success else "未完全完成"
                response = self.query_LLM("stop", self.user_api_key['conversation'], is_new_chat=False)
                history_action=response['messages'][1:-1]
                try:
                    with open(Path("generate_workflow_prompt.md"), "r", encoding="utf-8") as f:
                        generate_workflow_prompt = f.read()
                except Exception as e:
                    logger.error(f"读取generate_workflow_prompt出错: {str(e)}")
                    return f"读取generate_workflow_prompt出错: {str(e)}"
                generate_workflow_prompt += f"""{history_action}
                </探索历史>
请生成一个简洁、有效的工作流程，去除所有失败的尝试和冗余步骤，确保每个步骤都具有明确的目的和正确的参数设置。
工作流应具有适当的元数据（如ID、名称、关键词），并且步骤顺序应保持逻辑连贯性。"""
                logger.info(f"生成探索历史的工作流")
                response = self.query_LLM(generate_workflow_prompt,self.user_api_key['summarization'], is_new_chat=True)
                try:
                    LLM_message = response["response"][-1]
                    LLM_action = response["codeBlocks"][-1]['code']
                    print(LLM_message)
                    action_data = self.extract_action(LLM_action)
                except Exception as e:
                    print(response)
                    logger.error(f"解析LLM响应失败: {str(e)}")
                    return f"无法理解AI助手的回复，请重试或使用不同的表述。错误: {str(e)}"
                action_data = self.extract_action(LLM_action)
                file_path=self.save_action_data_to_file(action_data)
                if file_path:
                    logger.info(f"保存工作流到文件: {file_path}")
                else:
                    logger.error("保存工作流到文件失败")                        
                return f"您的请求已{status}处理。{summary}"
            else:
                return "由于步骤过多，无法完成您的请求。请尝试更具体的指令或联系客服人员。"
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            return f"处理请求时出错: {str(e)}"
                        
async def main():
    LLM = {"provider": "claude"}
    LLM_api_url = f"http://localhost:8005/chat/{LLM['provider']}"
    user_api_key = {
        #"evaluation":{"api_key":"evaluation","tab_id":None},#评估可用的工作流的适配程度和组合修改
        "conversation":{"api_key":"conversation","tab_id":None},#主体agent评估探索每一步action
        "summarization":{"api_key":"summarization","tab_id":None} #历史探索生成可用工作流
    }
    for key in user_api_key.keys():
        response = requests.post(
            "http://localhost:8005/tabs",
            headers={"api-key": user_api_key[key]["api_key"]},
            json=LLM
        )
        tab_id = response.json()["tab_id"]
        user_api_key[key]["tab_id"]=tab_id
    agent = UniversalAgent(LLM_api_url,user_api_key)
    
    # 创建工作流目录（如果不存在）
    workflows_dir = Path("workflows")
    if not workflows_dir.exists():
        workflows_dir.mkdir(parents=True)
        print("创建工作流目录：workflows")
    
    try:
        print("\n" + "="*50)
        print("🤖 欢迎使用通用浏览器Agent")
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