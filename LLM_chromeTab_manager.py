from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Dict, Optional, List, Any, Union
import asyncio
import uuid
import logging
from pathlib import Path
import sys
import json
import os

from tool_service.src.tools.browser.browser_session import BrowserSession
from tool_service.src.tools.llm.claude.auth_handler import ClaudeAuthHandler

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM API Service")

# 数据模型
class TabRequest(BaseModel):
    provider: str  # 提供商：claude, chatgpt等

class ChatRequest(BaseModel):
    prompt: str
    new_chat: bool = False
    file_paths: Optional[List[str]] = None

# 全局状态
browser_session = None
api_keys = {
    "wangendian": "user_1",
    "chenhao": "user_2",
    "evaluation": "agent_1",
    "conversation": "agent_2",
    "summarization": "agent_3",
}

# 用户标签页映射: {api_key: {provider: {"handle": window_handle, "tab_id": tab_id, "handler": handler_instance}}}
# 注意这里改为按provider组织而不是按tab_id
user_tabs = {key: {} for key in api_keys}

# 锁对象
lock = asyncio.Lock()

# 数据持久化文件
TABS_STATE_FILE = "tabs_state.json"

def save_tabs_state():
    """Save tab state to file"""
    try:
        # Load existing state
        state = {}
        if os.path.exists(TABS_STATE_FILE):
            try:
                with open(TABS_STATE_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:  # Only try to load if file is not empty
                        state = json.loads(content)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in {TABS_STATE_FILE}, starting with empty state")
                state = {}
        
        if "tabs" not in state:
            state["tabs"] = {}
        
        # Update LLM tabs
        for api_key, providers in user_tabs.items():
            user_id = api_keys.get(api_key)
            
            for provider, tab_info in providers.items():
                tab_id = tab_info.get("tab_id")
                if tab_id:
                    state["tabs"][tab_id] = {
                        "handle": tab_info.get("handle"),
                        "type": "llm",
                        "provider": provider,
                        "service_id": provider,
                        "user_id": user_id,
                        "url": browser_session.driver.current_url if browser_session else ""
                    }
        
        # Write state
        with open(TABS_STATE_FILE, 'w') as f:
            json.dump(state, f)
        
        logger.info("Tab state saved")
    except Exception as e:
        logger.error(f"Failed to save tab state: {str(e)}")


def load_tabs_state():
    """Load tab state from file"""
    try:
        if not os.path.exists(TABS_STATE_FILE):
            logger.info("No tab state file found")
            return
        
        try:
            with open(TABS_STATE_FILE, 'r') as f:
                content = f.read().strip()
                if not content:  # File is empty
                    logger.warning(f"{TABS_STATE_FILE} is empty, no state to load")
                    return
                state = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {TABS_STATE_FILE}, skipping load")
            return
        
        # Clear current state
        for api_key in user_tabs:
            user_tabs[api_key] = {}
        
        # Get tabs
        tabs = state.get("tabs", {})
        
        # Load LLM tabs
        for tab_id, info in tabs.items():
            if info.get("type") == "llm":
                provider = info.get("provider")
                handle = info.get("handle")
                user_id = info.get("user_id")
                
                # Find API key for user
                matching_api_key = None
                for api_key, uid in api_keys.items():
                    if uid == user_id:
                        matching_api_key = api_key
                        break
                
                if matching_api_key and provider:
                    user_tabs[matching_api_key][provider] = {
                        "tab_id": tab_id,
                        "handle": handle,
                        "handler": None  # Create when needed
                    }
        
        logger.info("Tab state loaded")
    except Exception as e:
        logger.error(f"Failed to load tab state: {str(e)}")

async def validate_existing_tabs():
    """验证和清理已加载的标签页状态"""
    try:
        if not browser_session:
            logger.warning("浏览器会话不可用，无法验证标签页")
            return
        
        # 获取所有当前窗口句柄
        current_handles = await browser_session.get_all_tabs()
        
        # 验证每个用户的标签页
        for api_key, providers in user_tabs.items():
            invalid_providers = []
            
            for provider, tab_info in providers.items():
                handle = tab_info.get("handle")
                
                # 检查句柄是否有效
                if handle not in current_handles:
                    logger.warning(f"用户 {api_key} 的 {provider} 标签页句柄无效")
                    invalid_providers.append(provider)
                else:
                    # 句柄有效，切换并验证
                    try:
                        await browser_session.switch_to_tab(handle)
                        
                        # 如果是Claude，创建处理器
                        if provider == "claude":
                            tab_info["handler"] = ClaudeAuthHandler(browser_session)
                            
                        logger.info(f"用户 {api_key} 的 {provider} 标签页验证成功")
                    except Exception as e:
                        logger.error(f"验证标签页时出错: {str(e)}")
                        invalid_providers.append(provider)
            
            # 移除无效的标签页
            for invalid_provider in invalid_providers:
                user_tabs[api_key].pop(invalid_provider, None)
        
        # 更新持久化状态
        save_tabs_state()
        
    except Exception as e:
        logger.error(f"验证标签页状态时出错: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化浏览器会话"""
    global browser_session
    try:
        # 初始化浏览器会话
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:54805")
        driver_path =["/home/endian/.local/share/undetected_chromedriver/undetected_chromedriver",
                    "/usr/local/bin/chromedriver"]
        for path in driver_path:
            if os.path.exists(path):
                driver_path = path
                break
        uc_driver_port=54806
        service = Service(driver_path,port=uc_driver_port)#use different port for chromedriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 创建BrowserService模拟对象
        class SimpleBrowserService:
            def __init__(self):
                self.screenshots_dir = Path("./screenshots")
                self.cookies_manager = None
        
        browser_service = SimpleBrowserService()
        browser_session = BrowserSession(driver, service, browser_service)
        
        logger.info("成功初始化浏览器会话")
        
        # 从文件加载标签页状态
        load_tabs_state()
        
        # 验证和清理已加载的标签页状态
        await validate_existing_tabs()
        
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时保存状态"""
    save_tabs_state()

async def reinitialize_browser_session():
    """重新初始化浏览器会话"""
    global browser_session
    try:
        logger.info("尝试重新初始化浏览器会话")
        
        # 关闭现有会话
        if browser_session:
            try:
                await browser_session.close()
            except:
                pass
        
        # 重新创建会话
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:54805")
        #service = Service("/usr/local/bin/chromedriver")#"/home/endian/.local/share/undetected_chromedriver/undetected_chromedriver")
        uc_driver_port=54806
        service = Service("/home/endian/.local/share/undetected_chromedriver/undetected_chromedriver",port=uc_driver_port)
        # 尝试创建驱动
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"重新创建WebDriver失败: {str(e)}")
            raise
        
        # 创建BrowserService模拟对象
        class SimpleBrowserService:
            def __init__(self):
                self.screenshots_dir = Path("./screenshots")
                self.cookies_manager = None
        
        browser_service = SimpleBrowserService()
        browser_session = BrowserSession(driver, service, browser_service)
        
        logger.info("成功重新初始化浏览器会话")
        
        # 清理无效的标签页引用
        for api_key in user_tabs:
            invalid_providers = []
            for provider in user_tabs[api_key]:
                user_tabs[api_key][provider]["handler"] = None
                invalid_providers.append(provider)
            
            # 移除所有无效提供商
            for invalid_provider in invalid_providers:
                user_tabs[api_key].pop(invalid_provider, None)
        
        # 更新持久化状态
        save_tabs_state()
        
        return True
    except Exception as e:
        logger.error(f"重新初始化浏览器会话失败: {str(e)}")
        return False

async def get_api_key(api_key: str = Header(...)):
    """验证API密钥并返回用户信息"""
    if api_key not in api_keys:
        raise HTTPException(status_code=401, detail="无效的API密钥")
    return api_key

# Add this new endpoint to allow manual cleanup
@app.post("/admin/cleanup")
async def manual_cleanup(api_key: str = Depends(get_api_key)):
    """Manually trigger a cleanup of the tabs state file"""
    global last_cleanup_time
    
    try:
        # Perform cleanup
        await cleanup_tabs_state()
        last_cleanup_time = time.time()
        
        # Also validate existing tabs
        await validate_existing_tabs()
        
        return {
            "status": "success",
            "message": "Tab state cleanup completed successfully"
        }
    except Exception as e:
        logger.error(f"Manual cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual cleanup failed: {str(e)}")

# For an even more aggressive cleanup, you can add an option to completely reset the state
@app.post("/admin/reset_state")
async def reset_state(api_key: str = Depends(get_api_key)):
    """Reset the tabs state file completely"""
    global last_cleanup_time
    
    try:
        # Create a new empty state
        with open(TABS_STATE_FILE, 'w') as f:
            json.dump({"tabs": {}}, f)
            
        # Clear in-memory state
        for key in user_tabs:
            user_tabs[key] = {}
            
        last_cleanup_time = time.time()
        
        return {
            "status": "success",
            "message": "Tab state has been completely reset"
        }
    except Exception as e:
        logger.error(f"State reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"State reset failed: {str(e)}")

@app.post("/tabs")
async def create_tab(request: TabRequest, api_key: str = Depends(get_api_key)):
    """为用户创建新标签页，如果已有相同提供商的标签页则返回现有标签页"""
    async with lock:
        try:
            provider = request.provider
            
            # 检查浏览器会话是否有效
            try:
                # 尝试简单的浏览器操作来验证会话有效性
                current_handles = await browser_session.get_all_tabs()
                logger.info(f"当前有 {len(current_handles)} 个标签页")
            except Exception as e:
                logger.error(f"浏览器会话无效: {str(e)}")
                # 尝试重新初始化浏览器会话
                await reinitialize_browser_session()
                current_handles = await browser_session.get_all_tabs()
            
            # 检查用户是否已经有这个提供商的标签页
            if provider in user_tabs[api_key] and user_tabs[api_key][provider].get("handle"):
                # 验证标签页是否仍然有效
                handle = user_tabs[api_key][provider]["handle"]
                try:
                    if handle in current_handles:
                        await browser_session.switch_to_tab(handle)
                        # 标签页有效，返回现有信息
                        return {
                            "status": "success",
                            "message": f"已有{provider}标签页",
                            "tab_id": user_tabs[api_key][provider]["tab_id"],
                            "provider": provider,
                            "title": browser_session.driver.title,
                            "url": browser_session.driver.current_url
                        }
                except Exception:
                    # 标签页无效，继续创建新标签页
                    logger.info(f"现有{provider}标签页无效，创建新标签页")
                    # 从映射中移除无效标签页
                    user_tabs[api_key].pop(provider, None)
            
            # 定义提供商URL
            provider_urls = {
                "claude": "https://claude.ai/",
                "chatgpt": "https://chatgpt.com/",
                "qwen":"https://chat.qwen.ai/",
                "deepseek":"https://chat.deepseek.com/"
            }
            
            if provider not in provider_urls:
                raise HTTPException(status_code=400, detail=f"不支持的提供商: {provider}")
            
            # 查找未被使用的标签页
            unused_handles = []
            for handle in current_handles:
                is_used = False
                # 检查此标签页是否已被任何用户使用
                for user_api_key, providers in user_tabs.items():
                    for provider_name, provider_info in providers.items():
                        if provider_info.get("handle") == handle:
                            is_used = True
                            break
                    if is_used:
                        break
                
                if not is_used:
                    unused_handles.append(handle)
            
            logger.info(f"找到 {len(unused_handles)} 个未使用的标签页")
            
            # 使用未使用的标签页或创建新标签页
            if unused_handles:
                try:
                    new_handle = unused_handles[0]
                    success = await browser_session.switch_to_tab(new_handle)
                    if not success:
                        raise Exception("切换到未使用标签页失败")
                    logger.info(f"使用现有未使用标签页: {new_handle}")
                except Exception as e:
                    logger.warning(f"使用未使用标签页失败: {str(e)}，将创建新标签页")
                    unused_handles = []  # 清空未使用标签页列表，强制创建新标签页
            
            # 如果没有可用的未使用标签页，创建新标签页
            if not unused_handles:
                try:
                    logger.info("创建新标签页")
                    # 记录当前标签页列表
                    before_handles = await browser_session.get_all_tabs()
                    
                    # 使用 Selenium 原生方法创建新标签页，更可靠
                    browser_session.driver.switch_to.new_window('tab')
                    await asyncio.sleep(1)
                    
                    # 获取新的标签页列表
                    after_handles = await browser_session.get_all_tabs()
                    
                    # 找出新增的标签页
                    new_tabs = [h for h in after_handles if h not in before_handles]
                    
                    if new_tabs:
                        new_handle = new_tabs[0]
                        logger.info(f"成功创建新标签页: {new_handle}")
                    else:
                        # 如果检测不到新标签页，使用当前标签页
                        new_handle = await browser_session.get_current_tab()
                        logger.warning(f"未检测到新标签页，使用当前标签页: {new_handle}")
                    
                    # 确保切换到新标签页
                    success = await browser_session.switch_to_tab(new_handle)
                    if not success:
                        raise Exception("无法切换到新标签页")
                    
                except Exception as e:
                    logger.error(f"创建新标签页失败: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"创建新标签页失败: {str(e)}")
            else:
                new_handle = unused_handles[0]
            
            # 导航到提供商URL
            try:
                logger.info(f"导航到URL: {provider_urls[provider]}")
                success = await browser_session.goto(provider_urls[provider])
                if not success:
                    raise Exception(f"导航到 {provider_urls[provider]} 失败")
                
                # 等待页面加载
                await browser_session.wait_for_load_state("networkidle")
                
            except Exception as e:
                logger.error(f"导航到 {provider} 页面失败: {str(e)}")
                # 关闭失败的标签页
                try:
                    await browser_session.close_tab(new_handle)
                except:
                    pass
                raise HTTPException(status_code=500, detail=f"导航到 {provider} 页面失败: {str(e)}")
            
            # 创建对应的处理器
            handler = None
            if provider == "claude":
                try:
                    handler = ClaudeAuthHandler(browser_session)
                    logger.info("成功创建Claude处理器")
                except Exception as e:
                    logger.error(f"创建Claude处理器失败: {str(e)}")
            # 可以添加其他处理器
            
            # 生成标签页ID
            tab_id = str(uuid.uuid4())
            
            # 保存标签页信息
            user_tabs[api_key][provider] = {
                "tab_id": tab_id,
                "handle": new_handle,
                "handler": handler
            }
            
            # 更新持久化状态
            save_tabs_state()
            
            return {
                "status": "success",
                "tab_id": tab_id,
                "provider": provider,
                "title": browser_session.driver.title,
                "url": browser_session.driver.current_url
            }
            
        except Exception as e:
            logger.error(f"创建标签页失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"创建标签页失败: {str(e)}")

@app.delete("/tabs/{provider}")
async def close_tab(provider: str, api_key: str = Depends(get_api_key)):
    """关闭指定提供商的标签页"""
    async with lock:
        if provider not in user_tabs[api_key]:
            raise HTTPException(status_code=404, detail=f"找不到提供商 {provider} 的标签页")
        
        try:
            # 获取句柄
            handle = user_tabs[api_key][provider]["handle"]
            
            # 关闭标签页
            success = await browser_session.close_tab(handle)
            if not success:
                raise HTTPException(status_code=500, detail="关闭标签页失败")
            
            # 从映射中移除
            user_tabs[api_key].pop(provider)
            
            # 更新持久化状态
            save_tabs_state()
            
            return {"status": "success", "message": f"{provider}标签页已关闭"}
        except Exception as e:
            logger.error(f"关闭标签页失败: {str(e)}")
            # 从映射中移除（即使关闭失败）
            user_tabs[api_key].pop(provider, None)
            save_tabs_state()
            raise HTTPException(status_code=500, detail=f"关闭标签页失败: {str(e)}")

@app.get("/tabs")
async def list_tabs(api_key: str = Depends(get_api_key)):
    """列出用户的所有标签页"""
    try:
        tabs = []
        for provider, tab_info in user_tabs[api_key].items():
            try:
                # 切换到标签页
                await browser_session.switch_to_tab(tab_info["handle"])
                
                # 获取标签页信息
                tabs.append({
                    "tab_id": tab_info["tab_id"],
                    "provider": provider,
                    "title": browser_session.driver.title,
                    "url": browser_session.driver.current_url
                })
            except Exception as e:
                logger.error(f"获取标签页信息失败: {str(e)}")
                # 移除无效标签页
                user_tabs[api_key].pop(provider, None)
        
        # 更新持久化状态
        save_tabs_state()
        
        return tabs
    except Exception as e:
        logger.error(f"列出标签页失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出标签页失败: {str(e)}")

@app.post("/chat/{provider}")
async def chat_with_llm(
    provider: str, 
    request: Dict[str, Any], 
    api_key: str = Depends(get_api_key)
):
    """LLM对话API"""
    try:
        # 检查provider是否存在
        if provider not in user_tabs[api_key]:
            raise HTTPException(status_code=404, detail=f"找不到提供商 {provider} 的标签页")
        
        # 获取标签页信息
        tab_info = user_tabs[api_key][provider]
        
        # 切换到标签页
        await browser_session.switch_to_tab(tab_info["handle"])
        
        # 根据provider选择相应的LLM服务
        if provider == "claude":
            handler = tab_info["handler"]
            if not handler:
                # 如果handler不存在，重新创建
                handler = ClaudeAuthHandler(browser_session)
                tab_info["handler"] = handler
            
            # 获取参数
            prompt = request.get("prompt", "")
            file_paths = request.get("file_paths", None)
            stream = request.get("stream", False)
            new_chat = request.get("new_chat", False)
            
            # 使用 StreamingResponse 来处理流式响应
            if stream:
                from fastapi.responses import StreamingResponse
                
                async def generate_stream():
                    async for response in handler.handle_chat_stream(
                        prompt=prompt, 
                        file_paths=file_paths, 
                        stream=True, 
                        new_chat=new_chat
                    ):
                        # 将响应转换成JSON字符串
                        yield json.dumps(response) + "\n"
                
                return StreamingResponse(generate_stream(), media_type="application/json")
            else:
                # 对于非流式响应，收集完整的响应并返回
                responses = []
                async for response in handler.handle_chat_stream(
                    prompt=prompt, 
                    file_paths=file_paths, 
                    stream=False, 
                    new_chat=new_chat
                ):
                    responses.append(response)
                
                # 返回最后一个响应（完整响应）
                if responses:
                    return responses[-1]
                else:
                    return {"status": "error", "message": "未收到响应"}
        
        # 可以添加其他提供商的处理逻辑
        else:
            raise HTTPException(status_code=400, detail=f"不支持的提供商: {provider}")
    
    except Exception as e:
        logger.error(f"对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

@app.post("/tabs/{provider}/screenshot")
async def take_screenshot(provider: str, api_key: str = Depends(get_api_key)):
    """获取指定提供商标签页的截图"""
    async with lock:
        if provider not in user_tabs[api_key]:
            raise HTTPException(status_code=404, detail=f"找不到提供商 {provider} 的标签页")
        
        try:
            # 切换到标签页
            await browser_session.switch_to_tab(user_tabs[api_key][provider]["handle"])
            
            # 获取截图
            screenshot_path = await browser_session.screenshot()
            if not screenshot_path:
                raise HTTPException(status_code=500, detail="截图失败")
            
            return {
                "status": "success",
                "screenshot_path": screenshot_path
            }
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"截图失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005,reload=True)