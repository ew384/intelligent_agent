# test_api_direct.py
import httpx
import asyncio
import argparse
import json

async def test_api(url, data=None, method="GET"):
    """直接测试API端点"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url)
            else:  # POST
                response = await client.post(url, json=data or {})
            
            print(f"状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            try:
                json_response = response.json()
                print(f"格式化的JSON响应:\n{json.dumps(json_response, indent=2, ensure_ascii=False)}")
            except:
                pass
                
        except Exception as e:
            print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试API端点")
    parser.add_argument("--url", required=True, help="API端点URL")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP方法")
    parser.add_argument("--data", help="POST数据 (JSON格式)")
    
    args = parser.parse_args()
    
    # 解析JSON数据
    data = json.loads(args.data) if args.data else None
    
    asyncio.run(test_api(args.url, data, args.method))
