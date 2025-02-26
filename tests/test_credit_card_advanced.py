# simple_test.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 简单启动浏览器
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 访问目标网站
        await page.goto("https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html")
        
        # 等待用户手动操作
        print("请在浏览器中手动操作，完成后按回车键...")
        input()
        
        # 保存cookies
        cookies = await page.context.cookies()
        import json
        with open("citic_cookies.json", "w") as f:
            json.dump(cookies, f)
        print("已保存cookies到citic_cookies.json")
        
        # 关闭浏览器
        await browser.close()

asyncio.run(main())
