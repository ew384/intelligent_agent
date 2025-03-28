import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional

# API基础URL
BASE_URL = "http://localhost:8005"

# 用户API密钥
API_KEYS = {
    "user1": "user1_key",
    "user2": "user2_key"
}

# 存储用户的标签页ID
user_tabs = {
    "user1": [],
    "user2": []
}

# 打印带颜色的文本
def print_colored(user: str, message: str):
    colors = {
        "user1": "\033[92m",  # 绿色
        "user2": "\033[94m",  # 蓝色
        "error": "\033[91m",  # 红色
        "info": "\033[93m",   # 黄色
        "reset": "\033[0m"    # 重置
    }
    
    print(f"{colors[user]}{user}: {message}{colors['reset']}")

# 通用请求方法
async def make_request(user: str, method: str, endpoint: str, json_data: Optional[Dict] = None) -> Dict:
    url = f"{BASE_URL}{endpoint}"
    headers = {"api-key": API_KEYS[user]}
    
    async with aiohttp.ClientSession() as session:
        try:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print_colored("error", f"{user} - {method} {endpoint} 失败: {response.status} - {error_text}")
                        return {"success": False, "error": error_text}
                    return {"success": True, "data": await response.json()}
                    
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=json_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print_colored("error", f"{user} - {method} {endpoint} 失败: {response.status} - {error_text}")
                        return {"success": False, "error": error_text}
                    return {"success": True, "data": await response.json()}
                    
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print_colored("error", f"{user} - {method} {endpoint} 失败: {response.status} - {error_text}")
                        return {"success": False, "error": error_text}
                    return {"success": True, "data": await response.json()}
                    
            else:
                print_colored("error", f"不支持的方法: {method}")
                return {"success": False, "error": f"不支持的方法: {method}"}
                
        except Exception as e:
            print_colored("error", f"{user} - {method} {endpoint} 出错: {str(e)}")
            return {"success": False, "error": str(e)}

# 用户1的测试流程
async def user1_test():
    user = "user1"
    print_colored(user, "开始测试")
    
    # 1. 创建Claude标签页
    print_colored(user, "创建Claude标签页")
    result = await make_request(user, "POST", "/tabs/claude")
    
    if result["success"]:
        tab_id = result["data"]["id"]
        user_tabs[user].append(tab_id)
        print_colored(user, f"创建成功，标签页ID: {tab_id}")
        
        # 2. 等待页面加载
        print_colored(user, "等待页面加载 (5秒)")
        await asyncio.sleep(5)
        
        # 3. 执行输入操作 - 输入提示词
        print_colored(user, "尝试输入提示词")
        input_result = await make_request(user, "POST", f"/tabs/{tab_id}/execute", {
            "action": "type",
            "selector": "textarea[placeholder], [contenteditable=true]",
            "value": "请帮我解释量子力学的基本原理"
        })
        
        if input_result["success"]:
            print_colored(user, "输入提示词成功")
            
            # 4. 执行点击操作 - 发送消息
            print_colored(user, "尝试点击发送按钮")
            await asyncio.sleep(1)
            click_result = await make_request(user, "POST", f"/tabs/{tab_id}/execute", {
                "action": "click",
                "selector": "button[type='submit']"
            })
            
            if click_result["success"]:
                print_colored(user, "点击发送按钮成功")
                
                # 5. 等待回复
                print_colored(user, "等待AI回复 (10秒)")
                await asyncio.sleep(10)
                
                # 6. 获取页面截图
                print_colored(user, "获取页面截图")
                screenshot_result = await make_request(user, "GET", f"/tabs/{tab_id}/screenshot")
                
                if screenshot_result["success"]:
                    print_colored(user, "获取截图成功")
                else:
                    print_colored(user, f"获取截图失败: {screenshot_result.get('error')}")
            else:
                print_colored(user, f"点击发送按钮失败: {click_result.get('error')}")
        else:
            print_colored(user, f"输入提示词失败: {input_result.get('error')}")
    else:
        print_colored(user, f"创建标签页失败: {result.get('error')}")
    
    # 测试结束前不关闭标签页，留给最终清理

