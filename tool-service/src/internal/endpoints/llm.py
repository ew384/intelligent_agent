from fastapi import APIRouter, HTTPException
from typing import Dict

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
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
Improve
