from fastapi import FastAPI
from .routes.api import router as api_router

app = FastAPI(title="Scenario Service")

# 注册路由
app.include_router(api_router, prefix="/scenarios")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)