# 用户2的测试流程
async def user2_test():
    user = "user2"
    print_colored(user, "开始测试")
    
    # 1. 创建ChatGPT标签页
    print_colored(user, "创建ChatGPT标签页")
    result = await make_request(user, "POST", "/tabs/chatgpt")
    
    if result["success"]:
        tab_id = result["data"]["id"]
        user_tabs[user].append(tab_id)
        print_colored(user, f"创建成功，标签页ID: {tab_id}")
        
        # 2. 等待页面加载
        print_colored(user, "等待页面加载 (5秒)")
        await asyncio.sleep(5)
        
        # 3. 获取页面源码
        print_colored(user, "获取页面HTML源码")
        html_result = await make_request(user, "GET", f"/tabs/{tab_id}/html")
        
        if html_result["success"]:
            html_length = len(html_result["data"]["html"])
            print_colored(user, f"获取HTML源码成功，长度: {html_length} 字符")
            
            # 4. 创建另一个普通标签页
            print_colored(user, "创建普通标签页")
            blank_result = await make_request(user, "POST", "/tabs")
            
            if blank_result["success"]:
                blank_tab_id = blank_result["data"]["id"]
                user_tabs[user].append(blank_tab_id)
                print_colored(user, f"创建普通标签页成功，ID: {blank_tab_id}")
                
                # 5. 导航到百度
                print_colored(user, "将普通标签页导航到百度")
                nav_result = await make_request(user, "POST", f"/tabs/{blank_tab_id}/navigate", {
                    "url": "https://www.baidu.com"
                })
                
                if nav_result["success"]:
                    print_colored(user, f"导航成功，页面标题: {nav_result['data']['title']}")
                    
                    # 6. 等待页面加载
                    await asyncio.sleep(3)
                    
                    # 7. 立即关闭这个标签页
                    print_colored(user, f"关闭百度标签页")
                    close_result = await make_request(user, "DELETE", f"/tabs/{blank_tab_id}")
                    
                    if close_result["success"]:
                        print_colored(user, "关闭标签页成功")
                        user_tabs[user].remove(blank_tab_id)
                    else:
                        print_colored(user, f"关闭标签页失败: {close_result.get('error')}")
                else:
                    print_colored(user, f"导航失败: {nav_result.get('error')}")
            else:
                print_colored(user, f"创建普通标签页失败: {blank_result.get('error')}")
        else:
            print_colored(user, f"获取HTML源码失败: {html_result.get('error')}")
    else:
        print_colored(user, f"创建标签页失败: {result.get('error')}")
    
    # 测试结束前不关闭标签页，留给最终清理

# 获取每个用户的标签页列表
async def list_user_tabs(user: str):
    print_colored(user, "获取标签页列表")
    result = await make_request(user, "GET", "/tabs")
    
    if result["success"]:
        tabs = result["data"]
        print_colored(user, f"找到 {len(tabs)} 个标签页:")
        for tab in tabs:
            print_colored(user, f"  - ID: {tab['id']}, 标题: {tab['title']}, URL: {tab['url']}")
        return tabs
    else:
        print_colored(user, f"获取标签页列表失败: {result.get('error')}")
        return []

# 关闭所有标签页
async def cleanup():
    print_colored("info", "开始清理 - 关闭所有标签页")
    
    for user, key in API_KEYS.items():
        tabs = await list_user_tabs(user)
        
        for tab in tabs:
            tab_id = tab["id"]
            print_colored(user, f"关闭标签页: {tab_id}")
            await make_request(user, "DELETE", f"/tabs/{tab_id}")
            
    print_colored("info", "清理完成")

# 主测试函数
async def run_tests():
    print_colored("info", "开始API测试")
    
    # 并行执行两个用户的测试
    await asyncio.gather(
        user1_test(),
        user2_test()
    )
    
    # 等待一段时间，确保测试完成
    await asyncio.sleep(2)
    
    # 展示每个用户的标签页
    for user in API_KEYS.keys():
        await list_user_tabs(user)
    
    # 清理资源
    print_colored("info", "测试完成，准备清理资源")
    await asyncio.sleep(2)
    await cleanup()

# 执行测试
if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print_colored("info", "测试被手动中断")
    except Exception as e:
        print_colored("error", f"测试出错: {str(e)}")
        
    # 确保清理资源
    try:
        asyncio.run(cleanup())
    except Exception:
        pass
