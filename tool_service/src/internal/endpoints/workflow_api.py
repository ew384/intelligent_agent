from fastapi import APIRouter, Request, Path, Query, HTTPException, Body
import logging
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from ...tools.workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflow", tags=["workflow"])

# 浏览器实例管理
browser_instances = {}
workflow_engines = {}

# 数据模型
class WorkflowInfo(BaseModel):
    id: str
    name: str
    description: str
    actions: List[Dict[str, str]]

class ExecuteWorkflowRequest(BaseModel):
    action_id: str

class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowInfo]

class WorkflowMatchRequest(BaseModel):
    query: str
    
class WorkflowMatchResponse(BaseModel):
    matched: bool
    workflow_id: Optional[str] = None
    action_id: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: str

# 初始化浏览器和工作流引擎
async def init_browser_and_engine(session_id: str, chrome_debug_port: int = 54905):
    """初始化浏览器和工作流引擎"""
    if session_id in browser_instances:
        return browser_instances[session_id], workflow_engines[session_id]
    
    # 配置连接到已有的Chrome
    browser_config = BrowserConfig(
        cdp_url=f"http://localhost:{chrome_debug_port}"
    )
    
    # 创建Browser实例
    browser = Browser(config=browser_config)
    
    # 创建BrowserContext
    browser_context = BrowserContext(browser=browser)
    
    # 初始化会话
    await browser_context._initialize_session()
    logger.info("浏览器和上下文初始化完成，已连接到Chrome实例")
    
    # 创建工作流引擎
    workflow_engine = WorkflowEngine()
    workflow_engine.set_browser_context(browser_context)
    
    # 存储实例
    browser_instances[session_id] = browser_context
    workflow_engines[session_id] = workflow_engine
    
    logger.info(f"为会话 {session_id} 初始化浏览器和工作流引擎")
    return browser_context, workflow_engine

async def cleanup_session(session_id: str):
    """清理会话资源"""
    if session_id in browser_instances:
        browser_context = browser_instances[session_id]
        browser = browser_context.browser
        
        await browser_context.close()
        await browser.close()
        
        del browser_instances[session_id]
        del workflow_engines[session_id]
        
        logger.info(f"已清理会话 {session_id} 资源")

# API 端点
@router.get("/list", response_model=WorkflowListResponse)
async def list_workflows(session_id: str = Query(..., description="会话ID")):
    """获取所有可用工作流列表"""
    # 初始化会话
    _, workflow_engine = await init_browser_and_engine(session_id)
    
    # 获取所有工作流信息
    workflows_info = workflow_engine.get_all_workflows_info()
    
    return {"workflows": workflows_info}

@router.get("/{workflow_id}", response_model=WorkflowInfo)
async def get_workflow_info(
    workflow_id: str = Path(..., description="工作流ID"),
    session_id: str = Query(..., description="会话ID")
):
    """获取特定工作流的详细信息"""
    # 初始化会话
    _, workflow_engine = await init_browser_and_engine(session_id)
    
    # 获取工作流信息
    workflow_info = workflow_engine.get_workflow_info(workflow_id)
    if not workflow_info:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    return workflow_info

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    request: ExecuteWorkflowRequest,
    workflow_id: str = Path(..., description="工作流ID"),
    session_id: str = Query(..., description="会话ID")
):
    """执行特定工作流的操作"""
    # 初始化会话
    _, workflow_engine = await init_browser_and_engine(session_id)
    
    # 验证工作流是否存在
    workflow_info = workflow_engine.get_workflow_info(workflow_id)
    print(workflow_info)
    if not workflow_info:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    # 验证操作是否存在
    action_exists = any(action["id"] == request.action_id for action in workflow_info["actions"])
    if not action_exists:
        raise HTTPException(status_code=404, detail=f"操作 {request.action_id} 在工作流 {workflow_id} 中不存在")
    
    try:
        # 执行工作流
        result = await workflow_engine.execute_workflow(workflow_id, request.action_id)
        return {
            "workflow_id": workflow_id,
            "action_id": request.action_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"执行工作流 {workflow_id}.{request.action_id} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行工作流失败: {str(e)}")

@router.post("/{workflow_id}/test")
async def test_workflow(
    workflow_id: str = Path(..., description="工作流ID"),
    action_id: str = Query(..., description="操作ID"),
    session_id: str = Query(..., description="会话ID")
):
    """测试特定工作流的操作，提供详细的步骤执行信息"""
    # 初始化会话
    browser_context, workflow_engine = await init_browser_and_engine(session_id)
    
    # 验证工作流是否存在
    workflow_info = workflow_engine.get_workflow_info(workflow_id)
    if not workflow_info:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    # 验证操作是否存在
    action_exists = any(action["id"] == action_id for action in workflow_info["actions"])
    if not action_exists:
        raise HTTPException(status_code=404, detail=f"操作 {action_id} 在工作流 {workflow_id} 中不存在")
    
    try:
        # 获取操作步骤
        steps = workflow_engine.get_action_steps(workflow_id, action_id)
        if not steps:
            raise HTTPException(status_code=404, detail=f"未找到工作流操作步骤: {workflow_id}.{action_id}")
        
        # 执行工作流并收集详细结果
        result = await workflow_engine.execute_workflow(workflow_id, action_id)
        
        return {
            "workflow_id": workflow_id,
            "action_id": action_id,
            "steps_count": len(steps),
            "result": result
        }
    except Exception as e:
        logger.error(f"测试工作流 {workflow_id}.{action_id} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试工作流失败: {str(e)}")

@router.post("/match", response_model=WorkflowMatchResponse)
async def match_workflow(
    request: WorkflowMatchRequest = Body(...),
    session_id: str = Query(..., description="会话ID")
):
    """使用智能匹配算法，根据用户查询匹配最合适的工作流"""
    # 初始化会话
    browser_context, workflow_engine = await init_browser_and_engine(session_id)
    
    try:
        from ...agents.universal_agent import UniversalAgent
        
        # 临时创建Universal Agent实例，用于调用工作流匹配方法
        # 注意：这里不使用浏览器功能，只使用LLM匹配功能
        temp_agent = UniversalAgent(
            LLM_api_url="http://localhost:8005/chat/claude",
            api_key={"api-key": "wangendian"}
        )
        temp_agent.workflow_engine = workflow_engine
        
        # 分析用户查询与工作流的匹配度
        match_result = temp_agent.analyze_workflow_match(request.query)
        
        return match_result
    except Exception as e:
        logger.error(f"工作流匹配分析失败: {str(e)}")
        return {
            "matched": False,
            "confidence": 0,
            "reasoning": f"匹配分析过程中出错: {str(e)}"
        }

@router.post("/cleanup")
async def cleanup(session_id: str = Query(..., description="会话ID")):
    """清理会话资源"""
    await cleanup_session(session_id)
    return {"status": "success", "message": f"会话 {session_id} 资源已清理"}