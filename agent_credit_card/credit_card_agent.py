import streamlit as st
import asyncio
import httpx
import json
import re
import time
from typing import Any, Dict
from datetime import datetime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import the SPA function tools we generated
from spa_navigator.integrated_tools import all_tools as spa_tools
# Modified version of your Agent app with SPA tools integration


class CreditCardAgentApp:
    def __init__(self, use_mock_tools=False):
        # Set page config
        """
        初始化应用
        
        Args:
            use_mock_tools: 是否使用模拟工具
        """
        st.set_page_config(
            page_title="中信银行信用卡中心",
            page_icon="💳",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Apply custom CSS
        self.apply_custom_css()
        # Initialize session state
        self.init_session_state()
        # Add SPA Navigator tools to our tools list
        self.tools = None
        if use_mock_tools:
            self.setup_mock_tools() 
        else:
            self.setup_tools()
        # Setup agent with tools
        self.agent = self.create_agent(use_mock_api=use_mock_tools)
        # Track the last user query for response cleaning
        self._last_user_query = ""
    
    def setup_tools(self):
        """设置工具函数"""
        try:
            # 尝试导入实际工具
            from spa_navigator.integrated_tools import all_tools as spa_tools
            
            # 创建工具字典
            self.tools = {
                "query_knowledge_base": self.query_knowledge_base,
                "place_installment_order": self.place_installment_order
            }
            
            # 添加SPA工具包装方法
            self.add_spa_tool_wrappers()
        except ImportError:
            print("警告: 无法导入实际工具，将使用模拟实现")
            # 返回模拟工具
            return self.setup_mock_tools()
    
    def setup_mock_tools(self):
        """设置模拟工具函数，完全模拟spa_tools和integrated_tools中的所有工具"""
        # 这里是完整的setup_mock_tools函数实现
        # 为简化，我们只展示一部分关键工具函数
        import random
        import time
        
        def mock_query_customer_info(customer_id: str):
            """查询客户信息"""
            return {
                "status": "success",
                "content": {
                    "id": customer_id,
                    "name": f"测试用户_{customer_id[-4:]}",
                    "card_number": f"6229{customer_id[-4:]}XXXX4598",
                    "available_credit": 30000,
                    "total_credit_limit": 50000,
                    "card_status": "正常",
                    "level": "普卡"
                }
            }
        
        def mock_calculate_installment_plan(amount: float, periods: int, rate: float = None):
            """计算分期方案详情"""
            if rate is None:
                rate = periods * 0.5
            fee_amount = amount * (rate / 100)
            total_amount = amount + fee_amount
            monthly_payment = total_amount / periods
            
            return {
                "status": "success",
                "content": {
                    "amount": amount,
                    "periods": periods,
                    "rate": rate,
                    "fee_amount": round(fee_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "monthly_payment": round(monthly_payment, 2)
                }
            }
        
        def mock_place_installment_order(amount: float, periods: int, rate: float, customer_info: dict):
            """下分期订单"""
            return {
                "status": "success",
                "order_id": f"INS{int(time.time())}",
                "message": "分期订单已成功创建，系统处理中，预计10分钟内完成审批。"
            }
        
        def mock_query_knowledge_base(query: str):
            """查询知识库回答问题"""
            return "我们的分期业务包括消费分期、账单分期和现金分期。不同期数的费率各不相同，例如3期的费率约为1.5%，6期约为3.0%，12期约为6.0%。"
        
        # 返回所有模拟工具
        return {
            "query_customer_info": mock_query_customer_info,
            "calculate_installment_plan": mock_calculate_installment_plan,
            "place_installment_order": mock_place_installment_order,
            "query_knowledge_base": mock_query_knowledge_base
        }
    def add_spa_tool_wrappers(self):
        """为 SPA 工具创建包装方法，确保类型注解正确"""
        from typing import Dict, Any, List, Optional, Union
        
        def wrapped_get_menu_structure() -> Dict[str, Any]:
            """获取菜单结构"""
            func = spa_tools["get_menu_structure"]
            return func()
        self.tools["get_menu_structure"] = wrapped_get_menu_structure
        
        def wrapped_search_menu_items(keyword: str) -> Dict[str, Any]:
            """搜索包含关键词的菜单项"""
            func = spa_tools["search_menu_items"]
            return  func(keyword)
        self.tools["search_menu_items"] = wrapped_search_menu_items
        
        def wrapped_navigate_to_menu(menu_path: str) -> Dict[str, Any]:
            """导航到指定菜单路径"""
            func = spa_tools["navigate_to_menu"]
            return  func(menu_path)
        self.tools["navigate_to_menu"] = wrapped_navigate_to_menu
        
        def wrapped_get_current_iframe_content() -> Dict[str, Any]:
            """获取当前 iframe 的内容"""
            func = spa_tools["get_current_iframe_content"]
            return  func()
        self.tools["get_current_iframe_content"] = wrapped_get_current_iframe_content
        
        def wrapped_click_button_in_iframe(button_text: str) -> Dict[str, Any]:
            """点击 iframe 中的按钮"""
            func = spa_tools["click_button_in_iframe"]
            return  func(button_text)
        self.tools["click_button_in_iframe"] = wrapped_click_button_in_iframe
        
        def wrapped_fill_input_in_iframe(field_name: str, value: str) -> Dict[str, Any]:
            """填写 iframe 中的输入框"""
            func = spa_tools["fill_input_in_iframe"]
            return  func(field_name, value)
        self.tools["fill_input_in_iframe"] = wrapped_fill_input_in_iframe
        
        def wrapped_click_link_in_iframe(link_text: str) -> Dict[str, Any]:
            """点击 iframe 中的链接"""
            func = spa_tools["click_link_in_iframe"]
            return  func(link_text)
        self.tools["click_link_in_iframe"] = wrapped_click_link_in_iframe
        
        def wrapped_query_customer_info(customer_id: str) -> Dict[str, Any]:
            """查询客户信息"""
            func = spa_tools["query_customer_info"]
            return  func(customer_id)
        self.tools["query_customer_info"] = wrapped_query_customer_info
        
        def wrapped_query_installment_offers() -> Dict[str, Any]:
            """查询客户可用的分期优惠"""
            func = spa_tools["query_installment_offers"]
            return  func()
        self.tools["query_installment_offers"] = wrapped_query_installment_offers
        
        def wrapped_query_historical_bills():
            """查询客户可用的分期优惠"""
            func = spa_tools["query_historical_bills"]
            return  func()
        self.tools["query_historical_bills"] = wrapped_query_historical_bills

        def wrapped_calculate_installment_plan(amount: float, periods: int, rate: Optional[float] = None) -> Dict[str, Any]:
            """计算分期方案详情"""
            func = spa_tools["calculate_installment_plan"]
            return  func(amount, periods, rate)
        self.tools["calculate_installment_plan"] = wrapped_calculate_installment_plan
        
        # 组合工具包装
        def wrapped_search_and_navigate(keyword: str) -> Dict[str, Any]:
            """搜索并导航到匹配的菜单项"""
            func = spa_tools["search_and_navigate"]
            return  func(keyword)
        self.tools["search_and_navigate"] = wrapped_search_and_navigate
        
        def wrapped_process_form_and_submit(form_data: Dict[str, str], submit_button: str = "提交") -> Dict[str, Any]:
            """填写表单并提交"""
            func = spa_tools["process_form_and_submit"]
            return  func(form_data, submit_button)
        self.tools["process_form_and_submit"] = wrapped_process_form_and_submit
        
        def wrapped_place_installment_order_sap(amount: float, periods: int, customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """通过SAP系统下分期订单"""
            func = spa_tools["place_installment_order_sap"]
            return  func(amount, periods, customer_info)
        self.tools["place_installment_order_sap"] = wrapped_place_installment_order_sap
        
    def apply_custom_css(self):
        # Professional Custom CSS
        st.markdown("""
        <style>
            /* Main background and text colors */
            .main {
                background-color: #FFFFFF;
                color: #333333;
            }
            
            /* Header styling */
            h1, h2, h3 {
                color: #C1272D; /* CITIC Bank red */
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            }
            
            /* Input field styling */
            .stTextInput > div > div > input, .stTextArea > div > div > textarea {
                background-color: #F8F9FA;
                border: 1px solid #EAEAEA;
                border-radius: 5px;
                padding: 10px;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            }
            
            /* Button styling */
            .stButton > button {
                background-color: #C1272D; /* CITIC Bank red */
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            
            .stButton > button:hover {
                background-color: #A61E22; /* Darker red on hover */
                box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
            }
            
            /* Chat message styling */
            .chat-message {
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 16px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                line-height: 1.5;
            }
            
            .user-message {
                background-color: #F0F4F8;
                border-left: 4px solid #4A6FE3;
                margin-left: 40px;
            }
            
            .assistant-message {
                background-color: #FFF8F8;
                border-left: 4px solid #C1272D;
                margin-right: 40px;
            }
            
            /* Sidebar styling */
            .sidebar .sidebar-content {
                background-color: #F8F9FA;
            }
            
            /* Footer styling */
            footer {
                border-top: 1px solid #EAEAEA;
                padding-top: 16px;
                color: #666666;
                font-size: 12px;
            }
            
            /* Card styling for the expandable sections */
            .card {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #EAEAEA;
                padding: 16px;
                margin-bottom: 16px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            
            /* Streaming effect styling */
            @keyframes blink {
                0% { opacity: 1; }
                50% { opacity: 0; }
                100% { opacity: 1; }
            }
            
            #streaming-content::after {
                content: '▌';
                display: inline-block;
                animation: blink 1s step-end infinite;
                color: #C1272D;
                margin-left: 2px;
            }
        </style>
        """, unsafe_allow_html=True)
    
    def init_session_state(self):
        # Initialize session state for chat history and input clearing
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
            
        # Initialize session state for customer information
        if "customer_info" not in st.session_state:
            st.session_state.customer_info = {
                "customer_type": "普通客户",
                "name": "",
                "id": "",
                "amount": 0,
                "periods": 0,
                "rate": 0
            }
        
        # Initialize state for current navigation context
        if "current_menu" not in st.session_state:
            st.session_state.current_menu = None
        
        if "current_iframe" not in st.session_state:
            st.session_state.current_iframe = None
            
        # Check if we need to clear the input from previous run
        if "clear_input" in st.session_state and st.session_state.clear_input:
            st.session_state.user_input = ""
            st.session_state.clear_input = False
    
    # Read the sales agent prompt template
    def read_prompt_template(self):
        try:
            with open("integrated-agent-prompt.md", "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            print(f"Error reading prompt template: {e}")
            # Fallback prompt if template file not found
            return """
            # 中信银行信用卡中心客户经理

            你是中信银行信用卡中心的专业客户经理，负责为客户提供信用卡分期业务咨询和服务。

            ## 主要职责
            1. 回答客户关于信用卡分期业务的问题
            2. 根据客户需求推荐合适的分期方案
            3. 协助客户完成分期申请流程
            4. 操作系统查询相关信息

            ## 工作风格
            - 专业：展示你对金融产品的专业知识
            - 热情：主动了解客户需求，提供周到服务
            - 高效：能快速解决客户问题，简洁明了地回答
            - 诚信：提供真实准确的信息，不夸大产品优势
            
            ## 重要提示
            - 回复时请勿重复用户的问题或输入
            - 回复要直接给出信息，不要像"您好！请告诉我您的分期需求"这样的开场白
            - 直接回答用户的问题，简明扼要
            - 使用函数工具时，保持简洁，不要在回复中包含函数调用的技术细节
            """
    
    # Tool: Place credit card installment order
    def place_installment_order(self, amount: float, periods: int, rate: float, customer_info: dict) -> str:
        """Place a credit card installment order in the system"""
        try:
            # 首先尝试使用SPA系统下单
            sap_result = self.tools["place_installment_order_sap"](amount, periods, customer_info)
            
            if sap_result["status"] == "success":
                # 如果SPA下单成功，直接返回结果
                return {
                    "status": "success",
                    "order_id": sap_result.get("order_id", f"INS{int(time.time())}"),
                    "message": "分期订单已成功创建，系统处理中，预计10分钟内完成审批。"
                }
            else:
                # 如果SPA下单失败，返回原本的模拟下单逻辑
                print(f"SPA下单失败，返回模拟结果: {sap_result}")
        except Exception as e:
            print(f"SPA下单异常，返回模拟结果: {str(e)}")
        
        # 原始模拟下单逻辑作为备选
        order_data = {
            "amount": amount,
            "periods": periods,
            "rate": rate,
            "customer_info": customer_info,
            "timestamp": time.time()
        }
        return {
            "status": "success",
            "order_id": f"INS{int(time.time())}",
            "message": "分期订单已成功创建，系统处理中，预计10分钟内完成审批。"
        }

    # Tool: Knowledge base RAG API for answering customer questions
    async def query_knowledge_base(self, query: str) -> str:
        """Query the knowledge base to answer customer questions"""
        async with httpx.AsyncClient() as client:
            try:
                # 按照新的接口格式构建请求
                request_data = [
                    {"role": "user", "content": query}
                ]
                
                response = await client.post(
                    "http://cacp.devapps.oa.citicbank.com/cacp-faq-model/generate",
                    json=request_data,
                    timeout=30.0
                )
                result = response.json()
                
                # 根据接口的返回格式获取答案
                if result.get("code") == '200':
                    return result.get("data", {}).get("answer", "抱歉，我暂时无法回答这个问题，请联系客服热线获取更多帮助。")
                else:
                    return f"知识库查询失败: {result.get('message', '未知错误')}。请稍后再试。"
            except Exception as e:
                return f"知识库查询失败: {str(e)}。请稍后再试。"
                
    # Create an agent with the tools
    def create_agent(self, use_mock_api=True):
        if use_mock_api:
        # 使用模拟API
            from mock_llm_api import create_mock_openai_client
            model_client = create_mock_openai_client()
            print("成功创建模拟OpenAI客户端")
        else:
            # 使用实际API
            model_client = OpenAIChatCompletionClient(
                model="gemma2:27b-tools",
                base_url="http://localhost:11434/v1",#外网
                #base_url="http://28.105.66.197:11434/v1",
                api_key="placeholder",
                model_info={
                    "vision": False,
                    "function_calling": True,
                    "json_output": False,
                    "family": "unknown",
                },
            )
        
        # Read the sales agent prompt template
        system_prompt = self.read_prompt_template()
        system_prompt += "\n\n重要提示：严格禁止在回复中重复用户的问题。直接回答，不要重复用户的输入。"

        # Convert tools dict to list for the agent
        tool_list = list(self.tools.values())
        agent = AssistantAgent(
            name="assistant",
            model_client=model_client,
            tools=tool_list,
            system_message=system_prompt,
        )
        
        return agent
    
    # Main function to run the agent with streaming output
    # In the run_agent method, update the logic to better handle streaming output and filter function calls
    async def run_agent(self, task, history_container=None):
        """
        运行代理并处理响应
        
        Args:
            task: 用户任务
            history_container: 用于显示历史的容器
        
        Returns:
            str: 完整的响应
        """
        # 如果没有提供历史容器，创建一个空容器
        if history_container is None:
            history_container = st.empty()
        
        # 创建占位符
        response_placeholder = history_container.empty()
        debug_placeholder = history_container.empty()
        self._last_user_query = task
        
        try:
            # 运行代理
            full_response = ""
            debug_info = ""
            
            # 获取流式响应
            async_gen = self.agent.run_stream(task=task)
            
            # 初始化HTML容器
            html_template = """
            <div class="chat-message assistant-message">
                <div id="streaming-content">💼 经理：{}</div>
            </div>
            """
            
            # 处理异步生成器
            async for response_chunk in async_gen:
                # 处理基于类型的块
                chunk_text = ""
                
                # 检查response_chunk的类型并相应处理
                if isinstance(response_chunk, str):
                    chunk_text = response_chunk
                elif hasattr(response_chunk, 'content'):
                    # 处理UserMessage或类似对象
                    chunk_text = str(response_chunk.content)
                elif isinstance(response_chunk, dict) and "content" in response_chunk:
                    # 处理类似字典的对象
                    chunk_text = str(response_chunk["content"])
                else:
                    # 处理其他类型
                    chunk_text = str(response_chunk)
                
                # 检查是否包含函数调用信息
                if any(marker in chunk_text for marker in ["[FunctionCall", "[FunctionExecutionResult", "TaskResult("]):
                    # 添加到调试信息
                    debug_info += chunk_text
                    continue
                
                # 添加到完整响应
                full_response += chunk_text
                
                # 清理响应文本
                clean_response = self.clean_response_text(full_response)
                
                # 更新响应占位符
                response_placeholder.markdown(html_template.format(clean_response), unsafe_allow_html=True)
                
                # 小延迟以创建打字效果
                await asyncio.sleep(0.005)
            
            # 最终清理响应
            clean_response = self.clean_response_text(full_response)
            
            # 最后一次更新
            response_placeholder.markdown(html_template.format(clean_response), unsafe_allow_html=True)
            
            # 显示调试信息
            if debug_info and debug_info.strip():
                with debug_placeholder.expander("查看系统操作详情", expanded=False):
                    st.markdown(f'<div style="color: #999999; font-size: 0.8em;">{debug_info}</div>', unsafe_allow_html=True)
            
            # 返回清理后的响应
            return clean_response
            
        except Exception as e:
            error_msg = f"错误: {str(e)}"
            response_placeholder.error(error_msg)
            return error_msg
    # Helper method to clean response text
    def clean_response_text(self, text):
        """Clean the response text by removing function calls and query repetitions"""
        if not text:
            return ""
        
        # Remove any function call patterns
        clean_text = re.sub(r'\[FunctionCall.*?\]', '', text)
        clean_text = re.sub(r'\[FunctionExecutionResult.*?\]', '', clean_text)
        clean_text = re.sub(r'TaskResult\(.*?\)', '', clean_text)
        
        # Remove common greeting patterns that often precede repetition
        clean_text = re.sub(r'^(您好[！!,，.。]?\s*)', '', clean_text)
        clean_text = re.sub(r'^(好的[！!,，.。]?\s*)', '', clean_text)
        clean_text = re.sub(r'^(非常感谢您的咨询[！!,，.。]?\s*)', '', clean_text)
        
        # Remove any direct repetition of the user's query with various formats
        if self._last_user_query:
            # Escape special regex characters in the user query
            escaped_query = re.escape(self._last_user_query)
            
            # Create patterns for different ways the query might be repeated
            patterns = [
                # Direct repetition at start
                fr'^({escaped_query})\s*[:：]?\s*',
                # Repetition with a prefix like "关于" or "您的问题："
                fr'^(关于{escaped_query}|您的问题[:：]?\s*{escaped_query}|您询问的[:：]?\s*{escaped_query})\s*[:：]?\s*',
                # Repetition with "您问"
                fr'^(您问[:：]?\s*{escaped_query})\s*[:：]?\s*',
                # Summary repetition - match partial repetitions
                fr'^(根据您提到的.*?{escaped_query.split()[0]}.*?[:：]?)\s*',
            ]
            
            # Apply all patterns
            for pattern in patterns:
                clean_text = re.sub(pattern, '', clean_text)
        
        # Clean up any duplicate spaces and start of response
        clean_text = clean_text.strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text

    def update_navigation_state(self, debug_text):
        """Update session state based on SPA navigation function calls"""
        # Check for navigate_to_menu calls
        if "navigate_to_menu" in debug_text and "FunctionExecutionResult" in debug_text:
            # Try to parse the result
            try:
                # Extract the JSON part of the result
                result_match = re.search(r'\[FunctionExecutionResult\](.*?)\[/FunctionExecutionResult\]', debug_text, re.DOTALL)
                if result_match:
                    result_text = result_match.group(1).strip()
                    result = json.loads(result_text)
                    
                    # Check if navigation was successful
                    if result.get("status") == "success":
                        # Update current menu
                        menu_path = None
                        call_match = re.search(r'\[FunctionCall\](.*?)\[/FunctionCall\]', debug_text, re.DOTALL)
                        if call_match:
                            call_text = call_match.group(1).strip()
                            call_data = json.loads(call_text)
                            if "arguments" in call_data:
                                menu_path = call_data["arguments"].get("menu_path")
                        
                        if menu_path:
                            st.session_state.current_menu = menu_path
                            
                        # Update current iframe content if available
                        if "content" in result:
                            st.session_state.current_iframe = result["content"]
            except Exception as e:
                print(f"Error parsing navigation result: {e}")
    
    def run(self):
        """Run the Streamlit app"""
        # Main app content
        st.title("中信银行信用卡分期经理")

        # Introduction card
        st.markdown("""
        <div class="card">
            <h3>专业金融经理，为您定制最优分期方案</h3>
            <p>您好！我是中信银行信用卡中心的专业经理，很高兴为您服务。</p>
            <p>请告诉我您的分期需求，我将为您推荐最合适的分期方案，并解答您的各类问题。</p>
        </div>
        """, unsafe_allow_html=True)

        # System status indicator (if navigated to a menu)
        if st.session_state.current_menu:
            st.markdown(f"""
            <div style="background-color: #F0F8FF; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                <p><strong>当前系统位置:</strong> {st.session_state.current_menu}</p>
            </div>
            """, unsafe_allow_html=True)

        # Chat container
        chat_container = st.container()

        # Display chat history
        with chat_container:
            if not st.session_state.chat_history:
                st.info("👋 您好！请告诉我您的分期需求，我将为您推荐最合适的方案。")
            # Update the chat display part in the run method to use the new helper function
            # Replace the chat history display section in run() method with this:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <div>👤 您：{message["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 使用 content 属性或字典访问方式获取内容
                    if isinstance(message, dict):
                        content = message.get("content", "")
                    elif hasattr(message, "content"):
                        content = message.content
                    else:
                        content = str(message)
                    
                    # 清理响应文本
                    content = self.clean_response_text(content)
                    
                    # 提取调试信息（函数调用和结果）
                    debug_info = ""
                    for pattern in [r'\[FunctionCall.*?\]', r'\[FunctionExecutionResult.*?\]', r'TaskResult\(.*?\)']:
                        if isinstance(content, str):
                            matches = re.findall(pattern, content, re.DOTALL)
                            if matches:
                                debug_info += ''.join(matches)
                    
                    # 显示清理后的内容
                    if content.strip():
                        st.markdown(f"""
                        <div class="chat-message assistant-message">
                            <div>💼 经理：{content}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 显示调试信息
                    if debug_info:
                        with st.expander("查看系统操作详情", expanded=False):
                            st.markdown(f"""
                            <div style="color: #999999; font-size: 0.8em;">
                                {debug_info}
                            </div>
                            """, unsafe_allow_html=True)
        
        # User input
        # 修改 run 方法中处理用户输入和接收响应的部分
        # 替换以下代码到 run 方法中对应部分

        with st.container():
            user_input = st.text_area("请输入您的问题或需求:", key="user_input", height=80, 
                                    placeholder="例如：我想购买一部手机，大约5000元，可以分期吗？")
            cols = st.columns([1, 1, 4])
            with cols[0]:
                if st.button("发送", use_container_width=True):
                    if user_input:
                        # 添加用户消息到历史
                        st.session_state.chat_history.append({"role": "user", "content": user_input})
                        
                        # 创建一个容器用于显示这次响应
                        response_container = st.empty()
                        
                        # 运行代理获取响应
                        response = asyncio.run(self.run_agent(user_input, response_container))
                        
                        # 添加响应到历史（确保它是字典格式）
                        if isinstance(response, str):
                            response_dict = {"role": "assistant", "content": response}
                            st.session_state.chat_history.append(response_dict)
                        else:
                            # 如果response已经是一个对象，转换为字典格式
                            content = response.content if hasattr(response, "content") else str(response)
                            st.session_state.chat_history.append({"role": "assistant", "content": content})
                        
                        # 清空输入
                        st.session_state.clear_input = True
                        st.rerun()
            
            with cols[1]:
                if st.button("清空对话", use_container_width=True):
                    st.session_state.chat_history = []
                    st.session_state.current_menu = None
                    st.session_state.current_iframe = None
                    st.rerun()
        
        # Sidebar content
        self.render_sidebar()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>中信银行信用卡中心</span>
            <span>客服热线：400-888-8888</span>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar content"""
        with st.sidebar:
            # Try to load local logo first, fall back to placeholder if file doesn't exist
            try:
                st.image("citic_logo.png", width=150)
            except:
                st.markdown("### 中信银行信用卡中心")
            
            st.header("客户画像配置")
            customer_type = st.selectbox(
                "选择客户类型:",
                ["普通客户", "价格敏感型客户", "急速决策型客户", "关系导向型客户", "犹豫不决型客户", "知识型客户"]
            )
            st.session_state.customer_info["customer_type"] = customer_type
            
            st.markdown("---")
            
            # Add SPA Navigator status
            if st.session_state.current_menu:
                st.subheader("当前系统状态")
                st.markdown(f"**当前菜单**: {st.session_state.current_menu}")
                
                # Show preview of current iframe if available
                if st.session_state.current_iframe:
                    with st.expander("当前页面预览", expanded=False):
                        if isinstance(st.session_state.current_iframe, dict):
                            if "title" in st.session_state.current_iframe:
                                st.markdown(f"**页面标题**: {st.session_state.current_iframe['title']}")
                            
                            if "summary" in st.session_state.current_iframe:
                                st.markdown(f"**内容摘要**: {st.session_state.current_iframe['summary']}")
                            
                            if "headings" in st.session_state.current_iframe and st.session_state.current_iframe["headings"]:
                                st.markdown("**主要标题**:")
                                for heading in st.session_state.current_iframe["headings"][:3]:
                                    st.markdown(f"- {heading}")
                        else:
                            st.write(st.session_state.current_iframe)
            
            st.markdown("---")
            
            with st.expander("💰 分期费率参考"):
                st.markdown("""
                | 分期期数 | 标准费率 | 可协商范围 |
                |---------|----------|----------|
                | 3期 | 3.0% | 1.5%-3.0% |
                | 6期 | 6.0% | 3.0%-6.0% |
                | 12期 | 9.0% | 6.0%-12.0% |
                | 24期 | 15.0% | 12.0%-18.0% |
                """)
            
            st.markdown("---")
            
            st.caption("中信银行信用卡中心 © 2025")
            st.caption("版本: 1.0.0")

        # Add instructions in an expander below the main application
        with st.expander("💡 使用指南"):
            st.markdown("""
            ### 如何获得最佳分期方案

            1. **明确您的需求**
               - 告诉我您的分期金额和用途
               - 您期望的每月还款预算
               - 您希望分几期还款

            2. **了解分期政策**
               - 不同期数有不同的费率标准
               - 可以根据您的需求和资质提供个性化优惠
               - 分期不会影响您的信用记录（正常还款情况下）

            3. **办理流程**
               - 确认分期方案后，系统将进行审批
               - 审批通过后资金即刻到账
               - 分期金额将计入您的信用卡账单

            ### 常见问题

            - **提前还款**：支持提前还款，但可能无法退还未发生的手续费
            - **额度影响**：分期金额将占用您的信用卡额度
            - **申请条件**：信用卡状态正常，且有足够的可用额度
            """)

def main():
    app = CreditCardAgentApp(use_mock_tools=False)
    app.run()

if __name__ == "__main__":
    main()
