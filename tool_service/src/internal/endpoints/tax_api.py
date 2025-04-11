# tool_service/src/internal/endpoints/tax_api.py
from fastapi import APIRouter, Request
import logging
from datetime import datetime, timedelta
from .base_api import BaseAPI
from ...tools.handlers.tax_handler import TaxHandler

logger = logging.getLogger(__name__)

# 创建税务API处理器
tax_api = BaseAPI(
    handler_class=TaxHandler,
    prefix="/tax",
    chrome_debug_port=54905
)

# 获取路由器
router = tax_api.get_router()