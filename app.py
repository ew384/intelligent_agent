import streamlit as st
import asyncio
import httpx
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
import sys
import os
from pathlib import Path
import time

# Set page config
st.set_page_config(page_title="AutoGen WeChat Assistant", page_icon="💬", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .stTextInput>div>div>input {
        background-color: white;
    }
    .chat-message {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        display: flex;
    }
    .user-message {
        background-color: #DCF8C6;
        margin-left: 40px;
    }
    .assistant-message {
        background-color: #ECECEC;
        margin-right: 40px;
    }
</style>
""", unsafe_allow_html=True)

# Define the wechat_send function
async def wechat_send(name: str, message: str) -> str:
    """Send information by wechat"""
    processed_params = {
        "contact_name": name,
        "message": message
    }
    async with httpx.AsyncClient() as client:
        tool_response = await client.post(
            "http://localhost:8003/tools/wechat/search_and_send",
            json=processed_params,
            timeout=300.0
        )
    return tool_response.json()

# Create an agent with the tools
def create_agent():
    model_client = OpenAIChatCompletionClient(
        model="qwen2.5-coder:7b-instruct-fp16",
        base_url="http://localhost:11434/v1",
        api_key="placeholder",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
        },
    )
    
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[wechat_send],
        system_message="当对话中提到发送信息时,使用工具完成任务，微信联系人提取对话文中的人名。",
    )
    
    return agent

# We don't need the StreamlitMessageCollector class since
# the current version of AutoGen doesn't support message_callback

# Main function to run the agent
async def run_agent(task, history_container):
    agent = create_agent()
    
    # Create a placeholder for streaming response
    response_placeholder = history_container.empty()
    
    try:
        # Run the agent with the async generator handling
        full_response = ""
        async_gen = agent.run_stream(task=task)
        
        # Process the async generator
        async for response_chunk in async_gen:
            # If response_chunk is a string, append it
            if isinstance(response_chunk, str):
                full_response += response_chunk
            # If it's a message object (which is more likely), get its content
            elif hasattr(response_chunk, 'content'):
                full_response += str(response_chunk.content)
            # Otherwise convert it to string
            else:
                full_response += str(response_chunk)
                
            # Update the displayed response
            response_placeholder.markdown(full_response)
        
        # Return the final result for history tracking
        return full_response
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        response_placeholder.error(error_msg)
        return error_msg

# Initialize session state for chat history and input clearing
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
# Check if we need to clear the input from previous run
if "clear_input" in st.session_state and st.session_state.clear_input:
    st.session_state.user_input = ""
    st.session_state.clear_input = False

# App title
st.title("AutoGen WeChat Assistant")
st.markdown("与AI助手对话，发送任务或发微信给联系人")

# Chat container
chat_container = st.container()

# User input
with st.container():
    user_input = st.text_area("输入您的任务:", key="user_input", height=100)
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
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <div>🧑‍💻: {message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <div>🤖: {message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)

# Instructions
with st.expander("使用说明"):
    st.markdown("""
    ### 如何使用:
    1. 在文本框中输入您想要完成的任务
    2. 如果任务涉及发送微信消息，请确保包含联系人信息
    3. 点击"发送"按钮提交任务
    4. AI助手将处理您的请求并在对话框中显示响应
    
    ### 示例任务:
    - 写一首李白的将进酒，写完后使用微信发给联系人：张三
    - 总结今天的天气情况，发微信给李四
    - 写一个会议邀请，发给王五
    
    ### 注意事项:
    - 确保WeChat工具服务在 http://localhost:8003 运行
    - 确保本地AI模型服务在 http://localhost:11434 运行
    """)

# Footer
st.markdown("---")
st.markdown("AutoGen WeChat Assistant © 2025")
