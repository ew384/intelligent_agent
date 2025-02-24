"""
API Gateway Service

Provides the main entry point and routing for the intelligent agent system.
"""

from .src.main import app  # 导出 FastAPI 应用实例

__all__ = ['app']