import asyncio
import json
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from anthropic import AsyncAnthropic
import os
import logging
from tqdm import tqdm
import pickle

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agent_optimizer")

# 定义常量

RESULTS_DIR = "optimization_results"
PROMPTS_DIR = "optimized_prompts"

# 确保结果目录存在
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(PROMPTS_DIR, exist_ok=True)

#########################
# 参数化提示词模板
#########################

class PromptParams:
    """可优化的提示词参数类"""
    
    def __init__(self, 
                 aggression_level: float = 5.0,
                 concession_threshold: int = 3,
                 anchoring_level: float = 0.2,
                 emotional_appeal: float = 5.0,
                 focus_on_benefits: float = 5.0,
                 time_pressure: float = 5.0,
                 risk_tolerance: float = 5.0,
                 cross_selling: float = 3.0):
        """
        初始化提示词参数
        
        参数:
            aggression_level: 销售积极度 (1-10)
            concession_threshold: 让步阈值，客户拒绝多少次后进行让步 (1-5)
            anchoring_level: 价格锚定因子，初始报价比最低价高出的百分比 (0.05-0.5)
            emotional_appeal: 情感诉求强度 (1-10)
            focus_on_benefits: 关注产品利益点的程度 (1-10)
            time_pressure: 施加时间压力的程度 (1-10)
            risk_tolerance: 接受风险的程度 (1-10)
            cross_selling: 交叉销售的积极度 (1-10)
        """
        self.aggression_level = aggression_level
        self.concession_threshold = concession_threshold
        self.anchoring_level = anchoring_level
        self.emotional_appeal = emotional_appeal
        self.focus_on_benefits = focus_on_benefits
        self.time_pressure = time_pressure
        self.risk_tolerance = risk_tolerance
        self.cross_selling = cross_selling
    
    def to_dict(self) -> Dict[str, Any]:
        """将参数转换为字典"""
        return {
            "aggression_level": self.aggression_level,
            "concession_threshold": self.concession_threshold,
            "anchoring_level": self.anchoring_level,
            "emotional_appeal": self.emotional_appeal,
            "focus_on_benefits": self.focus_on_benefits,
            "time_pressure": self.time_pressure,
            "risk_tolerance": self.risk_tolerance,
            "cross_selling": self.cross_selling
        }
    
    @classmethod
    def from_dict(cls, params_dict: Dict[str, Any]) -> 'PromptParams':
        """从字典创建参数对象"""
        return cls(**params_dict)
        
    def mutate(self, mutation_rate: float = 0.2) -> 'PromptParams':
        """产生一个变异的参数集"""
        return PromptParams(
            aggression_level = max(1.0, min(10.0, self.aggression_level + random.gauss(0, mutation_rate * 3))),
            concession_threshold = max(1, min(5, self.concession_threshold + random.choice([-1, 0, 1]))),
            anchoring_level = max(0.05, min(0.5, self.anchoring_level + random.gauss(0, mutation_rate * 0.1))),
            emotional_appeal = max(1.0, min(10.0, self.emotional_appeal + random.gauss(0, mutation_rate * 3))),
            focus_on_benefits = max(1.0, min(10.0, self.focus_on_benefits + random.gauss(0, mutation_rate * 3))),
            time_pressure = max(1.0, min(10.0, self.time_pressure + random.gauss(0, mutation_rate * 3))),
            risk_tolerance = max(1.0, min(10.0, self.risk_tolerance + random.gauss(0, mutation_rate * 3))),
            cross_selling = max(1.0, min(10.0, self.cross_selling + random.gauss(0, mutation_rate * 3))),
        )
    
    def crossover(self, other: 'PromptParams') -> 'PromptParams':
        """与另一个参数集进行交叉"""
        # 随机选择父母的参数
        child_params = {}
        for key in self.to_dict().keys():
            # 70%概率从第一个父母继承，30%从第二个父母继承
            if random.random() < 0.7:
                child_params[key] = getattr(self, key)
            else:
                child_params[key] = getattr(other, key)
                
        return PromptParams.from_dict(child_params)
        
    def generate_sales_prompt(self) -> str:
        """根据参数生成销售人员的系统提示词"""
        # 根据锚定程度调整初始费率
        base_rates = {
            3: 3.0,
            6: 6.0,
            12: 9.0,
            24: 15.0
        }
        
        # 调整后的费率（用于内部决策，不直接呈现给客户）
        adjusted_rates = {
            period: rate * (1 + self.anchoring_level) 
            for period, rate in base_rates.items()
        }
        
        # 构建策略指导
        strategies = []
        
        # 基于积极度的策略
        if self.aggression_level > 7:
            strategies.append("坚定地推荐更长期限、更高利润的分期方案")
            strategies.append("在谈判中保持主动，引导客户接受你的建议")
        elif self.aggression_level > 4:
            strategies.append("平衡推荐各期限方案，但侧重于12期及以上")
            strategies.append("适度引导客户，但也要根据客户反应调整策略")
        else:
            strategies.append("根据客户需求推荐合适方案，更注重客户满意度")
            strategies.append("采取顺应式谈判，以客户需求为主导")
            
        # 基于让步阈值的策略
        strategies.append(f"客户拒绝{self.concession_threshold}次后，考虑适度让步")
        
        # 基于情感诉求的策略
        if self.emotional_appeal > 7:
            strategies.append("强调分期对客户生活品质的提升")
            strategies.append("使用情感化语言描述产品体验")
        elif self.emotional_appeal > 4:
            strategies.append("适度结合理性分析和情感诉求")
        else:
            strategies.append("侧重于数据和事实，少用情感化语言")
            
        # 基于时间压力的策略
        if self.time_pressure > 7:
            strategies.append("强调'限时优惠'和'今日特批'等时间限制")
            strategies.append("创造一种'稍纵即逝'的机会感")
        elif self.time_pressure > 4:
            strategies.append("提及优惠有效期，但不过度强调")
        else:
            strategies.append("给客户充分的考虑时间，不施加时间压力")
            
        # 基于交叉销售的策略
        if self.cross_selling > 7:
            strategies.append("积极推荐相关的信用卡增值服务和保险产品")
        elif self.cross_selling > 4:
            strategies.append("在合适时机提及相关产品，但不强求")
        else:
            strategies.append("专注于分期业务，很少提及其他产品")
            
        # 将策略组合成文本
        strategy_text = "\n".join([f"- {s}" for s in strategies])
            
        # 生成完整的提示词
        prompt = f"""你是中信银行信用卡中心的李经理，一名专业的信用卡分期营销人员。你的任务是与客户沟通，推荐合适的信用卡分期方案，争取最大化公司利润。

你的销售风格参数:
- 积极度: {self.aggression_level}/10
- 让步阈值: 客户拒绝{self.concession_threshold}次后考虑让步
- 价格锚定: 初始报价比标准费率高{int(self.anchoring_level*100)}%
- 情感诉求: {self.emotional_appeal}/10
- 产品利益关注度: {self.focus_on_benefits}/10
- 时间压力营造: {self.time_pressure}/10
- 风险接受度: {self.risk_tolerance}/10
- 交叉销售积极度: {self.cross_selling}/10

你的销售目标是:
1. 了解客户分期需求和预算
2. 推荐合适的分期产品，优先推荐12期或24期
3. 尽量保持较高的手续费率，最低不低于标准费率的85%
4. 促成交易并完成订单

分期费率信息:
- 3期: 1.5%-3% (标准费率3%)
- 6期: 3%-6% (标准费率6%)
- 12期: 6%-12% (标准费率9%)
- 24期: 12%-18% (标准费率15%)

你的折扣权限最高为标准费率的85%。

谈判策略指导:
{strategy_text}

谈判经验:
- 当客户提到"预算有限"时，重点强调分期的月度压力小，而非总成本
- 当客户比较多家银行费率时，强调我行的服务质量和额外权益
- 客户通常会在第二次让步后接受方案，所以第一次让步不要超过30%权限
- 引导客户关注总体方案价值，而非单一费率数字

开始与客户对话时，保持专业、热情，主动询问客户的需求。"""

        return prompt
    
    def generate_customer_prompt(self, scenario: Dict[str, Any]) -> str:
        """根据参数和场景生成客户的系统提示词"""
        
        prompt = f"""你是{scenario['customer_name']}，一位正在考虑信用卡分期的客户。{scenario['background']}

你的情况是:
1. 月收入约{scenario['monthly_income']}元，每月可用于还款的金额不超过{scenario['max_monthly_payment']}元
2. 价格敏感度: {scenario['price_sensitivity']}/10 (越高表示越关注费率)
3. 决策速度: {scenario['decision_speed']}/10 (越高表示决策越快)
4. 你知道市场上其他银行提供的12期分期费率在{scenario['competitor_rate_min']}%-{scenario['competitor_rate_max']}%左右
5. 你的底线是不接受超过{scenario['max_acceptable_rate']}%的{scenario['preferred_period']}期分期费率

在与银行营销人员交流时，你会:
1. 询问当前的分期活动和费率
2. 提及竞争对手的更低报价
3. 尝试获得更低的手续费率
4. 在条件接近你的心理预期时同意方案

你的谈判风格:
- {scenario['negotiation_style']}

对话中可能使用的表达:
{scenario['dialogue_patterns']}

当你接受某个方案时，明确表示"我接受这个方案"。
如果你拒绝方案，请说明原因并表达期望。"""

        return prompt

