# test_services.py (修改版)
import asyncio
import httpx

async def check_service(name, url, expected_status=None):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
            status = response.status_code
            success = expected_status is None or status == expected_status
            result = "✓" if success else "✗"
            print(f"{result} {name} 可访问: {status}")
            return True
    except Exception as e:
        print(f"✗ {name} 不可访问: {str(e)}")
        return False

async def main():
    services = [
        ("API网关 (任务)", "http://localhost:8000/tasks", 405),  # POST需要请求体，所以GET会返回405
        ("API网关 (聊天)", "http://localhost:8000/chat", 405),   # 同上
        ("Orchestrator", "http://localhost:8001/tasks", 405),
        ("Scenario", "http://localhost:8002/", 404),
        ("Tool", "http://localhost:8003/", 200)
    ]
    
    for name, url, expected_status in services:
        await check_service(name, url, expected_status)

if __name__ == "__main__":
    asyncio.run(main())

