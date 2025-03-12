# 中信银行信用卡分期销售Agent实现指南

## 1. 系统架构

为了将最优提示词模板整合到您的系统中，建议采用以下架构：

```
+---------------------+      +---------------------+      +----------------------+
|                     |      |                     |      |                      |
|  客户标签识别系统    +----->+  提示词模板处理系统  +----->+  Claude API 接口     |
|                     |      |                     |      |                      |
+---------------------+      +---------------------+      +----------------------+
                                      ^                            |
                                      |                            v
                +---------------------+----+      +----------------------+
                |                          |      |                      |
                |  交易处理与业务系统      |<-----+  对话管理系统         |
                |                          |      |                      |
                +-------------------------+      +----------------------+
```

## 2. 接口实现

### 2.1 客户类型识别接口

创建一个函数来识别或接收客户类型：

```python
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
            response = requests.get(f"http://api.internal.bank/customer/{customer_id}/tags")
            if response.status_code == 200:
                tags = response.json().get("tags", [])
                # 根据标签映射客户类型
                tag_to_type = {
                    "price_sensitive": "价格敏感型",
                    "quick_decision": "急速决策型",
                    "relationship": "关系导向型",
                    "hesitant": "犹豫不决型",
                    "knowledgeable": "知识型"
                }
                for tag in tags:
                    if tag in tag_to_type:
                        return tag_to_type[tag]
        except Exception as e:
            logger.error(f"Error calling customer tag API: {e}")
    
    # 默认返回普通客户类型
    return "普通客户"
```

### 2.2 提示词模板处理

创建函数来处理提示词模板：

```python
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
```

### 2.3 Claude API 集成

创建函数来调用Claude API：

```python
from anthropic import AsyncAnthropic

async def chat_with_claude(prompt, messages):
    """
    使用Claude API进行对话
    
    参数:
        prompt: 系统提示词
        messages: 对话历史
        
    返回:
        Claude的回复
    """
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    try:
        response = await client.messages.create(
            model="claude-3-opus-20240229",  # 或其他适合的模型
            max_tokens=1000,
            system=prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        return "很抱歉，系统暂时无法处理您的请求，请稍后再试。"
```

## 3. 后端代码整合

以下是将上述功能整合到后端API的示例代码：

```python
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("credit_card_sales_agent")

app = FastAPI(title="中信银行信用卡分期销售Agent API")

# 客户会话状态
customer_sessions = {}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    amount: Optional[float] = None
    history: Optional[List[ChatMessage]] = None

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """处理聊天请求"""
    # 识别客户类型
    customer_type = identify_customer_type(
        customer_name=request.customer_name,
        customer_id=request.customer_id
    )
    
    # 生成优化的提示词
    prompt = generate_prompt(customer_type, request.amount)
    
    # 准备对话历史
    messages = []
    if request.history:
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
    
    # 添加用户最新消息
    messages.append({"role": "user", "content": request.message})
    
    # 调用Claude API
    response = await chat_with_claude(prompt, messages)
    
    return {"response": response, "customer_type": customer_type}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点处理实时聊天"""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    customer_sessions[session_id] = {"messages": []}
    
    try:
        while True:
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            customer_id = request_data.get("customer_id")
            customer_name = request_data.get("customer_name")
            amount = request_data.get("amount")
            message = request_data.get("message", "")
            
            # 识别客户类型
            customer_type = identify_customer_type(
                customer_name=customer_name,
                customer_id=customer_id
            )
            
            # 生成提示词
            prompt = generate_prompt(customer_type, amount)
            
            # 获取会话历史
            messages = customer_sessions[session_id]["messages"]
            
            # 添加用户消息
            messages.append({"role": "user", "content": message})
            
            # 调用Claude API
            response = await chat_with_claude(prompt, messages)
            
            # 添加助手回复到历史
            messages.append({"role": "assistant", "content": response})
            
            # 保存更新的会话历史
            customer_sessions[session_id]["messages"] = messages
            
            # 发送回复
            await websocket.send_text(json.dumps({
                "response": response,
                "customer_type": customer_type
            }))
            
    except WebSocketDisconnect:
        del customer_sessions[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except:
            pass

# 添加分期交易处理端点
class InstallmentRequest(BaseModel):
    customer_id: str
    customer_name: Optional[str] = None
    amount: float
    period: int
    rate: float

@app.post("/api/installment/process")
async def process_installment(request: InstallmentRequest):
    """处理分期申请"""
    try:
        # 这里调用实际的分期处理系统API
        # 示例实现
        result = {
            "status": "success",
            "transaction_id": f"TX{hash(request.customer_id + str(request.amount))}",
            "amount": request.amount,
            "period": request.period,
            "rate": request.rate,
            "monthly_payment": round(request.amount / request.period + 
                                    (request.amount * request.rate / 100), 2),
            "total_fee": round(request.amount * request.rate / 100, 2),
            "approval_time": "2分钟"
        }
        
        return result
    except Exception as e:
        logger.error(f"Error processing installment: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

## 4. 前端代码整合

以下是修改后的前端代码片段，展示如何将客户类型传递给后端：

```python
# 在前端代码中添加客户信息输入
with st.sidebar:
    st.subheader("客户信息")
    customer_id = st.text_input("客户号", key="customer_id")
    customer_name = st.text_input("客户姓名", key="customer_name")
    amount = st.number_input("分期金额", min_value=1000, max_value=100000, value=15000, step=1000)

# 修改WebSocket初始化函数
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
    ws.on_open = on_open
    
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

# 修改on_open函数
def on_open(ws):
    def run(*args):
        # 包含客户信息和分期金额
        message_data = json.dumps({
            "message": st.session_state.current_query,
            "customer_id": st.session_state.customer_id if "customer_id" in st.session_state else "",
            "customer_name": st.session_state.customer_name if "customer_name" in st.session_state else "",
            "amount": st.session_state.amount if "amount" in st.session_state else 15000
        })
        ws.send(message_data)
    
    threading.Thread(target=run).start()
```

## 5. 监控与改进

为持续优化Agent性能，建议实施以下监控与改进措施：

1. **对话分析**：记录所有客户对话，分析成功率和常见失败点
2. **A/B测试**：对不同客户类型的提示词参数进行小比例调整和测试
3. **人工反馈**：让真实销售人员评价AI回复质量，收集改进建议
4. **对话中断分析**：分析客户终止对话的时间点和原因
5. **成交率跟踪**：按客户类型分析成交率，优化低成交率类型的策略

## 6. 部署注意事项

1. **API密钥安全**：确保Claude API密钥安全存储，使用环境变量而非硬编码
2. **错误处理**：添加全面的错误处理和重试机制
3. **会话管理**：实现robust的会话状态管理，处理连接断开情况
4. **负载均衡**：为高流量场景准备负载均衡策略
5. **监控告警**：设置API使用监控和告警机制

通过以上实现指南，您可以将最