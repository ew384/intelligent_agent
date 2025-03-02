# orchestrator-service/src/workflows/credit_card.py
from .base import BaseWorkflow
from typing import Dict, Any
import httpx
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)

class CreditCardWorkflow(BaseWorkflow):
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 1. 从场景服务获取工作流配置
            async with httpx.AsyncClient() as client:
                scenario_response = await client.get(
                    "http://localhost:8002/scenarios/credit_card"
                )
                scenario_response.raise_for_status()
                scenario_config = scenario_response.json()
                
                logger.info(f"Retrieved scenario config: {scenario_config}")
                
                # 2. 解析工作流配置
                workflow_steps = scenario_config.get("workflow", {}).get("steps", [])
                
                # 3. 按顺序执行每个步骤
                results = {}
                i = 0
                while i < len(workflow_steps):
                    step = workflow_steps[i]
                    step_id = step.get("id", f"step_{i}")
                    step_type = step.get("type")
                    action = step.get("action")
                    step_params = step.get("parameters", {})
                    condition = step.get("condition")
                    
                    # 检查条件表达式，决定是否执行该步骤
                    if condition:
                        should_execute = self._evaluate_condition(condition, parameters, results)
                        if not should_execute:
                            logger.info(f"步骤 {step_id} 条件不满足，跳过执行")
                            i += 1
                            continue
                    
                    # 替换参数中的变量
                    processed_params = self._process_parameters(step_params, parameters, results)
                    
                    # 执行步骤
                    if step_type == "browser_api" or step_type == "browser_operations":
                        logger.info(f"执行浏览器操作: {action}")
                        tool_response = await client.post(
                            f"http://localhost:8003/tools/browser/{action}",
                            json=processed_params,
                            timeout=300.0
                        )
                        tool_response.raise_for_status()
                        step_result = tool_response.json()
                        results[step_id] = step_result
                    
                    elif step_type == "credit_card_action":
                        logger.info(f"执行信用卡特定操作: {action}")
                        tool_response = await client.post(
                            f"http://localhost:8003/tools/browser/credit-card",
                            json={**processed_params, "action": action}
                        )
                        tool_response.raise_for_status()
                        step_result = tool_response.json()
                        results[step_id] = step_result
                    
                    elif step_type == "wechat_action":
                        logger.info(f"执行微信操作: {action}")
                        tool_response = await client.post(
                            f"http://localhost:8003/tools/wechat/{action}",
                            json=processed_params,
                            timeout=300.0
                        )
                        tool_response.raise_for_status()
                        step_result = tool_response.json()
                        results[step_id] = step_result
                    
                    else:
                        # 处理未知的步骤类型
                        logger.warning(f"未知的步骤类型: {step_type}")
                        step_result = {
                            "status": "error",
                            "message": f"未知的步骤类型: {step_type}"
                        }
                        results[step_id] = step_result
                    
                    # 特殊处理 wait_for_login 步骤
                    if action == "wait_for_login":
                        if step_result.get("status") == "success":
                            # 用户已经登录，继续执行
                            logger.info("检测到用户已登录，继续执行工作流")
                        elif step_result.get("status") == "pending":
                            # 用户需要登录，返回等待状态
                            logger.info(f"步骤 {step_id} 需要用户登录: {step_result.get('message')}")
                            return {
                                "status": "pending",
                                "message": step_result.get('message', "请在浏览器中完成登录..."),
                                "step_id": step_id,
                                "results": results,
                                "current_step_index": i,
                                "remaining_steps": len(workflow_steps) - i - 1
                            }
                    # 处理其他步骤的错误状态
                    elif step_result.get("status") == "error":
                        # 步骤执行失败
                        logger.error(f"步骤 {step_id} 执行失败: {step_result.get('message')}")
                        return {
                            "status": "error",
                            "message": f"步骤 {step_id} 失败: {step_result.get('message')}",
                            "results": results
                        }
                    
                    # 进入下一个步骤
                    i += 1
                
                # 所有步骤执行完成
                return {
                    "status": "success",
                    "message": "工作流执行成功",
                    "results": results
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.text}")
            return {"status": "error", "message": f"Service error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            logger.exception(f"Workflow execution failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _process_parameters(self, step_params, input_params, previous_results):
        """
        处理参数中的变量引用
        
        Args:
            step_params: 步骤参数
            input_params: 输入参数
            previous_results: 之前步骤的结果
            
        Returns:
            处理后的参数
        """
        processed_params = {}
        
        for key, value in step_params.items():
            if isinstance(value, str) and "{" in value and "}" in value:
                # 处理复合字符串，可能包含多个变量引用
                processed_value = value
                
                # 查找所有变量引用并替换
                import re
                pattern = r"\{([^{}]+)\}"
                matches = re.findall(pattern, value)
                
                for match in matches:
                    placeholder = "{" + match + "}"
                    
                    # 检查是否是输入参数
                    if match in input_params:
                        replacement = str(input_params[match])
                        processed_value = processed_value.replace(placeholder, replacement)
                    
                    # 检查是否是来自之前步骤的结果
                    elif "." in match:
                        parts = match.split(".")
                        step_id = parts[0]
                        
                        if step_id in previous_results:
                            # 获取嵌套属性
                            current = previous_results[step_id]
                            for part in parts[1:]:
                                if isinstance(current, dict) and part in current:
                                    current = current[part]
                                else:
                                    current = None
                                    break
                            
                            if current is not None:
                                replacement = str(current)
                                processed_value = processed_value.replace(placeholder, replacement)
                
                processed_params[key] = processed_value
            else:
                processed_params[key] = value
                
        return processed_params
        
    def _evaluate_condition(self, condition: str, input_params: Dict[str, Any], previous_results: Dict[str, Any]) -> bool:
        """
        评估条件表达式
        
        Args:
            condition: 条件表达式字符串
            input_params: 输入参数
            previous_results: 之前步骤的结果
            
        Returns:
            条件是否满足
        """
        try:
            # 替换条件中的变量引用
            import re
            pattern = r"\{([^{}]+)\}"
            matches = re.findall(pattern, condition)
            
            # 准备本地命名空间
            local_vars = {}
            
            for match in matches:
                placeholder = "{" + match + "}"
                
                # 检查是否是输入参数
                if match in input_params:
                    value = input_params[match]
                    local_vars[match] = value
                    condition = condition.replace(placeholder, match)
                
                # 检查是否是来自之前步骤的结果
                elif "." in match:
                    parts = match.split(".")
                    step_id = parts[0]
                    
                    if step_id in previous_results:
                        # 获取嵌套属性
                        current = previous_results[step_id]
                        for part in parts[1:]:
                            if isinstance(current, dict) and part in current:
                                current = current[part]
                            else:
                                current = None
                                break
                        
                        # 创建安全的变量名
                        var_name = match.replace(".", "_")
                        local_vars[var_name] = current
                        condition = condition.replace(placeholder, var_name)
            
            # 评估条件
            return eval(condition, {"__builtins__": {}}, local_vars)
            
        except Exception as e:
            logger.error(f"评估条件表达式失败: {condition}, 错误: {str(e)}")
            return False