#########################
# 客户场景生成
#########################

class ScenarioGenerator:
    """客户场景生成器"""
    
    def __init__(self):
        """初始化场景生成器"""
        # 客户名称列表
        self.customer_names = [
            "张先生", "李女士", "王先生", "赵女士", "刘先生", 
            "陈女士", "杨先生", "黄女士", "周先生", "吴女士"
        ]
        
        # 客户背景模板
        self.background_templates = [
            "你想购买一台约{amount}元的笔记本电脑，正在寻找最优惠的分期方案。",
            "你需要{amount}元资金用于装修新房，正在考虑信用卡分期。",
            "你打算购买一部{amount}元的新手机，希望通过分期减轻一次性支付压力。",
            "你计划报名一个{amount}元的职业培训课程，正在寻找合适的分期方式。",
            "你想给家人购买{amount}元的家电，正在考虑通过信用卡分期支付。"
        ]
        
        # 谈判风格模板
        self.negotiation_styles = [
            "你非常理性，喜欢对比数据和计算总成本",
            "你比较情绪化，容易被推销话术影响，但对价格非常敏感",
            "你决策谨慎，需要多次确认和思考",
            "你决策果断，一旦条件满足就会迅速接受",
            "你非常擅长谈判，会利用竞争对手的报价争取最大优惠",
            "你对银行政策和市场行情了解有限，主要关注月供是否在预算内"
        ]
        
        # 对话模式模板
        self.dialogue_pattern_templates = [
            "- '其他银行给我的报价更低'\n- '这个费率是不是太高了'\n- '能不能再优惠一点'",
            "- '我需要尽快拿到这笔钱'\n- '手续简单吗，要多久能办下来'\n- '有没有什么隐藏费用'",
            "- '我之前听朋友说有更低的费率'\n- '这个方案总手续费是多少'\n- '月供压力会不会太大'",
            "- '我还在对比几家银行'\n- '如果现在办理有什么特别优惠吗'\n- '能详细解释一下各期数的区别吗'"
        ]
        
    def generate_random_scenario(self) -> Dict[str, Any]:
        """生成一个随机的客户场景"""
        # 随机选择一个客户名称
        customer_name = random.choice(self.customer_names)
        
        # 随机生成分期金额 (5000-50000)
        amount = random.randint(5, 50) * 1000
        
        # 随机生成月收入 (8000-30000)
        monthly_income = random.randint(8, 30) * 1000
        
        # 随机生成最大月供 (月收入的15%-30%)
        max_monthly_payment = int(monthly_income * random.uniform(0.15, 0.3))
        
        # 随机生成价格敏感度 (3-10)
        price_sensitivity = random.uniform(3, 10)
        
        # 随机生成决策速度 (3-10)
        decision_speed = random.uniform(3, 10)
        
        # 随机生成竞争对手费率范围
        competitor_rate_min = random.uniform(7, 8)
        competitor_rate_max = competitor_rate_min + random.uniform(0.5, 1.5)
        
        # 随机生成首选期数
        preferred_period = random.choice([6, 12, 24])
        
        # 随机生成最高可接受费率 (根据首选期数和价格敏感度)
        if preferred_period == 6:
            base_max_rate = random.uniform(4, 6)
        elif preferred_period == 12:
            base_max_rate = random.uniform(7, 9)
        else:  # 24期
            base_max_rate = random.uniform(12, 15)
            
        # 价格敏感度越高，最高可接受费率越低
        sensitivity_factor = 1 - (price_sensitivity - 3) / 14  # 将3-10映射到0.5-1
        max_acceptable_rate = base_max_rate * sensitivity_factor
        
        # 随机选择背景模板并填充
        background = random.choice(self.background_templates).format(amount=amount)
        
        # 随机选择谈判风格
        negotiation_style = random.choice(self.negotiation_styles)
        
        # 随机选择对话模式
        dialogue_patterns = random.choice(self.dialogue_pattern_templates)
        
        # 生成完整场景
        scenario = {
            "customer_name": customer_name,
            "amount": amount,
            "background": background,
            "monthly_income": monthly_income,
            "max_monthly_payment": max_monthly_payment,
            "price_sensitivity": price_sensitivity,
            "decision_speed": decision_speed,
            "competitor_rate_min": round(competitor_rate_min, 1),
            "competitor_rate_max": round(competitor_rate_max, 1),
            "preferred_period": preferred_period,
            "max_acceptable_rate": round(max_acceptable_rate, 1),
            "negotiation_style": negotiation_style,
            "dialogue_patterns": dialogue_patterns
        }
        
        return scenario

