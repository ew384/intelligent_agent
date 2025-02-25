from fastapi import FastAPI, HTTPException
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))
from common.models import TaskRequest, TaskResponse
import httpx

app = FastAPI()

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