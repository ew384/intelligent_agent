from fastapi import FastAPI
import sys
import os
from pathlib import Path

from .routes.api import router as api_router

app = FastAPI(title="Orchestrator Service")

# 注册路由
app.include_router(api_router, prefix="/orchestrator")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
