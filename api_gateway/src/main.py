from fastapi import FastAPI, HTTPException
import sys
import os
from pathlib import Path
#import pdb; pdb.set_trace()
# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))

from common.models import TaskRequest, TaskResponse
import httpx
from .routes.task import router as task_router
from .routes.chat import router as chat_router

app = FastAPI()

# 注册路由
app.include_router(task_router)
app.include_router(chat_router)

@app.post("/tasks")
async def create_task(request: TaskRequest) -> TaskResponse:
    try:
        
        print(f"Request data: {request.dict()}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/tasks",
                json=request.dict(),
                timeout=30.0  # 设置合理的超时时间
            )
            response.raise_for_status()
            return TaskResponse(**response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"服务调用失败: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"内部服务错误: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
