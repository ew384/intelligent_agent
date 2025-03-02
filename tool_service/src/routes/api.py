# tool-service/src/routes/api.py
from fastapi import APIRouter
from ..internal.endpoints import browser_api, llm, wechat_api

router = APIRouter()

# 注册各模块的路由
router.include_router(browser_api.router, prefix="/browser", tags=["browser"])
router.include_router(llm.router, prefix="/llm", tags=["llm"])
router.include_router(wechat_api.router, prefix="/wechat", tags=["wechat"])