from fastapi import FastAPI
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))

from .routes.api import router as api_router
from .tools.browser.browser_service import BrowserService

app = FastAPI(title="Tool Service")

# 初始化全局服务
browser_service = BrowserService(headless=False)

# 注册路由
app.include_router(api_router, prefix="/tools")

@app.on_event("startup")
async def startup_event():
    # 服务启动时的初始化
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # 服务关闭时的清理
    await browser_service.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
