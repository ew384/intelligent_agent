# test_playwright_basic.py - 修正版
import asyncio
from pathlib import Path

async def main():
    from playwright.async_api import async_playwright
    
    print("开始测试基本的 Playwright 功能...")
    
    # 创建用户数据目录
    user_data_dir = Path("./user_data_test").absolute()
    user_data_dir.mkdir(exist_ok=True)
    print(f"用户数据目录: {user_data_dir}")
    
    async with async_playwright() as p:
        # 使用 launch_persistent_context 替代 launch
        print("启动带有持久化上下文的浏览器...")
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=[
                '--no-sandbox'
            ]
        )
        
        # 直接从上下文创建页面
        print("创建页面...")
        page = await browser_context.new_page()
        
        # 访问网站
        print("访问测试网站...")
        await page.goto("https://example.com")
        
        # 等待用户手动检查
        print("浏览器已打开，请检查是否正常运行。完成后按回车键...")
        input()
        
        # 保存cookies
        cookies = await browser_context.cookies()
        cookies_dir = Path("./cookies_test")
        cookies_dir.mkdir(exist_ok=True)
        
        import json
        with open(cookies_dir / "test_cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"已保存cookies到: {cookies_dir / 'test_cookies.json'}")
        
        # 关闭浏览器
        print("关闭浏览器...")
        await browser_context.close()
        
    print("测试完成!")

if __name__ == "__main__":
    asyncio.run(main())
