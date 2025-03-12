import asyncio
import sys
import json
from typing import Dict, Any
from mock_llm_api import create_mock_openai_client, MockLLMClient

# 模拟工具函数结果以便测试
async def mock_query_customer_info(customer_id: str) -> Dict[str, Any]:
    """模拟查询客户信息函数"""
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

async def mock_place_installment_order_sap(amount: float, periods: int, customer_info=None) -> Dict[str, Any]:
    """模拟SAP下单函数"""
    return {
        "status": "success",
        "message": "分期订单已成功提交",
        "order_id": f"INS12345",
        "details": {
            "amount": amount,
            "periods": periods
        }
    }

async def mock_calculate_installment_plan(amount: float, periods: int, rate: float = None) -> Dict[str, Any]:
    """模拟计算分期方案函数"""
    # 使用标准费率如果未提供
    if rate is None:
        rate = periods * 0.5  # 简单估算
        
    # 计算费用
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

# 构建工具模块字典
mock_tools = {
    "spa_tools": {
        "query_customer_info": mock_query_customer_info,
        "calculate_installment_plan": mock_calculate_installment_plan
    },
    "integrated_tools": {
        "place_installment_order_sap": mock_place_installment_order_sap
    }
}

async def test_chat_completion():
    """测试聊天补全功能"""
    # 创建模拟客户端
    client = MockLLMClient(mock_tools)
    
    # 测试各种用户输入
    test_messages = [
        "你好，我是新客户",
        "我想了解一下分期业务",
        "我想申请5000元的消费分期，分12期",
        "计算5000元分12期的还款明细",
        "请帮我查询客户信息，ID是1234567890",
        "进入分期申请页面",
        "随便说点什么"
    ]
    
    for message in test_messages:
        print("\n" + "="*50)
        print(f"用户: {message}")
        print("="*50)
        
        # 构建消息
        messages = [{"role": "user", "content": message}]
        
        # 调用API
        response = await client.create(messages=messages)
        
        # 打印响应
        choice = response["choices"][0]
        assistant_message = choice["message"]
        print(f"助手: {assistant_message['content']}")
        
        # 如果有函数调用，打印函数调用详情
        if "function_call" in assistant_message:
            function_call = assistant_message["function_call"]
            print(f"\n函数调用: {function_call['name']}")
            print(f"参数: {function_call['arguments']}")
        
        print("-"*50)

async def test_in_autogen_context():
    """测试在类似Autogen环境下使用"""
    # 创建模拟客户端
    client = MockLLMClient(mock_tools)
    
    # 定义一个简单流程，模拟Autogen如何使用LLM客户端
    messages = []
    
    # 初始系统消息
    messages.append({
        "role": "system", 
        "content": "你是中信银行信用卡中心的专业客户经理，负责为客户提供信用卡分期业务咨询和服务。"
    })
    
    # 用户初始问题
    user_message = "你好，我想申请消费分期，大概5000元，可以分12期吗？"
    messages.append({"role": "user", "content": user_message})
    print(f"用户: {user_message}")
    
    # 获取助手响应
    response = await client.create(messages=messages)
    assistant_message = response["choices"][0]["message"]
    messages.append(assistant_message)
    print(f"助手: {assistant_message['content']}")
    
    # 如果有函数调用
    if "function_call" in assistant_message:
        function_call = assistant_message["function_call"]
        print(f"\n执行函数: {function_call['name']}")
        
        # 解析参数
        args = json.loads(function_call["arguments"])
        print(f"参数: {args}")
        
        # 在真实环境中，会调用实际函数
        # 这里我们使用模拟函数
        function_name = function_call["name"]
        if function_name == "place_installment_order_sap":
            result = await mock_place_installment_order_sap(**args)
        elif function_name == "calculate_installment_plan":
            result = await mock_calculate_installment_plan(**args)
        elif function_name == "query_customer_info":
            result = await mock_query_customer_info(**args)
        else:
            result = {"status": "error", "message": f"Unknown function: {function_name}"}
        
        # 添加函数结果到消息历史
        messages.append({
            "role": "function",
            "name": function_name,
            "content": json.dumps(result)
        })
        
        print(f"函数结果: {json.dumps(result, indent=2)}")
        
        # 获取处理函数结果后的响应
        response = await client.create(messages=messages)
        final_message = response["choices"][0]["message"]
        messages.append(final_message)
        print(f"\n助手最终回复: {final_message['content']}")
    
    # 用户后续问题
    user_message = "这个分期方案的每月还款金额是多少？"
    messages.append({"role": "user", "content": user_message})
    print(f"\n用户: {user_message}")
    
    # 获取助手响应
    response = await client.create(messages=messages)
    assistant_message = response["choices"][0]["message"]
    messages.append(assistant_message)
    print(f"助手: {assistant_message['content']}")

async def main():
    """主函数"""
    print("\n===== 测试聊天对话 =====")
    await test_chat_completion()
    
    print("\n\n===== 测试在Autogen环境中使用 =====")
    await test_in_autogen_context()

if __name__ == "__main__":
    asyncio.run(main())