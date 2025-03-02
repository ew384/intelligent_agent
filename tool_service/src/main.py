# tool_service/src/main.py
from fastapi import FastAPI, Request
import sys
import os
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tool_service")

# 创建FastAPI应用
app = FastAPI(title="Tool Service")

# 导入主路由
from .routes.api import router as api_router

# 注册主路由 - 所有子路由都通过api_router注册
app.include_router(api_router, prefix="/tools")

@app.get("/")
async def root():
    """服务根路径"""
    return {
        "service": "Tool Service",
        "status": "running",
        "endpoints": [
            "/tools/browser/{action}",
            "/tools/browser/credit-card",
            "/tools/llm/generate",
            "/tools/wechat/{action}",
            "/tools/wechat/login/check"
        ]
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    path = request.url.path
    method = request.method
    logger.info(f"收到请求: {method} {path}")
    
    response = await call_next(request)
    
    status_code = response.status_code
    logger.info(f"响应: {method} {path} - {status_code}")
    
    return response

if __name__ == "__main__":
    import uvicorn
    # 确保运行在正确的包路径下
    uvicorn.run("tool_service.src.main:app", host="0.0.0.0", port=8003, reload=True)