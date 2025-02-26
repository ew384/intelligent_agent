# api-gateway/src/routes/chat.py
from fastapi import APIRouter
from typing import Dict, Any

# 创建 router 对象，这在原始代码中缺失
router = APIRouter()

# 加载客户端
from ..clients.orchestrator import orchestrator_client

@router.post("/chat")
async def create_chat(request: Dict[str, Any]):
    """创建对话任务"""
    task = {
        "type": "chat",
        "provider": request.get("provider"),
        "prompt": request.get("prompt"),
        "image_path": request.get("image_path")
    }
    
    return await orchestrator_client.create_task(task)
