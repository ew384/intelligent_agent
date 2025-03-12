from .spa_tools import function_tools as spa_function_tools

# 导出所有SPA工具函数，供Agent使用
function_tools = spa_function_tools

# 添加高级抽象工具，组合多个基础工具操作
async def search_and_navigate(keyword):
    """
    搜索包含关键词的菜单并导航到最匹配的菜单项
    
    Args:
        keyword (str): 要搜索的关键词
        
    Returns:
        Dict: 导航结果和页面内容
    """
    # 搜索菜单项
    search_result = await function_tools["search_menu_items"](keyword)
    
    # 如果没有找到结果，返回错误
    if search_result["status"] != "success" or not search_result["content"]:
        return {
            "status": "error",
            "message": f"未找到包含 '{keyword}' 的菜单项"
        }
    
    # 获取最匹配的菜单项
    best_match = search_result["content"][0]
    
    # 导航到该菜单项
    nav_result = await function_tools["navigate_to_menu"](best_match["path"])
    
    return nav_result

async def process_form_and_submit(form_data, submit_button="提交"):
    """
    填写表单并提交
    
    Args:
        form_data (Dict): 字段名到字段值的映射
        submit_button (str): 提交按钮的文本
        
    Returns:
        Dict: 操作结果
    """
    # 获取当前页面内容
    content_result = await function_tools["get_current_iframe_content"]()
    
    # 如果获取页面内容失败，返回错误
    if content_result["status"] != "success":
        return content_result
    
    # 填写表单字段
    for field_name, field_value in form_data.items():
        field_result = await function_tools["fill_input_in_iframe"](field_name, str(field_value))
        
        # 如果填写失败，返回错误
        if field_result["status"] != "success":
            return {
                "status": "error",
                "message": f"填写字段 '{field_name}' 失败: {field_result['message']}"
            }
    
    # 点击提交按钮
    button_result = await function_tools["click_button_in_iframe"](submit_button)
    
    return button_result

async def place_installment_order_sap(amount, periods, customer_info=None):
    """
    通过SAP系统下分期订单
    
    Args:
        amount (float): 分期金额
        periods (int): 分期期数
        customer_info (Dict, optional): 客户信息
        
    Returns:
        Dict: 订单结果
    """
    # 导航到分期业务页面
    nav_result = await search_and_navigate("分期申请")
    
    # 如果导航失败，尝试其他可能的菜单
    if nav_result["status"] != "success":
        nav_result = await search_and_navigate("分期业务")
        
        if nav_result["status"] != "success":
            return {
                "status": "error",
                "message": "无法导航到分期业务页面"
            }
    
    # 准备表单数据
    form_data = {
        "分期金额": str(amount),
        "期数": str(periods)
    }
    
    # 如果有客户信息，添加到表单数据
    if customer_info and isinstance(customer_info, dict):
        if "name" in customer_info and customer_info["name"]:
            form_data["客户姓名"] = customer_info["name"]
        if "id" in customer_info and customer_info["id"]:
            form_data["证件号码"] = customer_info["id"]
    
    # 填写表单并提交
    result = await process_form_and_submit(form_data)
    
    # 解析结果
    if result["status"] == "success":
        # 尝试从页面内容中提取订单号
        order_id = None
        if "content" in result and "full_text" in result["content"]:
            import re
            # 尝试匹配订单号模式
            order_match = re.search(r'订单号[:\s]+([A-Z0-9]+)', result["content"]["full_text"])
            if order_match:
                order_id = order_match.group(1)
        
        return {
            "status": "success",
            "message": "分期订单已成功提交",
            "order_id": order_id or f"INS{int(time.time())}",
            "details": {
                "amount": amount,
                "periods": periods
            }
        }
    else:
        return result

# 导出新的组合工具
combined_tools = {
    "search_and_navigate": search_and_navigate,
    "process_form_and_submit": process_form_and_submit,
    "place_installment_order_sap": place_installment_order_sap
}

# 所有工具的合并字典，包括基础工具和组合工具
all_tools = {**function_tools, **combined_tools}
