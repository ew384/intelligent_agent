import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """工作流引擎，负责加载和执行工作流JSON"""
    
    def __init__(self, browser_context=None, workflows_dir="workflows"):
        """
        初始化工作流引擎
        
        参数:
            browser_context: 浏览器上下文对象，用于执行操作
            workflows_dir: 工作流JSON文件所在目录
        """
        self.workflows_dir = workflows_dir
        self.workflows = {}
        self.browser_context = browser_context
        self.base_handler = None
        #self.load_workflows()
        
    def set_browser_context(self, browser_context):
        """设置浏览器上下文和基础处理器"""
        from ...tools.handlers.base import BaseHandler
        self.browser_context = browser_context
        self.base_handler = BaseHandler(browser_context)
        


    def get_action_steps(self, workflow_id: str, action_id: str) -> Optional[List[Dict]]:
        """获取指定工作流中的指定操作步骤"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None
            
        for action in workflow.get("actions", []):
            if action.get("id") == action_id:
                return action.get("steps", [])
                
        return None
    
    def get_workflow_info(self, workflow_id: str) -> Optional[Dict]:
        """获取工作流信息"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None
            
        return {
            "id": workflow["id"],
            "name": workflow.get("name", ""),
            "description": workflow.get("description", ""),
            "actions": [
                {
                    "id": action.get("id", ""),
                    "name": action.get("name", ""),
                    "description": action.get("description", "")
                }
                for action in workflow.get("actions", [])
            ]
        }
    
    def get_all_workflows_info(self) -> List[Dict]:
        """获取所有工作流的基本信息"""
        return [self.get_workflow_info(workflow_id) for workflow_id in self.workflows]
    
    def resolve_step_parameter(self, parameter_value, step_results):
        """解析带有变量引用的参数值"""
        if not isinstance(parameter_value, str):
            return parameter_value
            
        # 如果是纯变量引用 (如 "${step_3.found_elements[0].index}")，则直接返回引用值而不是字符串
        pure_reference = False
        if parameter_value.startswith("${") and parameter_value.endswith("}"):
            pure_reference = True
            
        # 识别${step_X.field}形式的引用
        if '${' in parameter_value and '}' in parameter_value:
            # 提取引用表达式
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, parameter_value)
            
            for match in matches:
                try:
                    # 解析引用路径，例如 "step_3.found_elements[0].index"
                    path_parts = match.split('.')
                    step_id = path_parts[0]
                    
                    if step_id not in step_results:
                        logger.warning(f"引用了不存在的步骤结果: {step_id}")
                        continue
                        
                    # 从步骤结果中获取值
                    value = step_results[step_id]
                    for part in path_parts[1:]:
                        # 处理数组索引引用，例如 found_elements[0]
                        if '[' in part and ']' in part:
                            array_name, idx_str = part.split('[')
                            idx = int(idx_str.replace(']', ''))
                            value = value[array_name][idx]
                        else:
                            value = value[part]
                    
                    # 如果是纯变量引用，则直接返回值而不是字符串形式
                    if pure_reference:
                        return value
                        
                    # 替换引用为实际值
                    parameter_value = parameter_value.replace(f"${{{match}}}", str(value))
                except Exception as e:
                    logger.error(f"解析参数引用失败: {match}, 错误: {str(e)}")
                    
        return parameter_value
    
    async def execute_workflow(self, workflow_id: str, action_id: str) -> Dict[str, Any]:
        """
        执行指定工作流中的指定操作
        
        参数:
            workflow_id: 工作流ID
            action_id: 操作ID
            
        返回:
            操作结果
        """
        if not self.browser_context or not self.base_handler:
            return {"status": "error", "message": "尚未设置浏览器上下文，无法执行工作流"}
            
        logger.info(f"执行工作流: {workflow_id}, 操作: {action_id}")
        
        # 获取操作步骤
        steps = self.get_action_steps(workflow_id, action_id)
        if not steps:
            return {"status": "error", "message": f"未找到工作流操作: {workflow_id}.{action_id}"}
        
        # 初始化步骤结果存储
        step_results = {}
        last_result = None
        
        # 执行每个步骤
        for step in steps:
            step_id = step.get("id", f"step_{len(step_results) + 1}")
            action_name = step.get("action")
            parameters = step.get("parameters", {})
            description = step.get("description", "")
            
            logger.info(f"执行步骤 {step_id}: {action_name} - {description}")
            
            # 解析参数中的变量引用
            resolved_parameters = {}
            for param_name, param_value in parameters.items():
                resolved_value = self.resolve_step_parameter(param_value, step_results)
                resolved_parameters[param_name] = resolved_value
            
            # 检查是否是"done"操作
            if action_name == "done":
                success = resolved_parameters.get("success", False)
                text = resolved_parameters.get("text", "任务完成")
                
                result = {
                    "status": "success" if success else "partial",
                    "message": text,
                    "is_done": True,
                    "task_success": success
                }
                step_results[step_id] = result
                last_result = result
                break
            
            # 通过基础处理器执行操作
            try:
                result = await self.base_handler.process_query({
                    "action": action_name,
                    **resolved_parameters  # 展开操作参数
                })
                
                # 存储步骤结果
                step_results[step_id] = result
                last_result = result
                
                # 检查步骤是否成功，如果失败可以处理错误
                if result.get("status") != "success":
                    logger.warning(f"步骤 {step_id} 执行失败: {result.get('message', '')}")
                    
                    # 这里可以添加错误处理逻辑，例如重试或执行替代步骤
                    error_handling = step.get("error_handling", {})
                    if error_handling.get("retry", False):
                        max_retries = error_handling.get("max_retries", 1)
                        for retry_count in range(max_retries):
                            logger.info(f"重试步骤 {step_id}, 尝试 {retry_count+1}/{max_retries}")
                            result = await self.base_handler.process_query({
                                "action": action_name,
                                **resolved_parameters
                            })
                            if result.get("status") == "success":
                                step_results[step_id] = result
                                last_result = result
                                break
            except Exception as e:
                logger.error(f"执行步骤 {step_id} 出错: {str(e)}")
                result = {
                    "status": "error",
                    "message": f"步骤执行出错: {str(e)}"
                }
                step_results[step_id] = result
                last_result = result
        
        # 返回最后一个步骤的结果
        return last_result or {"status": "error", "message": "未执行任何步骤"}