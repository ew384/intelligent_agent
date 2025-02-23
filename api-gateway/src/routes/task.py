# api-gateway/src/routes/tasks.py
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.post("/tasks")
async def create_task(request: Dict[str, Any]):
    """统一的任务创建入口"""
    # 处理认证、权限等
    # 路由到正确的服务
    return await orchestrator_client.create_task(request)

@router.post("/tools/{tool_type}")
async def invoke_tool(tool_type: str, request: Dict[str, Any]):
    """直接工具调用入口"""
    # 转发到tool-service
    return await tool_client.invoke_tool(tool_type, request)