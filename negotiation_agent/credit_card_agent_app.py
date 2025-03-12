import streamlit as st
import asyncio
import httpx
import json
import re
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
import sys
import os
from pathlib import Path
import time

# Set page config
st.set_page_config(
    page_title="中信银行信用卡中心",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Read the sales agent prompt template
def read_prompt_template():
    try:
        with open("./agent_negotiation/optimized_prompt_template.md", "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading prompt template: {e}")
        return "Error loading prompt template"

# Tool: Place credit card installment order
async def place_installment_order(amount: float, periods: int, rate: float, customer_info: dict) -> str:
    """Place a credit card installment order in the system"""
    # This is a placeholder function for now
    # In the real implementation, this would call your order system API
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
async def query_knowledge_base(query: str) -> str:
    """Query the knowledge base to answer customer questions"""
    processed_params = {
        "query": query,
        "collection": "credit_card_faq"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8004/rag/query",
                json=processed_params,
                timeout=30.0
            )
            result = response.json()
            return result.get("answer", "抱歉，我暂时无法回答这个问题，请联系客服热线获取更多帮助。")
        except Exception as e:
            return f"知识库查询失败: {str(e)}。请稍后再试。"

# Create an agent with the tools
def create_agent():
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
    system_prompt = read_prompt_template()
    
    # Add tool usage instructions to the system prompt
    tool_instructions = """
## 工具使用规则

在与客户交互时，请遵循以下工具使用规则：

1. **知识库查询工具 (query_knowledge_base)**:
   - 当客户询问关于信用卡、分期政策、费率计算等知识性问题时使用
   - 例如："中信银行信用卡有哪些权益？"、"分期还款会影响我的信用记录吗？"
   - 使用方式：将客户问题作为参数调用query_knowledge_base工具

2. **订单下单工具 (place_installment_order)**:
   - 当客户明确表示同意办理分期业务，并且已经确认金额、期数和费率时使用
   - 必须先确认客户已经同意办理，再调用此工具
   - 使用方式：将分期金额、期数、费率和客户信息作为参数调用place_installment_order工具

请根据对话上下文和客户需求，灵活使用这些工具以提供最佳服务。始终保持专业且热情的服务态度。
"""
    
    system_prompt = system_prompt + "\n\n" + tool_instructions
    
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[query_knowledge_base, place_installment_order],
        system_message=system_prompt,
    )
    
    return agent

# Main function to run the agent with streaming output
async def run_agent(task, history_container):
    agent = create_agent()
    
    # Create placeholders - one for the actual response, one for the debug info
    response_placeholder = history_container.empty()
    debug_placeholder = history_container.empty()
    
    try:
        # Run the agent with the async generator handling
        full_response = ""
        debug_info = ""
        async_gen = agent.run_stream(task=task)
        
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
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        response_placeholder.error(error_msg)
        return error_msg

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
    
# Check if we need to clear the input from previous run
if "clear_input" in st.session_state and st.session_state.clear_input:
    st.session_state.user_input = ""
    st.session_state.clear_input = False

# Sidebar for configuration
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

# Chat container
chat_container = st.container()

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
                response = asyncio.run(run_agent(user_input, response_container))
                
                # Add assistant response to history
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                # Schedule clearing the input on next rerun
                st.session_state.clear_input = True
                st.rerun()
    
    with cols[1]:
        if st.button("清空对话", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

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

# Instructions in an expander
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

# Footer
st.markdown("---")
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center;">
    <span>中信银行信用卡中心</span>
    <span>客服热线：400-888-8888</span>
</div>
""", unsafe_allow_html=True)
