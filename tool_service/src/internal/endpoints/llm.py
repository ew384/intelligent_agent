from fastapi import APIRouter, HTTPException
from typing import Dict
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(current_path))

# 修复导入路径
from ...tools.llm.claude.service import ClaudeService
from ...tools.browser.browser_manager import BrowserManager

# 获取或创建browser_manager实例
browser_manager = BrowserManager()
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat/{provider}")
async def chat_with_llm(provider: str, request: Dict):
    """LLM对话API"""
    try:
        # 根据provider选择相应的LLM服务
        if provider == "claude":
            service = ClaudeService(browser_manager)
            await service.initialize()
            
            responses = []
            async for response in service.chat(
                request["prompt"],
                request.get("file_paths"),
                request.get("stream"),
                request.get("new_chat"),
            ):
                responses.append(response)
            
            return {"status": "success", "responses": responses}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的LLM提供商: {provider}"
            )
            
    except Exception as e:
        logger.error(f"LLM对话出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
