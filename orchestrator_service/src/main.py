# orchestrator_service/src/main.py
from fastapi import FastAPI, Response, Request
import sys
import os
from pathlib import Path

import logging
import json

# 配置日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))

from .routes.api import router as api_router
from .internal.endpoints.tasks import router as tasks_router

app = FastAPI(title="Orchestrator Service")

# 注册路由
app.include_router(api_router, prefix="/orchestrator")
app.include_router(tasks_router) 

@app.post("/direct-tasks")
async def direct_tasks_handler(request: Request):
    """直接处理/direct-tasks路径的请求，用于测试对比"""
    logger.info("直接处理任务请求")
    try:
        body = await request.json()
        logger.info(f"直接路由收到任务请求: {body}")
        return {"status": "direct", "received": body}
    except Exception as e:
        logger.exception("直接处理任务请求失败")
        return {"status": "error", "message": str(e)}

# 添加一个调试端点

@app.get("/")
async def read_root():
    return {"status": "ok", "service": "orchestrator"}


if __name__ == "__main__":
    logger.info("服务启动中，检查所有注册的路由:")
    for route in app.routes:
        logger.info(f"路由: {route.path} {route.methods}")
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
