# -*- coding: utf-8 -*-
import streamlit as st
import json
import websocket
import threading
import time
from typing import List, Dict
import requests

# 设置页面配置
st.set_page_config(page_title="中信银行信用卡分期系统", page_icon="💳", layout="wide")

# 自定义CSS
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
    .streaming-container {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        background-color: #ECECEC;
        margin-right: 40px;
    }
    .header-container {
        display: flex;
        align-items: center;
        padding: 10px;
        background-color: #E41B23;
        color: white;
        margin-bottom: 20px;
    }
    .header-logo {
        font-size: 24px;
        font-weight: bold;
        margin-right: 10px;
    }
    .header-title {
        font-size: 20px;
    }
    .card-info {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid #E41B23;
    }
</style>
""", unsafe_allow_html=True)

# 配置API端点
API_HOST = "localhost"
API_PORT = 8080
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
WS_URL = f"ws://{API_HOST}:{API_PORT}/ws/chat"

# 初始化会话状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "websocket" not in st.session_state:
    st.session_state.websocket = None
    
if "response_container" not in st.session_state:
    st.session_state.response_container = None
    
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False
    
if "current_query" not in st.session_state:
    st.session_state.current_query = ""

if "current_response" not in st.session_state:
    st.session_state.current_response = ""

if "clear_input" not in st.session_state:
    st.session_state.clear_input = False
    

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received message: {json.dumps(data, ensure_ascii=False, indent=2)}")
    message_type = data.get("type")
    content = data.get("content", "")

    if message_type == "typing":
        # 显示"正在输入"状态
        streaming_container = st.empty()
        streaming_container.markdown(f"""
        <div class="streaming-container">
            <div>🏦: {content}</div>
        </div>
        """, unsafe_allow_html=True)

    elif message_type == "message":
        # 接收完整消息
        st.session_state.current_response = content
        st.session_state.chat_history.append({"role": "assistant", "content": content})
        st.session_state.is_streaming = False
        # 触发页面刷新
        st.rerun()

    elif message_type == "chunk":  # 保留原有逻辑，以防后端修改为chunk模式
        # 增量添加到当前响应
        st.session_state.current_response += content
        # 通过会话状态触发重绘
        st.session_state.last_update = time.time()

    elif message_type == "complete":  # 保留原有逻辑，以防后端修改为complete模式
        # 完成响应
        st.session_state.current_response = content
        st.session_state.chat_history.append({"role": "assistant", "content": content})
        st.session_state.is_streaming = False
        # 触发页面刷新
        st.rerun()

    elif message_type == "error":
        st.session_state.is_streaming = False
        st.session_state.current_response = f"错误: {content}"
        st.session_state.chat_history.append({"role": "assistant", "content": f"错误: {content}"})
        st.rerun()

def on_error(ws, error):
    st.session_state.is_streaming = False
    st.session_state.current_response = f"连接错误: {str(error)}"
    st.session_state.chat_history.append({"role": "assistant", "content": f"连接错误: {str(error)}"})
    st.rerun()

def on_close(ws, close_status_code, close_msg):
    st.session_state.is_streaming = False
    if close_status_code or close_msg:
        st.session_state.current_response = f"连接已关闭: {close_status_code} {close_msg}"
    
# 在前端代码中添加客户信息输入
with st.sidebar:
    st.subheader("客户信息")
    customer_id = st.text_input("客户号", key="customer_id")
    customer_name = st.text_input("客户姓名", key="customer_name")
    amount = st.number_input("分期金额", min_value=1000, max_value=100000, value=15000, step=1000)


def init_websocket(user_message):
    # 存储当前查询
    st.session_state.current_query = user_message

    # 创建WebSocket连接
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # 使用闭包捕获用户消息
    def on_open_with_message(ws):
        def run(*args):
            # 直接使用传入的user_message，不依赖session_state
            message_data = json.dumps({
                "message": user_message, 
                "customer_id": st.session_state.customer_id if "customer_id" in st.session_state else "",
                "customer_name": st.session_state.customer_name if "customer_name" in st.session_state else "",
                "amount": st.session_state.amount if "amount" in st.session_state else 15000
            })
            logger.info(f"Sending message data: {message_data}")
            ws.send(message_data)
        threading.Thread(target=run).start()
    ws.on_open = on_open_with_message

    # 在后台线程中运行WebSocket
    def run_ws():
        ws.run_forever()

    wst = threading.Thread(target=run_ws)
    wst.daemon = True
    wst.start()

    # 保存WebSocket引用
    st.session_state.websocket = ws

    # 设置为流式传输模式
    st.session_state.is_streaming = True
    st.session_state.current_response = ""

def on_open(ws):
    print("WebSocket connection opened")
    def run(*args):
        # 包含客户信息和分期金额
        print(f"current_query in session state: '{st.session_state.current_query if 'current_query' in st.session_state else 'NOT SET'}'")
        message_data = json.dumps({
            "message": st.session_state.current_query if "current_query" in st.session_state else "",
            "customer_id": st.session_state.customer_id if "customer_id" in st.session_state else "",
            "customer_name": st.session_state.customer_name if "customer_name" in st.session_state else "",
            "amount": st.session_state.amount if "amount" in st.session_state else 15000
        })
        print(f"Sending message: {message_data}")
        ws.send(message_data)

    threading.Thread(target=run).start()


# 直接API调用函数（非流式）
def call_chat_api(message):
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={"message": message},
            timeout=300
        )
        return response.json().get("response", "无响应")
    except Exception as e:
        return f"API错误: {str(e)}"

# 应用标题与LOGO
st.markdown("""
<div class="header-container">
    <div class="header-logo">💳</div>
    <div class="header-title">中信银行信用卡中心</div>
