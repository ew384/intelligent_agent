# tool-service/src/main.py
from fastapi import FastAPI, APIRouter
from .tools.browser import BrowserService
from .tools.llm import LLMService

app = FastAPI(title="Tool Service")
internal_router = APIRouter(prefix="/internal")  # 内部API路由

@internal_router.post("/browser/navigate")
async def navigate(request: Dict[str, Any]):
    """浏览器导航"""
    browser_service = BrowserService()
    return await browser_service.navigate(request["url"])

@internal_router.post("/llm/chat")
async def chat(request: Dict[str, Any]):
    """LLM对话"""
    llm_service = LLMService()
    return await llm_service.chat(request["prompt"])

app.include_router(internal_router)
