from fastapi import FastAPI, HTTPException
import sys
import os
from pathlib import Path

from ...common.models import TaskRequest, TaskResponse
import httpx
from .routes.task import router as task_router
from .routes.chat import router as chat_router
app = FastAPI()

# 注册路由
app.include_router(task_router)
app.include_router(chat_router)


@app.post("/tasks")
async def create_task(request: TaskRequest) -> TaskResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/tasks",
            json=request.dict()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Task creation failed")
        return TaskResponse(**response.json())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)