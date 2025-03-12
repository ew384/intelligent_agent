# -*- coding: utf-8 -*-
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging
import uuid
from anthropic import AsyncAnthropic
import requests
import os
import uvicorn


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("credit_card_sales_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("credit_card_sales_agent")
app = FastAPI(title="中信银行信用卡分期客服营销Agent")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义API模型
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    history: Optional[List[ChatMessage]] = None

class InstallmentRequest(BaseModel):
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    amount: float
    period: int
    rate: float
# Simulate an HTTP response object
class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

# 客户会话状态
customer_sessions = {}
def identify_customer_type(customer_name=None, customer_id=None, customer_history=None):
    """
    识别客户类型或从外部API获取客户类型

    参数:
        customer_name: 客户姓名
        customer_id: 客户号
        customer_history: 客户历史交易数据

    返回:
        客户类型: str, 如 "价格敏感型", "关系导向型" 等
    """
    # 这里是示例实现，实际可能是调用外部API
    if customer_history is not None:
        # 基于历史分析客户类型
        if customer_history.get("price_inquiries", 0) > 5:
            return "价格敏感型"
        elif customer_history.get("avg_decision_time", 1000) < 60:  # 小于60分钟
            return "急速决策型"
        # ... 其他逻辑

    # 如果有客户ID，调用外部API
    if customer_id is not None:
        try:
            # 调用外部客户标签API
            #response = requests.get(f"http://api.internal.bank/customer/{customer_id}/tags")
            tag_to_type = {
                    "price_sensitive": "价格敏感型",
                    "quick_decision": "急速决策型",
                    "relationship": "关系导向型",
                    "hesitant": "犹豫不决型",
                    "knowledgeable": "知识型"
                }
            response_data = {"status_code": 200, "tags": "price_sensitive"}
            response = MockResponse(status_code=200, json_data=response_data)
            if response.status_code == 200:
                tags = response.json().get("tags", [])
                # 根据标签映射客户类型
                for tag in tags:
                    if tag in tag_to_type:
                        return tag_to_type[tag]
        except Exception as e:
            logger.error(f"Error calling customer tag API: {e}")

    # 默认返回普通客户类型
    return "普通客户"

def generate_prompt(customer_type, amount=None, period=None):
    """
    基于客户类型和交易信息生成最优提示词
    
    参数:
        customer_type: 客户类型
        amount: 分期金额(可选)
        period: 分期期数(可选)
        
    返回:
        处理后的提示词
    """
    # 加载提示词模板
    with open("optimized_prompt_template.md", "r", encoding="utf-8") as f:
        template = f.read()
    
    # 获取该客户类型的费率信息
    rate_info = get_rate_info(customer_type)
    
    # 计算还款示例(如果提供了金额)
    payment_examples = {}
    if amount is not None:
        payment_examples = calculate_payment_examples(amount, rate_info)
    
    # 替换模板中的变量
    prompt = template.replace("{{customer_type}}", customer_type)
    
    # 替换费率相关变量
    if amount is not None:
        for key, value in payment_examples.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
    
    return prompt

def get_rate_info(customer_type):
    """获取特定客户类型的费率信息"""
    # 客户类型对应的初始费率和最低费率(标准费率的百分比)
    rate_info = {
        "价格敏感型": {"initial": 0.95, "minimum": 0.85},
        "急速决策型": {"initial": 0.90, "minimum": 0.88},
        "关系导向型": {"initial": 0.92, "minimum": 0.87},
        "犹豫不决型": {"initial": 0.93, "minimum": 0.88},
        "知识型": {"initial": 0.90, "minimum": 0.86},
        "普通客户": {"initial": 0.94, "minimum": 0.87}
    }
    
    # 标准费率
    standard_rates = {3: 0.03, 6: 0.06, 12: 0.09, 24: 0.15}
    
    # 计算实际费率
    result = {}
    for period, std_rate in standard_rates.items():
        initial = std_rate * rate_info.get(customer_type, rate_info["普通客户"])["initial"]
        minimum = std_rate * rate_info.get(customer_type, rate_info["普通客户"])["minimum"]
        result[period] = {"initial": initial, "minimum": minimum}
    
    return result

def calculate_payment_examples(amount, rate_info):
    """计算还款示例"""
    examples = {}
    
    for period in [3, 6, 12, 24]:
        rate = rate_info[period]["initial"]
        total_fee = amount * rate
        monthly_principal = amount / period
        monthly_fee = total_fee / period
        monthly_payment = monthly_principal + monthly_fee
        
        examples[f"{period}期费率"] = round(rate * 100, 2)
        examples[f"月供{period}期"] = round(monthly_payment, 2)
        examples[f"手续费{period}期"] = round(total_fee, 2)
    
    # 添加其他可能用到的变量
    examples["分期金额"] = amount
    examples["月手续费"] = round(examples["手续费12期"] / 12, 2)
    examples["日手续费"] = round(examples["月手续费"] / 30, 2)
    
    # 计算让步后的费率(用于谈判)
    for period in [3, 6, 12, 24]:
        mid_rate = (rate_info[period]["initial"] + rate_info[period]["minimum"]) / 2
        examples[f"让步后费率_{period}期"] = round(mid_rate * 100, 2)
    
    return examples

async def chat_with_sales_agent(user_message: str,
                              customer_type: str = "普通客户",
                              amount: float = None,
                              dialogue_history: List[Dict] = None):
    """
    与销售Agent进行对话

    参数:
        user_message: 用户输入的消息
        customer_type: 客户类型标签
        amount: 分期金额(可选)
        dialogue_history: 之前的对话历史

    返回:
        销售Agent的回复
    """
    # 生成针对特定客户类型的销售提示词
    sales_prompt = generate_prompt(customer_type, amount)

    # 准备对话历史
    messages = []
    if dialogue_history:
        for msg in dialogue_history:
            if msg["role"] == "user" and msg["content"].strip():
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant" and msg["content"].strip():
                messages.append({"role": "assistant", "content": msg["content"]})

    # 添加用户的最新消息
    if user_message and user_message.strip():
        messages.append({"role": "user", "content": user_message})

    # 确保有至少一条有效消息
    if not messages:
        messages.append({"role": "user", "content": "您好，我想了解一下信用卡分期。"})

    # 调用Claude API
    try:
        client = AsyncAnthropic(api_key="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")
        response = await client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            system=sales_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        return "抱歉，系统暂时无法处理您的请求，请稍后再试。"


# REST API端点
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """处理chat请求的REST API端点"""
    try:
        # 识别客户类型
        customer_type = identify_customer_type(
            customer_name=request.customer_name,
            customer_id=request.customer_id
        )

        # 准备对话历史
        dialogue_history = []
        if request.history:
            for msg in request.history:
                dialogue_history.append({"role": msg.role, "content": msg.content})

        # 与销售Agent对话
        response = await chat_with_sales_agent(
            user_message=request.message,
            customer_type=customer_type,
            amount=request.amount,
            dialogue_history=dialogue_history
        )

        return {
            "response": response,
            "customer_type": customer_type
        }
    except Exception as e:
        logger.error(f"API error: {e}")
        return {"error": str(e)}


# 定义WebSocket连接管理器

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.logger = logging.getLogger("connection_manager")

    async def connect(self, websocket: WebSocket) -> str:
        """连接WebSocket并返回会话ID"""
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        self.logger.info(f"New connection accepted: {session_id}")
        return session_id

    def disconnect(self, session_id: str):
        """断开WebSocket连接"""
        if session_id in self.active_connections:
            self.logger.info(f"Connection removed: {session_id}")
            del self.active_connections[session_id]
        else:
            self.logger.warning(f"Attempted to disconnect non-existent session: {session_id}")

    async def send_message(self, session_id: str, message: str):
        """向特定会话发送消息"""
        if session_id in self.active_connections:
            try:
                self.logger.info(f"Sending message to {session_id}: {message[:100]}...")
                await self.active_connections[session_id].send_text(message)
                self.logger.info(f"Message sent to {session_id}")
                return True
            except Exception as e:
                self.logger.error(f"Error sending message to {session_id}: {e}")
                # 如果发送失败，可能连接已断开，清理它
                self.disconnect(session_id)
                return False
        else:
            self.logger.warning(f"Attempted to send message to non-existent session: {session_id}")
            return False

    async def broadcast(self, message: str):
        """向所有连接的客户端广播消息"""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        # 清理断开的连接
        for session_id in disconnected:
            self.disconnect(session_id)

manager = ConnectionManager()

# WebSocket端点用于实时通信
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点处理实时聊天"""
    session_id = await manager.connect(websocket)

    # 初始化会话状态
    if session_id not in customer_sessions:
        customer_sessions[session_id] = {
            "dialogue_history": [],
            "customer_type": "普通客户",
            "customer_id": None,
            "customer_name": None,
            "amount": None
        }

    try:
        while True:
            data = await websocket.receive_text()
            try:
                request_data = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_message(session_id, json.dumps({
                    "type": "error",
                    "content": "无效的JSON格式"
                }))
                continue
            logger.info(f"Parsed request data: {json.dumps(request_data,ensure_ascii=False)}")

            # 从请求中获取信息
            customer_id = request_data.get("customer_id")
            customer_name = request_data.get("customer_name")
            amount = request_data.get("amount")
            message = request_data.get("message", "")

            # 更新会话状态
            if customer_id:
                customer_sessions[session_id]["customer_id"] = customer_id
            if customer_name:
                customer_sessions[session_id]["customer_name"] = customer_name
            if amount:
                customer_sessions[session_id]["amount"] = amount

            # 识别客户类型
            customer_type = identify_customer_type(
                customer_name=customer_sessions[session_id].get("customer_name"),
                customer_id=customer_sessions[session_id].get("customer_id")
            )
            customer_sessions[session_id]["customer_type"] = customer_type

            # 发送"正在输入"状态
            await manager.send_message(session_id, json.dumps({
                "type": "typing",
                "content": "正在输入..."
            }))

            # 与销售Agent对话
            response = await chat_with_sales_agent(
                user_message=message,
                customer_type=customer_type,
                amount=customer_sessions[session_id].get("amount"),
                dialogue_history=customer_sessions[session_id]["dialogue_history"]
            )

            # 更新对话历史
            customer_sessions[session_id]["dialogue_history"].append(
                {"role": "user", "content": message}
            )
            customer_sessions[session_id]["dialogue_history"].append(
                {"role": "assistant", "content": response}
            )

            # 记录发送的响应
            logger.info(f"Sending response to {session_id}, response: {response}")
            
            # 发送回复前记录数据
            response_data = json.dumps({
                "type": "message",
                "content": response,
                "customer_type": customer_type
            },ensure_ascii=False)
            
            # 发送回复
            await manager.send_message(session_id, response_data)
            logger.info(f"Response sent to {session_id}. Response:{response_data}")

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        # 保留会话状态一段时间，以便用户重新连接
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_message(session_id, json.dumps({
                "type": "error",
                "content": "系统错误，请刷新页面重试"
            },ensure_ascii=False))
        except:
            pass

async def process_installment(amount: float, periods: int, rate: float, customer_name: str = None) -> str:
    """处理信用卡分期交易"""
    # 这是一个dummy实现，后续可以替换为实际的系统调用
    processed_params = {
        "amount": amount,
        "periods": periods,
        "rate": rate,
        "customer_name": customer_name or "客户",
        "status": "success",
        "transaction_id": f"TX{hash(f'{amount}{periods}{customer_name}') % 1000000:06d}",
        "monthly_payment": round(amount / periods + (amount * rate / 100), 2),
        "total_fee": round(amount * rate / 100, 2),
        "approval_time": "2分钟",
        "processing_time": "立即"
    }

    # 模拟API调用延迟
    await asyncio.sleep(1)
    return json.dumps(processed_params)

@app.post("/api/installment/process")
async def process_installment_request(request: InstallmentRequest):
    """处理分期申请的API端点"""
    try:
        result = await process_installment(
            amount=request.amount,
            periods=request.period,
            rate=request.rate,
            customer_name=request.customer_name
        )

        # 解析JSON字符串为字典
        result_dict = json.loads(result)

        return result_dict
    except Exception as e:
        logger.error(f"Error processing installment: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    """API根路径，返回简单的欢迎信息"""
    return {
        "name": "中信银行信用卡分期系统API",
        "version": "1.0",
        "endpoints": [
            "/api/chat - 聊天接口",
            "/api/installment/process - 分期处理接口",
            "/ws/chat - WebSocket聊天接口"
        ]
    }
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
