from fastapi import APIRouter, HTTPException
from typing import Dict
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(current_path))

# 修复导入路径
from ...tools.llm.claude.service import ClaudeService
from ...tools.browser.browser_service import BrowserService

# 获取或创建browser_service实例
browser_service = BrowserService(headless=False)
router = APIRouter()

@router.post("/chat/{provider}")
async def chat_with_llm(provider: str, request: Dict):
    """LLM对话API"""
    try:
        # 根据provider选择相应的LLM服务
        if provider == "claude":
            service = ClaudeService(browser_service)
            await service.initialize()
            
            responses = []
            async for response in service.chat(
                request["prompt"],
                request.get("image_path")
            ):
                responses.append(response)
            
            return {"status": "success", "responses": responses}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的LLM提供商: {provider}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