</div>
""", unsafe_allow_html=True)

# 信用卡分期信息卡片
st.markdown("""
<div class="card-info">
    <h3>信用卡分期产品优势</h3>
    <p>💰 灵活分期: 3-24期自由选择</p>
    <p>🔥 低至1.5%手续费率</p>
    <p>⚡ 秒批秒到账</p>
    <p>🛡️ 额度单独计算，不占用常规额度</p>
</div>
""", unsafe_allow_html=True)

# 聊天容器
chat_container = st.container()

# 显示聊天历史
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <div>👨‍💼: {message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <div>🏦: {message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # 显示正在流式传输的响应
    if st.session_state.is_streaming:
        streaming_container = st.empty()
        streaming_container.markdown(f"""
        <div class="streaming-container">
            <div>🏦: {st.session_state.current_response}</div>
        </div>
        """, unsafe_allow_html=True)

# 用户输入
# 在脚本开始处检查 is_streaming 状态
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False

# 使用会话状态来跟踪按钮点击
if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False

def set_button_clicked():
    st.session_state.button_clicked = True

with st.container():
    # 检查是否需要清除输入
    if "clear_input" in st.session_state and st.session_state.clear_input:
        st.session_state.user_input = ""
        st.session_state.clear_input = False
    user_input = st.text_area("请输入您的问题:", key="user_input", height=100,
                            placeholder="例如: 我想分期购买一台15,000元的笔记本电脑，想了解一下分期方案...")
    cols = st.columns([1, 1, 4])
    print(user_input)
    # 在UI部分
    with cols[0]:
        # 使用 on_click 处理函数来设置状态
        send_button = st.button("发送", use_container_width=True, on_click=set_button_clicked, disabled=st.session_state.is_streaming)
    
    # 在脚本末尾检查按钮状态并处理
    if st.session_state.button_clicked and user_input:
        print("*"*100)
        # 添加用户消息到历史
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.current_query = user_input
        print(f"Setting current_query to: '{user_input}'")
        # 创建WebSocket连接并开始流式传输
        init_websocket(user_input)
        # 安排在下次重新运行时清除输入
        st.session_state.clear_input = True
        # 重置按钮状态
        st.session_state.button_clicked = False
        st.rerun()
# 分期计算器小工具
with st.expander("分期计算器"):
    col1, col2 = st.columns(2)
    
    with col1:
        calc_amount = st.number_input("分期金额(元)", min_value=1000, max_value=100000, value=15000, step=1000)
        calc_period = st.selectbox("分期期数", [3, 6, 12, 24], index=2)
    
    with col2:
        # 根据期数显示不同的默认费率
        default_rates = {3: 3.0, 6: 6.0, 12: 9.0, 24: 15.0}
        calc_rate = st.number_input("手续费率(%)", min_value=1.0, max_value=18.0, value=default_rates[calc_period], step=0.1)
        st.write("标准费率: {}%".format(default_rates[calc_period]))
    
    # 计算结果
    total_fee = calc_amount * calc_rate / 100
    monthly_principal = calc_amount / calc_period
    monthly_fee = total_fee / calc_period
    monthly_payment = monthly_principal + monthly_fee
    
    st.markdown(f"""
    #### 计算结果
    - 总手续费: **{total_fee:.2f}** 元
    - 每月还款: **{monthly_payment:.2f}** 元 (本金 {monthly_principal:.2f} + 手续费 {monthly_fee:.2f})
    - 总还款额: **{calc_amount + total_fee:.2f}** 元
    """)
    
    if st.button("咨询此方案", use_container_width=True):
        query = f"我想办理{calc_amount}元的{calc_period}期分期，想了解一下手续费率"
        st.session_state.chat_history.append({"role": "user", "content": query})
        init_websocket(query)
        st.rerun()

# 使用说明
with st.expander("使用说明"):
    st.markdown("""
    ### 如何使用:
    1. 在文本框中输入您的分期需求
    2. 点击"发送"按钮提交咨询
    3. 与中信银行信用卡中心客服进行实时对话
    4. 可以使用分期计算器快速了解各期数的还款情况
    
    ### 可咨询内容:
    - 信用卡分期产品介绍
    - 分期手续费率查询
    - 分期申请流程
    - 分期优惠活动
    - 特殊商户分期
    
    ### 温馨提示:
    - 本系统支持多轮对话，可以进行讨价还价
    - 最终分期方案需以系统审批为准
    - 分期成功后资金将直接入账
    """)

# 页脚
st.markdown("---")
st.markdown("中信银行信用卡分期服务中心 © 2025")

# 添加自动刷新以获取流式更新
if st.session_state.is_streaming:
    time.sleep(0.5)  # 短暂延迟
    st.rerun()
