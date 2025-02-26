from fastapi import FastAPI
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))

from .routes.api import router as api_router

app = FastAPI(title="Scenario Service")

# 注册路由
app.include_router(api_router, prefix="/scenarios")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
