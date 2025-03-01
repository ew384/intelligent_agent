# orchestrator_service/src/internal/endpoints/tasks.py
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
from ...core.orchestrator import TaskOrchestrator

router = APIRouter()  # 设置前缀
logger = logging.getLogger(__name__)
orchestrator = TaskOrchestrator()

@router.post("/tasks")
async def handle_task(request: Request):
    """处理任务请求，支持多种格式"""
    try:
        # 获取并打印请求信息，帮助调试
        body = await request.json()
        logger.info(f"收到任务请求: {body}")
        
        # 提取 scenario_type 和 parameters
        scenario_type = body.get("scenario_type")
        parameters = body.get("parameters", {})
        
        if not scenario_type:
            return {"status": "error", "message": "Missing scenario_type"}
            
        logger.info(f"处理场景: {scenario_type}")
        
        # 获取对应的工作流
        workflow = orchestrator.get_workflow(scenario_type)
        if not workflow:
            logger.error(f"未找到工作流: {scenario_type}")
            return {"status": "error", "message": f"Workflow not found for {scenario_type}"}
        
        # 执行工作流
        result = await workflow.execute(parameters)
        logger.info(f"工作流执行结果: {result}")
        
        return result
    except Exception as e:
        logger.exception(f"任务处理失败: {str(e)}")
        return {"status": "error", "message": str(e)}
# orchestrator_service/src/internal/endpoints/tasks.py

# 添加一个简单的内存存储来保存任务状态
task_storage = {}

@router.post("/tasks/continue")
async def continue_task(request: Request):
    """继续执行之前暂停的任务"""
    try:
        body = await request.json()
        task_id = body.get("task_id")
        
        if not task_id:
            return {"status": "error", "message": "Missing task_id"}
        
        # 获取任务状态
        task_data = task_storage.get(task_id)
        if not task_data:
            return {"status": "error", "message": f"Task {task_id} not found"}
        
        # 获取工作流类型
        scenario_type = task_data.get("scenario_type")
        parameters = task_data.get("parameters", {})
        current_step_index = task_data.get("current_step_index", 0)
        results = task_data.get("results", {})
        
        # 获取工作流
        workflow = orchestrator.get_workflow(scenario_type)
        if not workflow:
            return {"status": "error", "message": f"Workflow not found for {scenario_type}"}
        
        # 继续执行工作流
        result = await workflow.continue_from(parameters, results, current_step_index + 1)
        
        return result
    except Exception as e:
        logger.exception(f"继续任务失败: {str(e)}")
        return {"status": "error", "message": str(e)}