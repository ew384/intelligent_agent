from fastapi import FastAPI
import sys
import os
from pathlib import Path
# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))
from .routes.api import router as api_router
from .tools.browser.browser_manager import BrowserManager

app = FastAPI(title="Tool Service")

# 初始化全局服务
browser_manager = BrowserManager()

# 注册路由
app.include_router(api_router, prefix="/tools")

@app.on_event("startup")
async def startup_event():
    # 服务启动时的初始化
    # 检查ChromeDriver是否已存在
    chromedriver_path = "/usr/local/bin/chromedriver"
    if os.path.exists(chromedriver_path) and os.access(chromedriver_path, os.X_OK):
        print(f"ChromeDriver已存在于{chromedriver_path}，跳过下载")
    else:
        # 下载匹配的ChromeDriver
        try:
            browser_manager.download_chromedriver()
        except Exception as e:
            print(f"警告: ChromeDriver下载失败: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    # 服务关闭时的清理
    browser_manager.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)

