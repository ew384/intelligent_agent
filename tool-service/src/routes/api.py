from fastapi import APIRouter
from ..internal.endpoints import browser

router = APIRouter()

# 注册各模块的路由
router.include_router(browser.router, prefix="/browser", tags=["browser"])
