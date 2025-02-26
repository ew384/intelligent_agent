# orchestrator_service/src/main.py
from fastapi import FastAPI, Response
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))

from .routes.api import router as api_router
from .internal.endpoints.tasks import router as tasks_router

app = FastAPI(title="Orchestrator Service")

# 注册路由
app.include_router(api_router, prefix="/orchestrator")

# 为了直接响应 /tasks 请求，添加根级别的路由
app.include_router(tasks_router)  # 移除 prefix，让它直接处理 /tasks 路径

# 添加一个调试端点
@app.get("/")
async def read_root():
    return {"status": "ok", "service": "orchestrator"}

@app.post("/debug-tasks")
async def debug_tasks(data: dict):
    """
    调试用的任务端点，打印接收到的数据并返回成功
    """
    print(f"收到任务请求数据: {data}")
    return {
        "status": "success", 
        "message": "调试任务已接收", 
        "received_data": data
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
