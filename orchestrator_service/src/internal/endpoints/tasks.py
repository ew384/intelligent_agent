# orchestrator_service/src/internal/endpoints/tasks.py
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import logging
from ...core.orchestrator import TaskOrchestrator

router = APIRouter(prefix="/tasks")  # 设置前缀
logger = logging.getLogger(__name__)
orchestrator = TaskOrchestrator()

@router.post("/")
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
