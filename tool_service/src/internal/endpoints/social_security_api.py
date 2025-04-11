# tool_service/src/internal/endpoints/social_security_api.py
from fastapi import APIRouter, Request
import logging
from .base_api import BaseAPI
from ...tools.handlers.social_security_handler import SocialSecurityHandler

logger = logging.getLogger(__name__)

# 创建社保API处理器
social_security_api = BaseAPI(
    handler_class=SocialSecurityHandler,
    prefix="/social_security",
    chrome_debug_port=54905
)

# 获取路由器
router = social_security_api.get_router()
