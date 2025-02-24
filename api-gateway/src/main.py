# api-gateway/src/main.py
from fastapi import FastAPI, HTTPException
from common.models import TaskRequest, TaskResponse
import httpx

app = FastAPI()

@app.post("/tasks")
async def create_task(request: TaskRequest) -> TaskResponse:
    async with httpx.AsyncClient() as client:
        # 转发到编排服务
        response = await client.post(
            "http://localhost:8001/tasks",
            json=request.dict()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Task creation failed")
        return TaskResponse(**response.json())

# api-gateway/src/main.py if __name__ block
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)