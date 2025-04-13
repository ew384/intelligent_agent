# tool_service/src/routes/api.py
from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# 导入原有的API模块 - 保持向后兼容
# 这些会逐步被工作流功能取代，但为了平稳过渡保留原有接口
from ..internal.endpoints.tax_api import router as tax_router
from ..internal.endpoints.workflow_api import router as social_security_router

# 添加原有API路由
router.include_router(tax_router)
router.include_router(social_security_router)

@router.get("/info")
async def get_api_info():
    """获取API信息"""
    return {
        "status": "active",
        "message": "原有API保持可用，建议迁移到工作流API",
        "legacy_endpoints": [
            "/tools/tax/{action}",
            "/tools/social_security/{action}"
        ],
        "recommended_endpoints": [
            "/workflow/list",
            "/workflow/{workflow_id}",
            "/workflow/{workflow_id}/execute"
        ]
    }