# api-gateway/src/routes/chat.py
@router.post("/chat")
async def create_chat(request: ChatRequest):
    """创建对话任务"""
    task = {
        "type": "chat",
        "provider": request.provider,
        "prompt": request.prompt,
        "image_path": request.image_path
    }
    
    return await orchestrator_client.create_task(task)