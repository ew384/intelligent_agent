# api_gateway/src/routes/task.py
from fastapi import APIRouter
from typing import Dict, Any
import httpx

router = APIRouter()

# 添加客户端实例导入
from ..clients.orchestrator import orchestrator_client

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
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8003/tools/{tool_type}",
            json=request,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
