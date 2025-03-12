import os
import sys
from typing import Dict, Any, List, Optional, Union
import asyncio

# 导入模拟LLM API
from mock_llm_api import create_mock_openai_client

# 假设这是你的主应用程序，例如CreditCardAgentApp的修改版
class ModifiedCreditCardAgentApp:
    def __init__(self, use_mock_api=True):
        """
        初始化应用
        
        Args:
            use_mock_api: 是否使用模拟API
        """
        # 设置页面配置等其他初始化...
        
        # 初始化工具和代理
        self.tools = self.setup_tools()
        self.agent = self.create_agent(use_mock_api=use_mock_api)
    
    def setup_tools(self):
        """设置工具函数"""
        # 导入实际的SPA工具函数
        try:
            # 正常导入
            from spa_navigator.integrated_tools import all_tools as spa_tools
            
            # 创建包装器函数...
            tools = {
                "query_knowledge_base": self.query_knowledge_base,
                "place_installment_order": self.place_installment_order
            }
            
            # 添加SPA工具...
            
            return tools
        except ImportError:
            print("警告: 无法导入实际工具，将使用模拟实现")
            # 返回模拟工具
            return self.setup_mock_tools()
    
    def setup_mock_tools(self):
        """设置模拟工具函数"""
        async def mock_get_menu_structure():
            return {"status": "success", "content": {"分期业务": {"submenus": {"分期申请": {}, "账单分期": {}}}}}
        
        async def mock_search_menu_items(keyword):
            return {"status": "success", "content": [{"menu_name": "分期申请", "path": "分期业务 > 分期申请"}]}
        
        async def mock_navigate_to_menu(menu_path):
            return {"status": "success", "message": f"Successfully navigated to {menu_path}"}
        
        async def mock_query_customer_info(customer_id):
            return {
                "status": "success",
                "content": {
                    "id": customer_id,
                    "name": f"测试用户_{customer_id[-4:]}",
                    "card_number": f"6229{customer_id[-4:]}XXXX4598",
                    "available_credit": 30000,
                    "total_credit_limit": 50000
                }
            }
        
        async def mock_calculate_installment_plan(amount, periods, rate=None):
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
        
        # 其他模拟工具函数...
        
        return {
            "get_menu_structure": mock_get_menu_structure,
            "search_menu_items": mock_search_menu_items,
            "navigate_to_menu": mock_navigate_to_menu,
            "query_customer_info": mock_query_customer_info,
            "calculate_installment_plan": mock_calculate_installment_plan,
            "query_knowledge_base": self.query_knowledge_base,
            "place_installment_order": self.place_installment_order
            # 添加其他模拟工具...
        }
    
    async def query_knowledge_base(self, query: str) -> str:
        """模拟知识库查询工具"""
        # 模拟查询结果
        responses = {
            "分期": "我们的分期业务包括消费分期、账单分期和现金分期，期数从3-36期不等，费率从1.2%-18%不等。",
            "费率": "不同期数对应不同费率，例如3期约1.5%，6期约3%，12期约6%，24期约12%。",
            "提前还款": "支持提前还款，但可能无法退还未发生的手续费。提前还款不收取违约金。",
            "default": "抱歉，我暂时无法回答这个问题，请联系客服热线获取更多帮助。"
        }
        
        # 查找匹配的关键词
        for key, response in responses.items():
            if key in query:
                return response
        
        return responses["default"]
    
    async def place_installment_order(self, amount: float, periods: int, rate: float, customer_info: dict) -> str:
        """模拟分期下单工具"""
        # 模拟下单过程
        import random
        import time
        
        order_id = f"INS{int(time.time())}"
        
        return {
            "status": "success",
            "order_id": order_id,
            "message": "分期订单已成功创建，系统处理中，预计10分钟内完成审批。"
        }
    
    def create_agent(self, use_mock_api=True):
        """
        创建代理
        
        Args:
            use_mock_api: 是否使用模拟API
        """
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        if use_mock_api:
            # 使用模拟API
            model_client = self.create_mock_model_client()
        else:
            # 使用实际API
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
        
        # 读取提示模板
        system_prompt = self.read_prompt_template()
        
        # 转换工具字典为列表
        tool_list = list(self.tools.values())
        
        # 创建代理
        agent = AssistantAgent(
            name="assistant",
            model_client=model_client,
            tools=tool_list,
            system_message=system_prompt,
        )
        
        return agent
    
    def create_mock_model_client(self):
        """创建模拟模型客户端"""
        # 导入模拟客户端创建函数
        try:
            # 导入我们的模拟API
            client = create_mock_openai_client()
            print("成功创建模拟OpenAI客户端")
            return client
        except Exception as e:
            print(f"创建模拟客户端失败: {e}")
            # 返回一个最小化的模拟客户端
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            return OpenAIChatCompletionClient(
                model="mock-model",
                base_url="http://localhost:11434/v1",
                api_key="mock-key",
                model_info={
                    "vision": False, 
                    "function_calling": True,
                    "json_output": False,
                    "family": "unknown",
                },
            )
    
    def read_prompt_template(self):
        """读取提示模板"""
        # 模拟读取模板
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

    async def run_agent(self, task, show_debug=True):
        """
        运行代理
        
        Args:
            task: 用户输入任务
            show_debug: 是否显示调试信息
        
        Returns:
            str: 代理响应
        """
        try:
            # 运行代理
            print(f"执行任务: {task}")
            
            # 收集完整响应
            full_response = ""
            async_gen = self.agent.run_stream(task=task)
            
            async for response_chunk in async_gen:
                # 处理响应块
                chunk_text = ""
                if isinstance(response_chunk, str):
                    chunk_text = response_chunk
                elif hasattr(response_chunk, 'content'):
                    chunk_text = str(response_chunk.content)
                else:
                    chunk_text = str(response_chunk)
                
                # 检查是否包含函数调用信息
                if any(marker in chunk_text for marker in ["[FunctionCall", "[FunctionExecutionResult", "TaskResult("]):
                    if show_debug:
                        print(f"调试信息: {chunk_text}")
                    continue
                
                # 添加到完整响应
                full_response += chunk_text
                print(f"收到响应块: {chunk_text}")
            
            print(f"完整响应: {full_response}")
            return full_response
            
        except Exception as e:
            error_msg = f"错误: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def test_interaction(self):
        """测试交互"""
        print("\n===== 开始测试模拟交互 =====\n")
        
        # 测试问题列表
        test_questions = [
            "你好，我想了解一下信用卡分期业务",
            "我想申请5000元的消费分期，可以分12期吗？",
            "这个分期方案每月需要还多少钱？",
            "可以查询一下我的客户信息吗？我的ID是1234567890",
            "我想办理分期，帮我打开分期申请页面"
        ]
        
        for question in test_questions:
            print("\n" + "="*50)
            print(f"用户: {question}")
            print("="*50)
            
            response = await self.run_agent(question)
            
            print("\n")
            print(f"助手: {response}")
            print("-"*50)
            
            # 简单等待，模拟用户阅读时间
            await asyncio.sleep(1)

# 测试运行
async def main():
    app = ModifiedCreditCardAgentApp(use_mock_api=True)
    await app.test_interaction()

if __name__ == "__main__":
    asyncio.run(main())
