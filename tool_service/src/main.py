# tool_service/src/main.py
from fastapi import FastAPI, Request
import sys
import os
from pathlib import Path
import logging
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tool_service")

# 创建FastAPI应用
app = FastAPI(title="Tool Service")

# 导入主路由
from .routes.api import router as api_router

# 导入工作流API路由
from .internal.endpoints.workflow_api import router as workflow_router

# 注册主路由 - 所有子路由都通过api_router注册
app.include_router(api_router, prefix="/tools")

# 注册工作流API路由
app.include_router(workflow_router)#, prefix="/workflow")

@app.get("/")
async def root():
    """服务根路径"""
    # 获取工作流信息
    workflows_dir = Path("workflows")
    available_workflows = []
    
    if workflows_dir.exists():
        for workflow_file in workflows_dir.glob("*.json"):
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    available_workflows.append({
                        "id": workflow.get("id", ""),
                        "name": workflow.get("name", ""),
                    })
            except Exception as e:
                logger.error(f"读取工作流文件失败 {workflow_file}: {str(e)}")
    
    return {
        "service": "Tool Service",
        "status": "running",
        "endpoints": [
            "/tools/browser/{action}",
            #"/tools/llm/chat/claude",
            "/tools/wechat/{action}",
            "/tools/tax/{action}",
            "/tools/tax/query_complete",
        ],
        "workflow_endpoints": [
            "/workflow/list",
            "/workflow/{workflow_id}",
            "/workflow/{workflow_id}/execute",
            "/workflow/{workflow_id}/test",
            "/workflow/search"
        ],
        "available_workflows": available_workflows
    }

@app.on_event("startup")
async def startup_event():
    """服务启动时执行，初始化工作流目录"""
    # 确保工作流目录存在
    workflows_dir = Path("workflows")
    workflows_dir.mkdir(exist_ok=True)
    
    # 检查并记录工作流数量
    workflow_count = len(list(workflows_dir.glob("*.json")))
    logger.info(f"服务已启动，工作流目录中包含 {workflow_count} 个工作流文件")

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时执行"""
    logger.info("服务正在关闭...")

if __name__ == "__main__":
    import uvicorn
    # 确保运行在正确的包路径下
    uvicorn.run("tool_service.src.main:app", host="0.0.0.0", port=8003, reload=True)