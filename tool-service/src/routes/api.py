# tool-service/src/routes/api.py
from fastapi import APIRouter
from ..internal.endpoints import browser, llm

router = APIRouter()

# 注册各模块的路由
router.include_router(browser.router, prefix="/browser", tags=["browser"])
router.include_router(llm.router, prefix="/llm", tags=["llm"])
router = APIRouter()

# 注册各模块的路由
router.include_router(browser.router, prefix="/browser", tags=["browser"])