#########################
# 谈判模拟
#########################

class NegotiationSimulator:
    """谈判模拟器"""
    
    def __init__(self, anthropic_api_key: str = ANTHROPIC_API_KEY):
        """初始化谈判模拟器"""
        self.client = AsyncAnthropic(api_key=anthropic_api_key)
        self.scenario_generator = ScenarioGenerator()
        
    async def run_negotiation(self, 
                            sales_prompt: str, 
                            customer_prompt: str, 
                            max_turns: int = 10) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        运行一次谈判模拟
        
        参数:
            sales_prompt: 销售人员的系统提示词
            customer_prompt: 客户的系统提示词
            max_turns: 最大对话轮数
        
        返回:
            对话历史和交易结果
        """
        dialogue_history = []
        
        # 客户初始消息
        customer_message = await self._generate_customer_message(
            customer_prompt,
            "我想了解一下信用卡分期的情况，有什么方案可以推荐吗？"
        )
        dialogue_history.append({
            "role": "customer",
            "content": customer_message
        })
        
        # 进行多轮对话
        deal_result = None
        for turn in range(max_turns):
            # 销售回复
            sales_message = await self._generate_sales_message(
                sales_prompt,
                dialogue_history
            )
            dialogue_history.append({
                "role": "sales",
                "content": sales_message
            })
            
            # 检查是否达成交易
            deal_info = self._extract_deal_info(sales_message)
            if deal_info and deal_info.get("status") == "success":
                deal_result = deal_info
                break
                
            # 客户回复
            customer_message = await self._generate_customer_message(
                customer_prompt,
                sales_message,
                dialogue_history
            )
            dialogue_history.append({
                "role": "customer",
                "content": customer_message
            })
            
            # 检查客户是否接受方案
            if "我接受这个方案" in customer_message:
                # 提取最后一次销售方案作为成交方案
                deal_result = {
                    "status": "success",
                    "amount": self._extract_amount(dialogue_history),
                    "period": self._extract_period(dialogue_history),
                    "rate": self._extract_rate(dialogue_history),
                    "turns": turn + 1
                }
                break
                
        # 如果没有达成交易，标记为失败
        if not deal_result:
            deal_result = {
                "status": "failed",
                "turns": max_turns
            }
            
        return dialogue_history, deal_result
    
    async def _generate_sales_message(self, 
                                    sales_prompt: str, 
                                    dialogue_history: List[Dict[str, str]]) -> str:
        """生成销售人员的回复"""
        # 构建对话上下文 - 使用正确的Anthropic API格式
        messages = []
        
        # 添加对话历史，但不添加系统消息到messages数组
        for entry in dialogue_history:
            if entry["role"] == "customer":
                messages.append({"role": "user", "content": entry["content"]})
            else:
                messages.append({"role": "assistant", "content": entry["content"]})
                
        # 如果对话历史为空，添加一个初始用户消息
        if not dialogue_history:
            messages.append({"role": "user", "content": "您好，我想了解一下信用卡分期。"})
            
        # 调用Claude API生成回复 - 系统提示词作为单独的system参数传递
        response = await self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            system=sales_prompt,  # 系统提示词作为单独参数
            messages=messages
        )
        
        return response.content[0].text
    
    async def _generate_customer_message(self, 
                                       customer_prompt: str, 
                                       last_sales_message: str,
                                       dialogue_history: List[Dict[str, str]] = None) -> str:
        """生成客户的回复"""
        # 构建对话上下文
        messages = []
        
        if dialogue_history:
            # 添加前几轮对话历史（最多3轮）
            recent_history = dialogue_history[-min(6, len(dialogue_history)):]
            for entry in recent_history:
                if entry["role"] == "sales":
                    messages.append({"role": "user", "content": f"销售顾问: {entry['content']}"})
                else:
                    messages.append({"role": "assistant", "content": entry["content"]})
        
        # 添加最新的销售消息
        if not dialogue_history:
            # 如果是第一次对话，使用标准开场白
            messages.append({"role": "user", "content": "你好，我是中信银行信用卡中心的客服。请问有什么可以帮到您的吗？"})
        else:
            messages.append({"role": "user", "content": f"销售顾问: {last_sales_message}"})
            
        # 调用Claude API生成回复 - 系统提示词作为单独的system参数传递
        response = await self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=800,
            system=customer_prompt,  # 系统提示词作为单独参数
            messages=messages
        )
        
        return response.content[0].text
    
    def _extract_deal_info(self, sales_message: str) -> Optional[Dict[str, Any]]:
        """从销售消息中提取成交信息"""
        # 这个函数可以根据实际需要进行扩展，使用更复杂的提取逻辑
        # 目前简单检查是否包含交易成功的关键词
        if "交易已完成" in sales_message or "订单已提交" in sales_message:
            # 尝试提取金额、期数和费率
            amount = self._extract_amount([{"role": "sales", "content": sales_message}])
            period = self._extract_period([{"role": "sales", "content": sales_message}])
            rate = self._extract_rate([{"role": "sales", "content": sales_message}])
            
            if amount and period and rate:
                return {
                    "status": "success",
                    "amount": amount,
                    "period": period,
                    "rate": rate
                }
                
        return None
    
    def _extract_amount(self, dialogue_history: List[Dict[str, str]]) -> Optional[float]:
        """从对话历史中提取分期金额"""
        # 从后往前遍历对话历史
        for entry in reversed(dialogue_history):
            content = entry["content"]
            # 使用简单的正则表达式或字符串匹配来提取金额
            # 这里使用简化的逻辑，实际应用中可能需要更复杂的提取方法
            import re
            amount_matches = re.findall(r'(\d{1,3}(,\d{3})*(\.\d+)?|\d+(\.\d+)?)元的分期', content)
            if amount_matches:
                # 提取第一个匹配并转换为数字
                amount_str = amount_matches[0][0].replace(',', '')
                return float(amount_str)
                
        # 如果没有找到，返回默认值15000
        return 15000.0
    
    def _extract_period(self, dialogue_history: List[Dict[str, str]]) -> Optional[int]:
        """从对话历史中提取分期期数"""
        # 从后往前遍历对话历史
        for entry in reversed(dialogue_history):
            content = entry["content"]
            # 查找常见的期数表达
            for period in [24, 12, 6, 3]:
                if f"{period}期分期" in content or f"{period}个月分期" in content:
                    return period
                    
        # 如果没有找到，返回默认值12
        return 12
    
    def _extract_rate(self, dialogue_history: List[Dict[str, str]]) -> Optional[float]:
        """从对话历史中提取费率"""
        # 从后往前遍历对话历史
        for entry in reversed(dialogue_history):
            content = entry["content"]
            # 使用正则表达式提取费率
            import re
            rate_matches = re.findall(r'费率[为是]?(\d+(\.\d+)?)%', content)
            if rate_matches:
                return float(rate_matches[0][0])
                
        # 如果没有找到，返回默认值9.0
        return 9.0

#########################
# 谈判评估
#########################

class NegotiationEvaluator:
    """谈判评估器"""
    
    def __init__(self):
        """初始化评估器"""
        # 标准费率
        self.standard_rates = {
            3: 3.0,
            6: 6.0,
            12: 9.0,
            24: 15.0
        }
        
    def evaluate(self, 
                dialogue_history: List[Dict[str, str]], 
                deal_result: Dict[str, Any],
                scenario: Dict[str, Any]) -> Dict[str, float]:
        """
        评估谈判结果
        
        参数:
            dialogue_history: 对话历史
            deal_result: 交易结果
            scenario: 客户场景
            
        返回:
            评分结果
        """
        # 初始化评分
        scores = {
            "profit_score": 0.0,  # 利润评分
            "efficiency_score": 0.0,  # 效率评分
            "customer_satisfaction_score": 0.0,  # 客户满意度评分
            "overall_score": 0.0  # 总评分
        }
        
        # 如果交易失败，返回低分
        if deal_result.get("status") == "failed":
            scores["overall_score"] = 30.0  # 失败但至少进行了尝试
            return scores
            
        # 提取交易信息
        amount = deal_result.get("amount", 0)
        period = deal_result.get("period", 0)
        rate = deal_result.get("rate", 0)
        turns = deal_result.get("turns", 0)
        
        # 计算利润评分 (0-100)
        if period in self.standard_rates:
            standard_rate = self.standard_rates[period]
            # 实际费率相对于标准费率的比例
            rate_ratio = rate / standard_rate
            
            # 费率越高，利润越高，评分越高
            # 最低可接受费率是标准费率的85%
            min_acceptable_ratio = 0.85
            
            if rate_ratio >= 1.0:
                # 高于标准费率，满分
                profit_score = 100.0
            elif rate_ratio >= min_acceptable_ratio:
                # 在最低可接受费率和标准费率之间，按比例评分
                profit_score = 70.0 + 30.0 * (rate_ratio - min_acceptable_ratio) / (1.0 - min_acceptable_ratio)
            else:
                # 低于最低可接受费率，按比例给低分
                profit_score = 70.0 * (rate_ratio / min_acceptable_ratio)
                
            # 考虑期数因素，期数越长越好
            period_factor = {3: 0.7, 6: 0.8, 12: 0.9, 24: 1.0}.get(period, 0.8)
            profit_score *= period_factor
            
            # 考虑金额因素，金额越大越好
            amount_factor = min(1.0, amount / 20000.0)  # 最高考虑到20000元
            profit_score *= (0.8 + 0.2 * amount_factor)  # 金额因素影响20%
            
            scores["profit_score"] = profit_score
        
        # 计算效率评分 (0-100)
        max_efficient_turns = 5  # 理想情况下5轮内完成
        if turns <= max_efficient_turns:
            # 在理想轮数内完成，满分
            efficiency_score = 100.0
        else:
            # 超过理想轮数，按比例扣分
            efficiency_score = max(60.0, 100.0 - 10.0 * (turns - max_efficient_turns))
            
        scores["efficiency_score"] = efficiency_score
        
        # 计算客户满意度评分 (0-100)
        satisfaction_score = 0.0
        
        # 根据客户价格敏感度和实际费率计算满意度
        price_sensitivity = scenario.get("price_sensitivity", 5.0)
        max_acceptable_rate = scenario.get("max_acceptable_rate", 8.0)
        
        if rate <= max_acceptable_rate:
            # 费率在客户接受范围内
            rate_satisfaction = 100.0 - (rate / max_acceptable_rate * 100.0 - 70.0)
        else:
            # 费率超出客户接受范围
            rate_satisfaction = max(50.0, 70.0 - (rate - max_acceptable_rate) * 10.0)
            
        # 费率因素权重随价格敏感度增加而增加
        rate_weight = 0.5 + (price_sensitivity / 20.0)  # 0.65-1.0
        
        # 根据期数是否符合客户偏好计算满意度
        preferred_period = scenario.get("preferred_period", 12)
        if period == preferred_period:
            period_satisfaction = 100.0
        else:
            period_satisfaction = 80.0 - abs(period - preferred_period) * 5.0
            
        # 期数因素权重
        period_weight = 1.0 - rate_weight
        
        # 综合计算满意度评分
        satisfaction_score = rate_satisfaction * rate_weight + period_satisfaction * period_weight
        
        scores["customer_satisfaction_score"] = satisfaction_score
        
        # 计算总评分 (加权平均)
        # 利润40%，效率20%，客户满意度40%
        scores["overall_score"] = (
            scores["profit_score"] * 0.4 +
            scores["efficiency_score"] * 0.2 +
            scores["customer_satisfaction_score"] * 0.4
        )
        
        return scores

#########################
# 遗传算法优化
#########################

class GeneticOptimizer:
    """使用遗传算法优化提示词参数"""
    
    def __init__(self, 
                population_size: int = 10, 
                elite_size: int = 2,
                mutation_rate: float = 0.2,
                crossover_rate: float = 0.7):
        """
        初始化遗传算法优化器
        
        参数:
            population_size: 种群大小
            elite_size: 精英个体数量
            mutation_rate: 变异率
            crossover_rate: 交叉率
        """
        self.population_size = population_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        
        # 初始化种群
        self.population = [PromptParams() for _ in range(population_size)]
        self.fitness_scores = [0.0] * population_size
        
        # 初始化最佳个体
        self.best_individual = None
        self.best_fitness = 0.0
        
        # 初始化评估器和模拟器
        self.evaluator = NegotiationEvaluator()
        self.simulator = NegotiationSimulator()
        
        # 创建场景生成器
        self.scenario_generator = ScenarioGenerator()
        
        # 进化历史
        self.evolution_history = []
        
    async def evaluate_population(self, scenarios_per_individual: int = 3):
        """评估当前种群的适应度"""
        for i, individual in enumerate(self.population):
            # 生成销售人员提示词
            sales_prompt = individual.generate_sales_prompt()
            
            # 每个个体在多个场景中进行测试
            total_score = 0.0
            successful_deals = 0
            
            for _ in range(scenarios_per_individual):
                # 生成随机场景
                scenario = self.scenario_generator.generate_random_scenario()
                
                # 生成客户提示词
                customer_prompt = individual.generate_customer_prompt(scenario)
                
                # 运行谈判模拟
                dialogue_history, deal_result = await self.simulator.run_negotiation(
                    sales_prompt, 
                    customer_prompt
                )
                
                # 评估谈判结果
                evaluation = self.evaluator.evaluate(
                    dialogue_history, 
                    deal_result,
                    scenario
                )
                
                # 累加分数
                total_score += evaluation["overall_score"]
                
                # 统计成功交易
                if deal_result.get("status") == "success":
                    successful_deals += 1
            
            # 计算平均分数
            avg_score = total_score / scenarios_per_individual
            
            # 加上成功率奖励
            success_rate = successful_deals / scenarios_per_individual
            fitness = avg_score * (0.7 + 0.3 * success_rate)  # 成功率占30%权重
            
            self.fitness_scores[i] = fitness
            
            # 更新最佳个体
            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.best_individual = individual
                
        logger.info(f"Population evaluated. Best fitness: {self.best_fitness}")
        
    def select_parents(self) -> List[PromptParams]:
        """使用轮盘赌选择法选择父代"""
        # 计算适应度总和
        total_fitness = sum(self.fitness_scores)
        
        # 如果总适应度为0，随机选择
        if total_fitness == 0:
            return random.sample(self.population, k=self.population_size)
            
        # 计算选择概率
        selection_probs = [score / total_fitness for score in self.fitness_scores]
        
        # 保留精英个体
        indices = np.argsort(self.fitness_scores)[-self.elite_size:]
        elites = [self.population[i] for i in indices]
        
        # 选择剩余父代
        remaining_count = self.population_size - self.elite_size
        parents = []
        
        for _ in range(remaining_count):
            # 轮盘赌选择
            selected_idx = np.random.choice(
                len(self.population), 
                p=selection_probs
            )
            parents.append(self.population[selected_idx])
            
        return elites + parents
        
    def crossover(self, parents: List[PromptParams]) -> List[PromptParams]:
        """对父代进行交叉操作"""
        offspring = parents[:self.elite_size]  # 保留精英个体
        
        # 生成剩余后代
        while len(offspring) < self.population_size:
            # 随机选择两个父代
            parent1, parent2 = random.sample(parents, k=2)
            
            # 根据交叉率决定是否进行交叉
            if random.random() < self.crossover_rate:
                child = parent1.crossover(parent2)
            else:
                # 不交叉，直接复制父代
                child = parent1
                
            offspring.append(child)
            
        return offspring
        
    def mutate(self, offspring: List[PromptParams]) -> List[PromptParams]:
        """对后代进行变异操作"""
        mutated = offspring[:self.elite_size]  # 精英个体不变异
        
        # 对剩余后代进行变异
        for i in range(self.elite_size, len(offspring)):
            # 根据变异率决定是否变异
            if random.random() < self.mutation_rate:
                mutated.append(offspring[i].mutate())
            else:
                mutated.append(offspring[i])
                
        return mutated
        
    async def evolve(self, generations: int = 10, scenarios_per_individual: int = 3):
        """运行遗传算法进行多代进化"""
        # 记录进化历史
        self.evolution_history = []
        
        # 初始评估
        logger.info("Evaluating initial population...")
        await self.evaluate_population(scenarios_per_individual)
        
        # 记录初始状态
        self.evolution_history.append({
            "generation": 0,
            "best_fitness": self.best_fitness,
            "avg_fitness": sum(self.fitness_scores) / len(self.fitness_scores),
            "best_params": self.best_individual.to_dict() if self.best_individual else None
        })
        
        # 进化过程
        for generation in range(1, generations + 1):
            logger.info(f"Generation {generation}/{generations}")
            
            # 选择父代
            parents = self.select_parents()
            
            # 交叉生成后代
            offspring = self.crossover(parents)
            
            # 变异
            self.population = self.mutate(offspring)
            
            # 评估新种群
            await self.evaluate_population(scenarios_per_individual)
            
            # 记录本代结果
            self.evolution_history.append({
                "generation": generation,
                "best_fitness": self.best_fitness,
                "avg_fitness": sum(self.fitness_scores) / len(self.fitness_scores),
                "best_params": self.best_individual.to_dict() if self.best_individual else None
            })
            
            # 保存当前最佳提示词
            if self.best_individual:
                self.save_best_prompt(generation)
                
            logger.info(f"Generation {generation} completed. Best fitness: {self.best_fitness}")
            
        return self.best_individual, self.best_fitness
        
    def save_best_prompt(self, generation: int):
        """保存当前最佳提示词"""
        if not self.best_individual:
            return
            
        # 生成提示词
        best_prompt = self.best_individual.generate_sales_prompt()
        
        # 保存到文件
        filename = os.path.join(PROMPTS_DIR, f"best_prompt_gen_{generation}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(best_prompt)
            
        # 保存参数
        params_filename = os.path.join(PROMPTS_DIR, f"best_params_gen_{generation}.json")
        with open(params_filename, "w", encoding="utf-8") as f:
            json.dump(self.best_individual.to_dict(), f, indent=2, ensure_ascii=False)
            
    def save_evolution_history(self):
        """保存进化历史"""
        if not self.evolution_history:
            return
            
        filename = os.path.join(RESULTS_DIR, f"evolution_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.evolution_history, f, indent=2, ensure_ascii=False)
            
    def plot_evolution_progress(self):
        """绘制进化过程图表"""
        if not self.evolution_history:
            return
            
        generations = [entry["generation"] for entry in self.evolution_history]
        best_fitness = [entry["best_fitness"] for entry in self.evolution_history]
        avg_fitness = [entry["avg_fitness"] for entry in self.evolution_history]
        
        plt.figure(figsize=(10, 6))
        plt.plot(generations, best_fitness, "b-", label="最佳适应度")
        plt.plot(generations, avg_fitness, "r--", label="平均适应度")
        plt.xlabel("代数")
        plt.ylabel("适应度")
        plt.title("遗传算法优化进度")
        plt.legend()
        plt.grid(True)
        
        # 保存图表
        plot_filename = os.path.join(RESULTS_DIR, f"evolution_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(plot_filename)
        plt.close()

#########################
# 记忆增强模块
#########################

class MemoryAugmentation:
    """记忆增强模块，用于从历史谈判中提取经验"""
    
    def __init__(self):
        """初始化记忆增强模块"""
        self.successful_strategies = []
        self.failed_strategies = []
        self.customer_patterns = {}
        
    async def analyze_negotiation(self, 
                                dialogue_history: List[Dict[str, str]],
                                deal_result: Dict[str, Any],
                                scenario: Dict[str, Any],
                                evaluation: Dict[str, float]):
        """分析一次谈判，提取经验"""
        # 是否成功的谈判
        is_successful = deal_result.get("status") == "success"
        
        # 提取关键信息
        customer_type = self._determine_customer_type(scenario)
        
        # 提取销售策略
        strategy_patterns = self._extract_strategy_patterns(dialogue_history)
        
        # 根据谈判结果分类经验
        if is_successful:
            self.successful_strategies.append({
                "customer_type": customer_type,
                "strategy_patterns": strategy_patterns,
                "deal_result": deal_result,
                "evaluation": evaluation
            })
        else:
            self.failed_strategies.append({
                "customer_type": customer_type,
                "strategy_patterns": strategy_patterns,
                "deal_result": deal_result,
                "evaluation": evaluation
            })
            
        # 更新客户模式识别
        if customer_type not in self.customer_patterns:
            self.customer_patterns[customer_type] = []
            
        self.customer_patterns[customer_type].append({
            "dialogue_history": dialogue_history,
            "is_successful": is_successful,
            "deal_result": deal_result
        })
        
    def _determine_customer_type(self, scenario: Dict[str, Any]) -> str:
        """确定客户类型"""
        price_sensitivity = scenario.get("price_sensitivity", 5.0)
        decision_speed = scenario.get("decision_speed", 5.0)
        
        if price_sensitivity > 7.0:
            if decision_speed > 7.0:
                return "price_sensitive_quick"
            else:
                return "price_sensitive_slow"
        else:
            if decision_speed > 7.0:
                return "convenience_oriented"
            else:
                return "balanced"
                
    def _extract_strategy_patterns(self, dialogue_history: List[Dict[str, str]]) -> List[str]:
        """从对话历史中提取销售策略模式"""
        patterns = []
        
        for entry in dialogue_history:
            if entry["role"] != "sales":
                continue
                
            content = entry["content"].lower()
            
            # 检测时间压力策略
            if "今天" in content and ("特价" in content or "优惠" in content):
                patterns.append("time_pressure")
                
            # 检测情感诉求策略
            if "生活质量" in content or "便利" in content or "享受" in content:
                patterns.append("emotional_appeal")
                
            # 检测价格锚定策略
            if "标准费率" in content and "特殊优惠" in content:
                patterns.append("price_anchoring")
                
            # 检测产品对比策略
            if "相比其他银行" in content or "我们的优势" in content:
                patterns.append("competitive_comparison")
                
            # 检测让步策略
            if "考虑到您的情况" in content and "特批" in content:
                patterns.append("concession")
                
        return list(set(patterns))
        
    def generate_experience_prompt(self) -> str:
        """生成基于经验的提示词增强部分"""
        # 如果没有足够的经验数据，返回空
        if len(self.successful_strategies) < 3:
            return ""
            
        # 提取最成功的策略
        top_strategies = sorted(
            self.successful_strategies,
            key=lambda x: x["evaluation"]["overall_score"],
            reverse=True
        )[:5]
        
        # 提取常见失败模式
        common_failures = {}
        for strategy in self.failed_strategies:
            customer_type = strategy["customer_type"]
            if customer_type not in common_failures:
                common_failures[customer_type] = 0
            common_failures[customer_type] += 1
            
        # 生成经验提示
        experience_text = "根据过去的谈判经验:\n\n"
        
        # 添加成功策略
        experience_text += "成功策略:\n"
        for i, strategy in enumerate(top_strategies, 1):
            customer_type = strategy["customer_type"]
            patterns = strategy["strategy_patterns"]
            result = strategy["deal_result"]
            
            experience_text += f"{i}. 对于{self._translate_customer_type(customer_type)}类客户，"
            experience_text += f"使用{', '.join(self._translate_strategy(p) for p in patterns)}策略，"
            experience_text += f"成功达成{result.get('period', 12)}期{result.get('rate', 0.0)}%的方案\n"
            
        # 添加常见失败模式
        if common_failures:
            experience_text += "\n需要注意的失败模式:\n"
            for customer_type, count in sorted(common_failures.items(), key=lambda x: x[1], reverse=True):
                if count >= 2:  # 至少出现两次才考虑
                    experience_text += f"- 对于{self._translate_customer_type(customer_type)}类客户，避免过度"
                    
                    # 分析这类客户的失败案例
                    failed_cases = [s for s in self.failed_strategies if s["customer_type"] == customer_type]
                    common_patterns = self._find_common_patterns(failed_cases)
                    
                    if common_patterns:
                        experience_text += f"使用{', '.join(self._translate_strategy(p) for p in common_patterns)}\n"
                    else:
                        experience_text += "强势或过度保守\n"
                        
        return experience_text
        
    def _translate_customer_type(self, customer_type: str) -> str:
        """将客户类型代码转为中文描述"""
        translations = {
            "price_sensitive_quick": "价格敏感且决策快速",
            "price_sensitive_slow": "价格敏感且谨慎决策",
            "convenience_oriented": "注重便利快速决策",
            "balanced": "平衡型"
        }
        return translations.get(customer_type, customer_type)
        
    def _translate_strategy(self, strategy: str) -> str:
        """将策略代码转为中文描述"""
        translations = {
            "time_pressure": "时间压力",
            "emotional_appeal": "情感诉求",
            "price_anchoring": "价格锚定",
            "competitive_comparison": "竞争对比",
            "concession": "适时让步"
        }
        return translations.get(strategy, strategy)
        
    def _find_common_patterns(self, strategies: List[Dict]) -> List[str]:
        """找出一组策略中的共同模式"""
        if not strategies:
            return []
            
        # 统计各模式出现次数
        pattern_counts = {}
        for strategy in strategies:
            for pattern in strategy["strategy_patterns"]:
                if pattern not in pattern_counts:
                    pattern_counts[pattern] = 0
                pattern_counts[pattern] += 1
                
        # 找出出现次数超过半数的模式
        threshold = len(strategies) / 2
        common = [p for p, count in pattern_counts.items() if count >= threshold]
        
        return common
        
    def save_memory(self, filename: str = "negotiation_memory.pkl"):
        """保存记忆数据"""
        memory_data = {
            "successful_strategies": self.successful_strategies,
            "failed_strategies": self.failed_strategies,
            "customer_patterns": self.customer_patterns
        }
        
        filepath = os.path.join(RESULTS_DIR, filename)
        with open(filepath, "wb") as f:
            pickle.dump(memory_data, f)
            
    def load_memory(self, filename: str = "negotiation_memory.pkl"):
        """加载记忆数据"""
        filepath = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(filepath):
            return False
            
        try:
            with open(filepath, "rb") as f:
                memory_data = pickle.load(f)
                
            self.successful_strategies = memory_data["successful_strategies"]
            self.failed_strategies = memory_data["failed_strategies"]
            self.customer_patterns = memory_data["customer_patterns"]
            
            return True
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return False

#########################
# 主程序
#########################

class AgentOptimizer:
    """Agent优化器主程序"""
    
    def __init__(self):
        """初始化Agent优化器"""
        self.genetic_optimizer = GeneticOptimizer(
            population_size=10,
            elite_size=2
        )
        self.memory = MemoryAugmentation()
        self.simulator = NegotiationSimulator()
        self.evaluator = NegotiationEvaluator()
        self.scenario_generator = ScenarioGenerator()
        
    async def run_optimization(self, generations: int = 5, scenarios_per_individual: int = 3):
        """运行优化过程"""
        logger.info("Starting agent optimization process")
        
        # 尝试加载历史记忆
        memory_loaded = self.memory.load_memory()
        if memory_loaded:
            logger.info("Loaded existing memory")
        
        # 运行遗传算法
        best_individual, best_fitness = await self.genetic_optimizer.evolve(
            generations=generations,
            scenarios_per_individual=scenarios_per_individual
        )
        
        # 保存进化历史
        self.genetic_optimizer.save_evolution_history()
        
        # 绘制进化过程图表
        self.genetic_optimizer.plot_evolution_progress()
        
        # 保存记忆数据
        self.memory.save_memory()
        
        # 返回最佳提示词
        if best_individual:
            best_prompt = best_individual.generate_sales_prompt()
            
            # 增加经验增强
            experience_prompt = self.memory.generate_experience_prompt()
            if experience_prompt:
                # 将经验插入到提示词中
                best_prompt = best_prompt.replace("谈判经验:", f"谈判经验:\n{experience_prompt}")
                
            # 保存最终提示词
            final_prompt_path = os.path.join(PROMPTS_DIR, "final_optimized_prompt.txt")
            with open(final_prompt_path, "w", encoding="utf-8") as f:
                f.write(best_prompt)
                
            logger.info(f"Optimization completed. Best fitness: {best_fitness}")
            logger.info(f"Final optimized prompt saved to {final_prompt_path}")
            
            return best_prompt, best_fitness
        else:
            logger.warning("Optimization failed to find a good solution")
            return None, 0.0
            
    async def evaluate_prompt(self, prompt: str, num_scenarios: int = 10):
        """评估单个提示词的效果"""
        logger.info(f"Evaluating prompt with {num_scenarios} scenarios")
        
        total_score = 0.0
        successful_deals = 0
        all_evaluations = []
        
        for i in range(num_scenarios):
            # 生成随机场景
            scenario = self.scenario_generator.generate_random_scenario()
            
            # 生成客户提示词
            customer_prompt = self.genetic_optimizer.population[0].generate_customer_prompt(scenario)
            
            # 运行谈判模拟
            dialogue_history, deal_result = await self.simulator.run_negotiation(
                prompt, 
                customer_prompt
            )
            
            # 评估谈判结果
            evaluation = self.evaluator.evaluate(
                dialogue_history, 
                deal_result,
                scenario
            )
            
            # 累加分数
            total_score += evaluation["overall_score"]
            
            # 统计成功交易
            if deal_result.get("status") == "success":
                successful_deals += 1
                
            # 保存评估结果
            all_evaluations.append({
                "scenario": scenario,
                "dialogue_history": dialogue_history,
                "deal_result": deal_result,
                "evaluation": evaluation
            })
            
            # 分析谈判并更新记忆
            await self.memory.analyze_negotiation(
                dialogue_history,
                deal_result,
                scenario,
                evaluation
            )
            
        # 计算平均分数
        avg_score = total_score / num_scenarios if num_scenarios > 0 else 0
        success_rate = successful_deals / num_scenarios if num_scenarios > 0 else 0
        
        logger.info(f"Prompt evaluation completed. Average score: {avg_score}, Success rate: {success_rate}")
        
        # 保存评估结果
        results_path = os.path.join(RESULTS_DIR, f"prompt_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "avg_score": avg_score,
                "success_rate": success_rate,
                "evaluations": all_evaluations
            }, f, default=lambda o: str(o), indent=2)
            
        return avg_score, success_rate, all_evaluations
        
    async def demo_optimized_agent(self, prompt_path: str = None):
        """使用优化后的Agent进行演示"""
        # 加载提示词
        if prompt_path and os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                sales_prompt = f.read()
        else:
            # 使用最新的优化提示词
            prompt_files = [f for f in os.listdir(PROMPTS_DIR) if f.startswith("final_optimized_prompt")]
            if not prompt_files:
                logger.error("No optimized prompt found for demo")
                return
                
            prompt_path = os.path.join(PROMPTS_DIR, prompt_files[0])
            with open(prompt_path, "r", encoding="utf-8") as f:
                sales_prompt = f.read()
                
        logger.info(f"Running demo with prompt from: {prompt_path}")
        
        # 生成随机场景
        scenario = self.scenario_generator.generate_random_scenario()
        
        # 生成客户提示词
        customer_prompt = self.genetic_optimizer.population[0].generate_customer_prompt(scenario)
        
        # 运行谈判模拟
        dialogue_history, deal_result = await self.simulator.run_negotiation(
            sales_prompt, 
            customer_prompt,
            max_turns=15  # 允许更长的对话
        )
        
        # 评估谈判结果
        evaluation = self.evaluator.evaluate(
            dialogue_history, 
            deal_result,
            scenario
        )
        
        # 打印对话
        print("\n=== 优化后的Agent演示 ===\n")
        print(f"客户场景: {scenario['customer_name']}，{scenario['background']}")
        print(f"客户特征: 价格敏感度 {scenario['price_sensitivity']}/10，决策速度 {scenario['decision_speed']}/10")
        print(f"首选期数: {scenario['preferred_period']}期，最高可接受费率: {scenario['max_acceptable_rate']}%")
        print("\n=== 对话开始 ===\n")
        
        for entry in dialogue_history:
            if entry["role"] == "customer":
                print(f"\n客户: {entry['content']}\n")
            else:
                print(f"\n销售顾问: {entry['content']}\n")
                
        print("\n=== 对话结束 ===\n")
        
        # 打印结果
        if deal_result.get("status") == "success":
            print(f"成交结果: 成功")
            print(f"金额: {deal_result.get('amount', 0)}元")
            print(f"期数: {deal_result.get('period', 0)}期")
            print(f"费率: {deal_result.get('rate', 0)}%")
            print(f"轮数: {deal_result.get('turns', 0)}轮")
        else:
            print("成交结果: 失败")
            
        print("\n=== 评估结果 ===\n")
        print(f"利润评分: {evaluation['profit_score']:.2f}/100")
        print(f"效率评分: {evaluation['efficiency_score']:.2f}/100")
        print(f"客户满意度评分: {evaluation['customer_satisfaction_score']:.2f}/100")
        print(f"总评分: {evaluation['overall_score']:.2f}/100")
        
        # 保存演示结果
        demo_path = os.path.join(RESULTS_DIR, f"agent_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(demo_path, "w", encoding="utf-8") as f:
            f.write("=== 优化后的Agent演示 ===\n\n")
            f.write(f"客户场景: {scenario['customer_name']}，{scenario['background']}\n")
            f.write(f"客户特征: 价格敏感度 {scenario['price_sensitivity']}/10，决策速度 {scenario['decision_speed']}/10\n")
            f.write(f"首选期数: {scenario['preferred_period']}期，最高可接受费率: {scenario['max_acceptable_rate']}%\n\n")
            f.write("=== 对话内容 ===\n\n")
            
            for entry in dialogue_history:
                if entry["role"] == "customer":
                    f.write(f"\n客户: {entry['content']}\n")
                else:
                    f.write(f"\n销售顾问: {entry['content']}\n")
                    
            f.write("\n\n=== 结果 ===\n\n")
            if deal_result.get("status") == "success":
                f.write(f"成交结果: 成功\n")
                f.write(f"金额: {deal_result.get('amount', 0)}元\n")
                f.write(f"期数: {deal_result.get('period', 0)}期\n")
                f.write(f"费率: {deal_result.get('rate', 0)}%\n")
                f.write(f"轮数: {deal_result.get('turns', 0)}轮\n")
            else:
                f.write("成交结果: 失败\n")
                
            f.write("\n=== 评估 ===\n\n")
            f.write(f"利润评分: {evaluation['profit_score']:.2f}/100\n")
            f.write(f"效率评分: {evaluation['efficiency_score']:.2f}/100\n")
            f.write(f"客户满意度评分: {evaluation['customer_satisfaction_score']:.2f}/100\n")
            f.write(f"总评分: {evaluation['overall_score']:.2f}/100\n")
            
        logger.info(f"Demo results saved to {demo_path}")

#########################
# 命令行入口
#########################

async def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Negotiation Ability Optimization Framework")
    parser.add_argument("--mode", type=str, default="optimize", 
                      choices=["optimize", "evaluate", "demo"],
                      help="运行模式: optimize(优化), evaluate(评估), demo(演示)")
    parser.add_argument("--generations", type=int, default=5, 
                      help="遗传算法运行代数")
    parser.add_argument("--population", type=int, default=10, 
                      help="种群大小")
    parser.add_argument("--scenarios", type=int, default=3, 
                      help="每个个体评估的场景数量")
    parser.add_argument("--prompt", type=str, default=None, 
                      help="用于评估或演示的提示词文件路径")
    parser.add_argument("--eval-count", type=int, default=10, 
                      help="评估模式下的场景数量")
    
    args = parser.parse_args()
    
    if args.mode == "optimize":
        # 优化模式
        optimizer = AgentOptimizer()
        optimizer.genetic_optimizer.population_size = args.population
        
        await optimizer.run_optimization(
            generations=args.generations,
            scenarios_per_individual=args.scenarios
        )
        
    elif args.mode == "evaluate":
        # 评估模式
        optimizer = AgentOptimizer()
        
        if args.prompt:
            # 加载指定提示词
            with open(args.prompt, "r", encoding="utf-8") as f:
                prompt = f.read()
        else:
            # 使用默认提示词
            prompt = PromptParams().generate_sales_prompt()
            
        await optimizer.evaluate_prompt(prompt, num_scenarios=args.eval_count)
        
    elif args.mode == "demo":
        # 演示模式
        optimizer = AgentOptimizer()
        await optimizer.demo_optimized_agent(prompt_path=args.prompt)
        
    else:
        print(f"未知模式: {args.mode}")

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
