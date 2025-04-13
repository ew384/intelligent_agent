import requests

# 设置API基础URL
base_url = "http://localhost:8003"  # 假设您的服务运行在本地8003端口

# 创建会话ID
session_id = "test_session_1"

# 测试tax_workflow
def test_tax_workflow():
    # 构建请求URL和数据
    url = f"{base_url}/workflow/tax_workflow/execute"
    data = {
        "action_id": "navigate_to_main"
    }
    params = {
        "session_id": "test_session_1"
    }
    
    # 发送请求
    response = requests.post(url, json=data, params=params)
    
    # 打印结果
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {response.json()}")

# 测试social_security_workflow
def test_social_security_workflow():
    # 构建请求URL和数据
    url = f"{base_url}/workflow/social_security_workflow/execute"
    data = {
        "action_id": "navigate_and_select_person"
    }
    params = {
        "session_id": session_id
    }
    
    # 发送请求
    response = requests.post(url, json=data, params=params)
    
    # 打印结果
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {response.json()}")

# 执行测试
print("测试税务工作流:")
#test_tax_workflow()

print("\n测试社保工作流:")
test_social_security_workflow()
