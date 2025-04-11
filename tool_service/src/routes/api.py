# tool-service/src/routes/api.py
from fastapi import APIRouter
from ..internal.endpoints import browser_api, wechat_api, tax_api, social_security_api

router = APIRouter()

# 注册各模块的路由
router.include_router(browser_api.router, prefix="/browser", tags=["browser"])
router.include_router(wechat_api.router, prefix="/wechat", tags=["wechat"])
router.include_router(tax_api.router, tags=["tax"])  # 移除prefix
router.include_router(social_security_api.router, tags=["social_security"])  # 移除prefix，并使用正确的路由器