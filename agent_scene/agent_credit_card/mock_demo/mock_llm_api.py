import json
import re
from typing import Dict, List, Any, Callable, Optional, Union
import random
import asyncio

class MockLLMResponseGenerator:
    """模拟大语言模型响应生成器"""
    
    def __init__(self, tools_modules=None):
        """
        初始化模拟LLM生成器
        
        Args:
            tools_modules: 可用工具模块字典，例如 {"spa_tools": spa_tools, "integrated_tools": integrated_tools}
        """
        self.tools_modules = tools_modules or {}
        
        # 预设回答模板 - 可以根据需要扩展
        self.response_templates = {
            "greeting": [
                "您好！我是中信银行信用卡分期经理，很高兴为您服务。请问有什么可以帮助您的吗？",
                "您好，我是中信银行的客户经理，很高兴为您服务。请告诉我您的分期需求，我将为您推荐最合适的方案。"
            ],
            "clarification": [
                "请问您是想了解哪种分期产品呢？我们有消费分期、账单分期和现金分期等多种选择。",
                "能否请您提供更多信息？例如您想分期的金额和期望的还款期限？"
            ],
            "recommendation": [
                "根据您的情况，我建议您选择{period}期分期，每月还款约{monthly_payment}元，总手续费为{fee_amount}元。",
                "考虑到您的需求，{period}期分期方案比较适合您，月供为{monthly_payment}元，总费率为{rate}%。"
            ],
            "confirmation": [
                "您的分期申请已提交成功，订单号为{order_id}。系统将在1-2个工作日内完成审批。",
                "分期订单已生成，订单号：{order_id}。我们会尽快处理您的申请，请耐心等待审批结果。"
            ],
            "fallback": [
                "很抱歉，我没能完全理解您的问题。请问您是想了解信用卡分期业务吗？",
                "抱歉，我可能理解有误。请问您是需要办理分期业务，还是想咨询分期相关问题？"
            ]
        }
        
        # 识别常见意图的关键词
        self.intent_keywords = {
            "分期查询": ["分期", "分几期", "利率", "手续费", "费率", "还款", "月供"],
            "账单分期": ["账单分期", "已出账", "已出账单", "账单"],
            "消费分期": ["消费分期", "购物分期", "消费"],
            "现金分期": ["现金分期", "取现分期", "取现"],
            "金额咨询": ["额度", "金额", "可以分期多少", "最高", "最低"],
            "期数咨询": ["几期", "多少期", "分期期数", "期数", "时间"],
            "申请流程": ["怎么申请", "如何办理", "申请流程", "办理流程"],
            "提前还款": ["提前还款", "提前结清", "违约金"]
        }
        
        # 工具调用决策逻辑
        self.tool_trigger_patterns = [
            {
                "pattern": r"(想要|办理|申请)(消费|账单|现金)?分期",
                "tool": "place_installment_order_sap",
                "module": "integrated_tools",
                "extract_params": self._extract_installment_params
            },
            {
                "pattern": r"查询(客户|用户|我的)信息",
                "tool": "query_customer_info",
                "module": "spa_tools",
                "extract_params": self._extract_customer_id
            },
            {
                "pattern": r"(查询|了解|想知道)(分期)?优惠",
                "tool": "query_installment_offers",
                "module": "spa_tools",
                "extract_params": self._extract_customer_id
            },
            {
                "pattern": r"计算(.*?)分期",
                "tool": "calculate_installment_plan",
                "module": "spa_tools",
                "extract_params": self._extract_calculation_params
            },
            {
                "pattern": r"打开(.*?)页面|进入(.*?)菜单|查看(.*?)功能",
                "tool": "search_and_navigate",
                "module": "integrated_tools",
                "extract_params": self._extract_navigation_target
            }
        ]

    def _extract_installment_params(self, message: str) -> Dict[str, Any]:
        """从消息中提取分期参数"""
        # 提取金额
        amount_match = re.search(r'(\d+)[万k千]?元|(\d+)[万k千]?块', message, re.IGNORECASE)
        amount = 5000  # 默认金额
        if amount_match:
            amount_str = amount_match.group(1) or amount_match.group(2)
            amount = int(amount_str)
            # 处理单位
            if '万' in amount_match.group(0):
                amount *= 10000
            elif 'k' in amount_match.group(0).lower() or '千' in amount_match.group(0):
                amount *= 1000
        
        # 提取期数
        periods_match = re.search(r'(\d+)期', message)
        periods = 12  # 默认期数
        if periods_match:
            periods = int(periods_match.group(1))
        
        # 构建一个简单的客户信息
        customer_info = {
            "name": "测试用户",
            "id": "1234567890"
        }
        
        return {
            "amount": amount,
            "periods": periods,
            "customer_info": customer_info
        }
    
    def _extract_customer_id(self, message: str) -> Dict[str, Any]:
        """从消息中提取客户ID"""
        # 尝试提取ID号码
        id_match = re.search(r'ID[号码]?[:：]?\s*(\d+)', message, re.IGNORECASE)
        customer_id = "1234567890"  # 默认ID
        
        if id_match:
            customer_id = id_match.group(1)
        
        return {
            "customer_id": customer_id
        }
    
    def _extract_calculation_params(self, message: str) -> Dict[str, Any]:
        """从消息中提取计算所需参数"""
        # 提取金额
        amount_match = re.search(r'(\d+)[万k千]?元|(\d+)[万k千]?块', message, re.IGNORECASE)
        amount = 5000  # 默认金额
        if amount_match:
            amount_str = amount_match.group(1) or amount_match.group(2)
            amount = int(amount_str)
            # 处理单位
            if '万' in amount_match.group(0):
                amount *= 10000
            elif 'k' in amount_match.group(0).lower() or '千' in amount_match.group(0):
                amount *= 1000
        
        # 提取期数
        periods_match = re.search(r'(\d+)期', message)
        periods = 12  # 默认期数
        if periods_match:
            periods = int(periods_match.group(1))
        
        # 提取费率
        rate_match = re.search(r'(\d+(\.\d+)?)%', message)
        rate = None  # 默认费率
        if rate_match:
            rate = float(rate_match.group(1))
        
        return {
            "amount": amount,
            "periods": periods,
            "rate": rate
        }
    
    def _extract_navigation_target(self, message: str) -> Dict[str, Any]:
        """从消息中提取导航目标"""
        # 尝试提取目标菜单或页面名称
        target_match = re.search(r'打开(.*?)页面|进入(.*?)菜单|查看(.*?)功能', message)
        keyword = "分期申请"  # 默认导航目标
        
        if target_match:
            for group in target_match.groups():
                if group:
                    keyword = group
                    break
        
        return {
            "keyword": keyword
        }
    
    def _should_call_tool(self, message: str) -> Optional[Dict[str, Any]]:
        """决定是否应该调用工具以及调用哪个工具"""
        for trigger in self.tool_trigger_patterns:
            if re.search(trigger["pattern"], message):
                # 找到匹配的工具触发模式
                tool_info = {
                    "tool_name": trigger["tool"],
                    "module_name": trigger["module"],
                    "parameters": trigger["extract_params"](message)
                }
                return tool_info
        return None
    
    def _identify_intent(self, message: str) -> str:
        """识别用户消息的主要意图"""
        # 计算每个意图的匹配得分
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in message:
                    score += 1
            intent_scores[intent] = score
        
        # 返回得分最高的意图
        if max(intent_scores.values(), default=0) > 0:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        else:
            return "greeting" if "你好" in message or "您好" in message else "fallback"
    
    def _format_response_with_template(self, intent: str, data: Dict[str, Any] = None) -> str:
        """使用模板格式化响应"""
        templates = self.response_templates.get(intent, self.response_templates["fallback"])
        template = random.choice(templates)
        
        if data:
            try:
                return template.format(**data)
            except KeyError:
                # 如果格式化失败，返回原始模板
                return template
        
        return template
    
    async def _execute_tool_call(self, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            module_name = tool_info["module_name"]
            tool_name = tool_info["tool_name"]
            parameters = tool_info["parameters"]
            
            if module_name in self.tools_modules and tool_name in self.tools_modules[module_name]:
                tool_func = self.tools_modules[module_name][tool_name]
                
                # 等待异步函数执行完成
                result = await tool_func(**parameters)
                
                return {
                    "status": "success",
                    "tool": tool_name,
                    "result": result
                }
            else:
                return {
                    "status": "error",
                    "message": f"Tool {tool_name} not found in module {module_name}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _generate_text_response(self, message: str, tool_result: Dict[str, Any] = None) -> str:
        """根据用户消息和可能的工具调用结果生成文本响应"""
        # 确定意图
        intent = self._identify_intent(message)
        
        # 如果有工具调用结果，根据结果生成响应
        if tool_result and tool_result["status"] == "success":
            tool_name = tool_result["tool"]
            result = tool_result["result"]
            
            # 根据不同工具生成不同响应
            if tool_name == "place_installment_order_sap":
                return self._format_response_with_template("confirmation", {
                    "order_id": result.get("order_id", "INS" + str(random.randint(10000, 99999)))
                })
            
            elif tool_name == "calculate_installment_plan":
                content = result.get("content", {})
                return self._format_response_with_template("recommendation", {
                    "period": content.get("periods", 12),
                    "monthly_payment": content.get("monthly_payment", 500),
                    "fee_amount": content.get("fee_amount", 300),
                    "rate": content.get("rate", 3.0)
                })
            
            elif tool_name == "query_customer_info":
                # 直接使用客户信息生成个性化回复
                content = result.get("content", {})
                return f"您好，{content.get('name', '尊敬的客户')}！您的信用卡可用额度为{content.get('available_credit', 30000)}元，总额度为{content.get('total_credit_limit', 50000)}元。"
            
            elif tool_name == "query_installment_offers":
                return "根据您的账户情况，我们为您提供了以下分期优惠：\n1. 消费分期：3-24期，最低费率1.5%\n2. 账单分期：3-12期，最低费率1.2%\n3. 现金分期：12-36期，最低费率6.5%\n请问您想了解哪种分期产品的详细信息？"
            
            elif tool_name == "search_and_navigate":
                return f"我已为您打开相关页面，请问您需要办理哪种业务？"
        
        # 没有工具调用或调用失败，根据意图生成响应
        if intent == "分期查询":
            return "我们的分期业务包括消费分期、账单分期和现金分期。不同期数的费率各不相同，例如3期的费率约为1.5%，6期约为3.0%，12期约为6.0%。请问您想了解哪种分期的具体费率？"
        
        elif intent == "账单分期":
            return "账单分期是将已出账单的消费金额分期偿还的业务，支持3期、6期和12期，最低500元起分。您当前账单有哪些消费需要分期呢？"
        
        elif intent == "消费分期":
            return "消费分期适用于单笔金额较大的消费，支持3-24期不等，最低100元起分。您有什么大额消费需要分期吗？"
        
        elif intent == "现金分期":
            return "现金分期可以将信用卡额度转为现金使用，支持12-36期，最低1000元起分。费率相对较高，您确定需要办理现金分期吗？"
        
        elif intent == "金额咨询":
            return "我们的分期业务最低起分金额为：消费分期100元、账单分期500元、现金分期1000元。最高可分期金额取决于您的信用卡可用额度，您想查询您的可用额度吗？"
        
        elif intent == "期数咨询":
            return "我们提供多种分期期数选择：消费分期支持3/6/12/24期，账单分期支持3/6/12期，现金分期支持12/24/36期。不同期数对应不同的手续费率。"
        
        elif intent == "申请流程":
            return "申请分期非常简单：1. 选择分期类型；2. 确定分期金额和期数；3. 确认分期方案；4. 提交申请。整个过程只需几分钟，我可以立即帮您办理，您需要分期的金额和期数是多少？"
        
        elif intent == "提前还款":
            return "我们支持提前还款，但可能无法退还未发生的手续费。提前还款不收取违约金，您可以通过我行APP或客服热线申请办理。"
        
        elif intent == "greeting":
            return self._format_response_with_template("greeting")
        
        else:  # fallback
            return self._format_response_with_template("clarification")
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        处理用户消息并生成回复
        
        Args:
            message: 用户输入的消息
            
        Returns:
            Dict: 包含回复内容和可能的功能调用信息
        """
        # 检查是否应该调用工具
        tool_info = self._should_call_tool(message)
        tool_result = None
        
        # 如果需要调用工具，执行工具调用
        if tool_info and self.tools_modules:
            tool_result = await self._execute_tool_call(tool_info)
            
            # 包装工具调用和执行结果为函数调用格式
            function_call = {
                "name": tool_info["tool_name"],
                "arguments": json.dumps(tool_info["parameters"])
            }
            
            function_response = {
                "name": tool_info["tool_name"],
                "content": json.dumps(tool_result["result"] if tool_result["status"] == "success" else {"error": tool_result["message"]})
            }
        else:
            function_call = None
            function_response = None
        
        # 生成文本响应
        text_response = self._generate_text_response(message, tool_result)
        
        # 构建完整响应
        response = {
            "role": "assistant",
            "content": text_response
        }
        # 如果有函数调用，添加到响应中
        if function_call:
            response["function_call"] = function_call
            
        # 构建完整返回结果
        result = {
            "response": response,
            "function_call": function_call,
            "function_response": function_response,
            "finish_reason": "function_call" if function_call else "stop"
        }
        
        return result


class MockLLMClient:
    """
    模拟大语言模型客户端，符合AutoGen的模型接口要求
    """
    
    def __init__(self, tools_modules=None):
        """
        初始化模拟LLM客户端
        
        Args:
            tools_modules: 可用工具模块字典
        """
        self.generator = MockLLMResponseGenerator(tools_modules)
        
        # 模型信息符合AutoGen期望
        self.model_info = {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "qwen",
        }
        
        # 记录对话历史
        self.history = []
    
    async def create(self, messages, stream=False, **kwargs):
        """
        创建一个对话响应，符合OpenAI格式的API调用
        
        Args:
            messages: 对话历史消息列表
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            Dict: 响应结果
        """
        # 将消息添加到历史
        self.history.extend(messages)
        
        # 获取用户的最后一条消息
        user_message = None
        for message in reversed(messages):
            # Try dictionary access first
            message_str = str(message)
            if "source='user'" in message_str:
                # Extract content from the string representation
                # This is a fallback and might not be reliable
                start_idx = message_str.find("content='") + 9
                end_idx = message_str.find("'", start_idx)
                if start_idx > 8 and end_idx > start_idx:
                    user_message = message_str[start_idx:end_idx]
                    break
        
        if not user_message:
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": "我没有收到您的消息，请问您需要什么帮助？"},
                    "finish_reason": "stop"
                }]
            }
        
        # 处理消息
        result = await self.generator.process_message(user_message)
        response = result["response"]
        
        # 构建符合OpenAI格式的响应
        completion = {
            "id": f"mock-completion-{random.randint(1000, 9999)}",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": "mock-qwen-model",
            "choices": [
                {
                    "index": 0,
                    "message": response,
                    "finish_reason": result["finish_reason"]
                }
            ]
        }
        
        # 流式输出
        if stream:
            async def stream_gen():
                # 简单模拟流式输出，为了简化，这里只返回完整响应
                yield completion
            
            return stream_gen()
        
        return completion

# 模拟创建新的OpenAI客户端的函数
def create_mock_openai_client(api_key=None, base_url=None, **kwargs):
    """创建一个模拟的OpenAI客户端"""
    # 在真实环境中导入工具模块
    # 为了演示，这里使用占位符
    try:
        # 尝试导入真实的工具模块
        from spa_navigator.integrated_tools import all_tools as spa_tools
        
        tools_modules = {
            "spa_tools": spa_tools,
        }
    except ImportError:
        print("警告: 未能导入实际工具模块，将使用空工具模块")
        tools_modules = {}
    
    return MockLLMClient(tools_modules)
