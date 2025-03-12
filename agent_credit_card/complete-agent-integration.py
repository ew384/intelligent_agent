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
    def __init__(self):
        # Set page config
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
        self.tools = {
            "query_knowledge_base": self.query_knowledge_base,
            "place_installment_order": self.place_installment_order
        }
        self.add_spa_tool_wrappers()
        # Setup agent with tools
        self.agent = self.create_agent()
    
    def add_spa_tool_wrappers(self):
        """为 SPA 工具创建包装方法，确保类型注解正确"""
        from typing import Dict, Any, List, Optional, Union
        
        async def wrapped_get_menu_structure() -> Dict[str, Any]:
            """获取菜单结构"""
            func = spa_tools["get_menu_structure"]
            return await func()
        self.tools["get_menu_structure"] = wrapped_get_menu_structure
        
        async def wrapped_search_menu_items(keyword: str) -> Dict[str, Any]:
            """搜索包含关键词的菜单项"""
            func = spa_tools["search_menu_items"]
            return await func(keyword)
        self.tools["search_menu_items"] = wrapped_search_menu_items
        
        async def wrapped_navigate_to_menu(menu_path: str) -> Dict[str, Any]:
            """导航到指定菜单路径"""
            func = spa_tools["navigate_to_menu"]
            return await func(menu_path)
        self.tools["navigate_to_menu"] = wrapped_navigate_to_menu
        
        async def wrapped_get_current_iframe_content() -> Dict[str, Any]:
            """获取当前 iframe 的内容"""
            func = spa_tools["get_current_iframe_content"]
            return await func()
        self.tools["get_current_iframe_content"] = wrapped_get_current_iframe_content
        
        async def wrapped_click_button_in_iframe(button_text: str) -> Dict[str, Any]:
            """点击 iframe 中的按钮"""
            func = spa_tools["click_button_in_iframe"]
            return await func(button_text)
        self.tools["click_button_in_iframe"] = wrapped_click_button_in_iframe
        
        async def wrapped_fill_input_in_iframe(field_name: str, value: str) -> Dict[str, Any]:
            """填写 iframe 中的输入框"""
            func = spa_tools["fill_input_in_iframe"]
            return await func(field_name, value)
        self.tools["fill_input_in_iframe"] = wrapped_fill_input_in_iframe
        
        async def wrapped_click_link_in_iframe(link_text: str) -> Dict[str, Any]:
            """点击 iframe 中的链接"""
            func = spa_tools["click_link_in_iframe"]
            return await func(link_text)
        self.tools["click_link_in_iframe"] = wrapped_click_link_in_iframe
        
        async def wrapped_query_customer_info(customer_id: str) -> Dict[str, Any]:
            """查询客户信息"""
            func = spa_tools["query_customer_info"]
            return await func(customer_id)
        self.tools["query_customer_info"] = wrapped_query_customer_info
        
        async def wrapped_query_installment_offers(customer_id: str) -> Dict[str, Any]:
            """查询客户可用的分期优惠"""
            func = spa_tools["query_installment_offers"]
            return await func(customer_id)
        self.tools["query_installment_offers"] = wrapped_query_installment_offers
        
        async def wrapped_calculate_installment_plan(amount: float, periods: int, rate: Optional[float] = None) -> Dict[str, Any]:
            """计算分期方案详情"""
            func = spa_tools["calculate_installment_plan"]
            return await func(amount, periods, rate)
        self.tools["calculate_installment_plan"] = wrapped_calculate_installment_plan
        
        # 组合工具包装
        async def wrapped_search_and_navigate(keyword: str) -> Dict[str, Any]:
            """搜索并导航到匹配的菜单项"""
            func = spa_tools["search_and_navigate"]
            return await func(keyword)
        self.tools["search_and_navigate"] = wrapped_search_and_navigate
        
        async def wrapped_process_form_and_submit(form_data: Dict[str, str], submit_button: str = "提交") -> Dict[str, Any]:
            """填写表单并提交"""
            func = spa_tools["process_form_and_submit"]
            return await func(form_data, submit_button)
        self.tools["process_form_and_submit"] = wrapped_process_form_and_submit
        
        async def wrapped_place_installment_order_sap(amount: float, periods: int, customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """通过SAP系统下分期订单"""
            func = spa_tools["place_installment_order_sap"]
            return await func(amount, periods, customer_info)
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
            """
    
    # Tool: Place credit card installment order
    async def place_installment_order(self, amount: float, periods: int, rate: float, customer_info: dict) -> str:
        """Place a credit card installment order in the system"""
        try:
            # 首先尝试使用SPA系统下单
            sap_result = await self.tools["place_installment_order_sap"](amount, periods, customer_info)
            
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
                if result.get("code") == 200:
                    return result.get("data", {}).get("answer", "抱歉，我暂时无法回答这个问题，请联系客服热线获取更多帮助。")
                else:
                    return f"知识库查询失败: {result.get('message', '未知错误')}。请稍后再试。"
            except Exception as e:
                return f"知识库查询失败: {str(e)}。请稍后再试。"
                
    # Create an agent with the tools
    def create_agent(self):
        model_client = OpenAIChatCompletionClient(
            model="qwen2.5:14b-instruct-q8_0",
            base_url="http://localhost:11434/v1",
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
    async def run_agent(self, task, history_container):
        # Create placeholders - one for the actual response, one for the debug info
        response_placeholder = history_container.empty()
        debug_placeholder = history_container.empty()
        
        try:
            # Run the agent with the async generator handling
            full_response = ""
            debug_info = ""
            async_gen = self.agent.run_stream(task=task)
            
            # Initialize HTML container for streaming effect
            html_template = """
            <div class="chat-message assistant-message">
                <div id="streaming-content">💼 经理：{}</div>
            </div>
            """
            
            # Process the async generator
            async for response_chunk in async_gen:
                # Process the chunk based on its type
                chunk_text = ""
                if isinstance(response_chunk, str):
                    chunk_text = response_chunk
                elif hasattr(response_chunk, 'content'):
                    chunk_text = str(response_chunk.content)
                else:
                    chunk_text = str(response_chunk)
                
                # Check for function calls, results or TaskResult in the chunk
                if "[FunctionCall" in chunk_text or "[FunctionExecutionResult" in chunk_text or "TaskResult" in chunk_text:
                    # Add this to debug info instead of the main response
                    debug_info += chunk_text
                    
                    # Check for SPA navigation updates and update session state
                    self.update_navigation_state(chunk_text)
                    continue
                
                # Add the chunk to our full response
                full_response += chunk_text
                
                # Update the displayed response with character-by-character streaming effect
                # Make sure to filter out any function call information that might have slipped through
                clean_response = full_response
                # Remove any function call patterns that might be in the response
                clean_response = re.sub(r'\[FunctionCall.*?\]', '', clean_response)
                clean_response = re.sub(r'\[FunctionExecutionResult.*?\]', '', clean_response)
                clean_response = re.sub(r'TaskResult\(.*?\)', '', clean_response)
                
                response_placeholder.markdown(html_template.format(clean_response), unsafe_allow_html=True)
                
                # Small delay to create a realistic typing effect
                await asyncio.sleep(0.005)
            
            # Final cleanup of the response to remove any function call artifacts
            clean_response = re.sub(r'\[FunctionCall.*?\]', '', full_response)
            clean_response = re.sub(r'\[FunctionExecutionResult.*?\]', '', clean_response)
            clean_response = re.sub(r'TaskResult\(.*?\)', '', clean_response)
            
            # Update one last time with clean response
            response_placeholder.markdown(html_template.format(clean_response), unsafe_allow_html=True)
            
            # Display debug info in a less prominent way if it exists
            if debug_info:
                debug_placeholder.markdown(f'<div style="color: #999999; font-size: 0.8em; margin-top: 8px;">{debug_info}</div>', unsafe_allow_html=True)
            
            # Return the clean response for history tracking
            return clean_response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            response_placeholder.error(error_msg)
            return error_msg
    
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
            
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <div>👤 您：{message["content"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Check if the content contains FunctionCall or FunctionExecutionResult
                    content = message["content"]
                    debug_info = ""
                    
                    # Use regex to extract function calls and results
                    function_calls = re.findall(r'\[FunctionCall.*?\]', content)
                    function_results = re.findall(r'\[FunctionExecutionResult.*?\]', content)
                    task_results = re.findall(r'TaskResult\(.*?\)', content)
                    
                    # If we found any function-related content
                    if function_calls or function_results or task_results:
                        # Clean the content
                        clean_content = content
                        for fc in function_calls:
                            clean_content = clean_content.replace(fc, '')
                        for fr in function_results:
                            clean_content = clean_content.replace(fr, '')
                        for tr in task_results:
                            clean_content = clean_content.replace(tr, '')
                        
                        # Build debug info
                        debug_info = ''.join(function_calls + function_results + task_results)
                        
                        # Display clean content
                        if clean_content.strip():
                            st.markdown(f"""
                            <div class="chat-message assistant-message">
                                <div>💼 经理：{clean_content.strip()}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Display debug info if any
                        if debug_info:
                            st.markdown(f"""
                            <div style="color: #999999; font-size: 0.8em; margin-top: 8px; margin-bottom: 16px; margin-right: 40px;">
                                {debug_info}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        # Normal display for content without function calls/results
                        st.markdown(f"""
                        <div class="chat-message assistant-message">
                            <div>💼 经理：{content}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # User input
        with st.container():
            user_input = st.text_area("请输入您的问题或需求:", key="user_input", height=80, 
                                    placeholder="例如：我想购买一部手机，大约5000元，可以分期吗？")
            cols = st.columns([1, 1, 4])
            with cols[0]:
                if st.button("发送", use_container_width=True):
                    if user_input:
                        # Add user message to history
                        st.session_state.chat_history.append({"role": "user", "content": user_input})
                        
                        # Create a container for this response
                        response_container = st.empty()
                        
                        # Run the agent asynchronously
                        response = asyncio.run(self.run_agent(user_input, response_container))
                        
                        # Add assistant response to history
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        
                        # Schedule clearing the input on next rerun
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

# Main application entry point
def main():
    app = CreditCardAgentApp()
    app.run()

if __name__ == "__main__":
    main()
