from .spa_tools import function_tools as spa_function_tools

# 导出所有SPA工具函数，供Agent使用
function_tools = spa_function_tools

# 添加高级抽象工具，组合多个基础工具操作
def search_and_navigate(keyword):
    """
    搜索包含关键词的菜单并导航到最匹配的菜单项
    
    Args:
        keyword (str): 要搜索的关键词
        
    Returns:
        Dict: 导航结果和页面内容
    """
    # 搜索菜单项
    search_result = function_tools["search_menu_items"](keyword)
    
    # 如果没有找到结果，返回错误
    if search_result["status"] != "success" or not search_result["content"]:
        return {
            "status": "error",
            "message": f"未找到包含 '{keyword}' 的菜单项"
        }
    
    # 获取匹配的菜单项并按相关性排序
    matches = search_result["content"]
    
    # 使用简单的文本相似度来确定最佳匹配
    best_match = None
    best_score = -1
    
    for match in matches:
        menu_name = match["menu_name"]
        
        # 计算简单相似度分数 - 精确匹配获得最高分
        score = 0
        
        # 精确匹配得分最高
        if menu_name.lower() == keyword.lower():
            score = 100
        # 开头匹配得分次之
        elif menu_name.lower().startswith(keyword.lower()):
            score = 80
        # 包含关键词得分再次
        elif keyword.lower() in menu_name.lower():
            score = 60
        # 关键词的部分匹配
        else:
            # 计算关键词中有多少字符存在于菜单名称中
            keyword_chars = set(keyword.lower())
            menu_chars = set(menu_name.lower())
            common_chars = keyword_chars.intersection(menu_chars)
            
            if common_chars:
                char_match_ratio = len(common_chars) / len(keyword_chars)
                score = 40 * char_match_ratio
        
        # 路径较短的选项优先（更简单的导航路径）
        path_parts = match["path"].split(" > ")
        path_penalty = len(path_parts) * 5  # 每层级减少5分
        score -= path_penalty
        
        # 更新最佳匹配
        if score > best_score:
            best_score = score
            best_match = match
    
    # 如果没有找到足够好的匹配，使用第一个结果
    if best_match is None and matches:
        best_match = matches[0]
    
    # 如果找到了匹配，导航到该菜单项
    if best_match:
        print(f"最佳匹配: {best_match['menu_name']}，分数: {best_score}")
        nav_result = function_tools["navigate_to_menu"](best_match["path"])
        return nav_result
    else:
        return {
            "status": "error",
            "message": f"未找到合适的匹配菜单项: '{keyword}'"
        }

def process_form_and_submit(form_data, submit_button="提交"):
    """
    填写表单并提交
    
    Args:
        form_data (Dict): 字段名到字段值的映射
        submit_button (str): 提交按钮的文本
        
    Returns:
        Dict: 操作结果
    """
    # 获取当前页面内容
    content_result = function_tools["get_current_iframe_content"]()
    
    # 如果获取页面内容失败，返回错误
    if content_result["status"] != "success":
        return content_result
    
    # 填写表单字段
    for field_name, field_value in form_data.items():
        field_result = function_tools["fill_input_in_iframe"](field_name, str(field_value))
        
        # 如果填写失败，返回错误
        if field_result["status"] != "success":
            return {
                "status": "error",
                "message": f"填写字段 '{field_name}' 失败: {field_result['message']}"
            }
    
    # 点击提交按钮
    button_result = function_tools["click_button_in_iframe"](submit_button)
    
    return button_result


def place_installment_order_sap(amount, periods, customer_info=None):
    """
    通过SAP系统下分期订单

    Args:
        amount (float): 分期金额
        periods (int): 分期期数
        customer_info (Dict, optional): 客户信息

    Returns:
        Dict: 订单结果
    """
    # 导航到分期业务下单页面
    nav_result = search_and_navigate("分期业务下单")

    # 如果导航失败，尝试其他可能的菜单
    if nav_result["status"] != "success":
        # 尝试导航到"分期业务"菜单
        nav_result = search_and_navigate("分期业务")

        if nav_result["status"] != "success":
            return {
                "status": "error",
                "message": "无法导航到分期业务下单页面"
            }

    # 获取当前页面内容
    page_content = get_current_iframe_content()
    if page_content["status"] != "success":
        return {
            "status": "error",
            "message": "无法获取页面内容"
        }

    # 查询各种分期资格
    qualification_results = {}

    # 1. 查询合并分期资格
    try:
        combined_result = click_button_in_iframe("资格查询")
        qualification_results["合并分期"] = combined_result["status"] == "success"
    except Exception as e:
        print(f"查询合并分期资格失败: {str(e)}")
        qualification_results["合并分期"] = False

    # 2. 查询单笔分期资格
    try:
        single_result = click_button_in_iframe("资格查询")
        qualification_results["单笔分期"] = single_result["status"] == "success"
    except Exception as e:
        print(f"查询单笔分期资格失败: {str(e)}")
        qualification_results["单笔分期"] = False

    # 3. 查询先息后本合并分期资格
    try:
        interest_first_result = click_button_in_iframe("资格查询")
        qualification_results["先息后本合并分期"] = interest_first_result["status"] == "success"
    except Exception as e:
        print(f"查询先息后本合并分期资格失败: {str(e)}")
        qualification_results["先息后本合并分期"] = False

    # 4. 查询家装分期资格
    try:
        home_improvement_result = click_button_in_iframe("资格查询")
        qualification_results["家装分期"] = home_improvement_result["status"] == "success"
    except Exception as e:
        print(f"查询家装分期资格失败: {str(e)}")
        qualification_results["家装分期"] = False

    # 填写分期金额和计算分期方案
    try:
        # 填写分期金额
        amount_result = fill_input_in_iframe("请输入分期金额", str(amount))
        if amount_result["status"] != "success":
            return {
                "status": "error",
                "message": f"填写分期金额失败: {amount_result['message']}"
            }

        # 填写营销折扣（默认为1）
        discount_result = fill_input_in_iframe("营销折扣", "1")

        # 填写抵扣金额（默认为0）
        deduction_result = fill_input_in_iframe("抵扣金额", "0")

        # 点击计算按钮
        calc_result = click_button_in_iframe("计算")
        if calc_result["status"] != "success":
            return {
                "status": "error",
                "message": f"计算分期方案失败: {calc_result['message']}"
            }

        # 获取计算结果页面内容
        calc_page_content = get_current_iframe_content()

        # 处理计算结果
        calculation_result = {}
        if calc_page_content["status"] == "success" and "content" in calc_page_content:
            content = calc_page_content["content"]

            # 尝试从表格或页面内容中提取关键信息
            if "tables" in content and content["tables"]:
                calculation_result["tables"] = content["tables"]

            if "full_text" in content:
                calculation_result["full_text"] = content["full_text"]

        # 选择分期期数（如果有期数选择界面）
        try:
            # 尝试从页面中找到期数选择
            period_select_result = None
            for period_str in [str(periods), f"{periods}期"]:
                try:
                    period_select_result = click_button_in_iframe(period_str)
                    if period_select_result["status"] == "success":
                        break
                except:
                    continue

            if period_select_result is None or period_select_result["status"] != "success":
                # 如果无法直接选择期数，尝试填写期数输入框
                fill_input_in_iframe("期数", str(periods))
        except Exception as e:
            print(f"选择分期期数失败: {str(e)}")
            # 继续处理，不中断流程

        # 提交订单
        submit_result = click_button_in_iframe("提交")

        # 获取订单结果
        if submit_result["status"] == "success":
            # 提取订单号
            order_id = None
            if "content" in submit_result and "full_text" in submit_result["content"]:
                import re
                # 尝试匹配订单号模式
                order_match = re.search(r'订单号[:\s]+([A-Z0-9]+)', submit_result["content"]["full_text"])
                if order_match:
                    order_id = order_match.group(1)

            return {
                "status": "success",
                "message": "分期订单已成功提交",
                "order_id": order_id or f"INS{int(time.time())}",
                "qualification_results": qualification_results,
                "calculation_result": calculation_result,
                "details": {
                    "amount": amount,
                    "periods": periods
                }
            }
        else:
            # 如果提交失败，返回计算结果和资格查询结果
            return {
                "status": "partial",
                "message": "分期方案已计算，但订单提交失败",
                "qualification_results": qualification_results,
                "calculation_result": calculation_result,
                "details": {
                    "amount": amount,
                    "periods": periods
                }
            }

    except Exception as e:
        # 捕获所有异常，确保函数不崩溃
        error_msg = f"分期订单处理过程中发生错误: {str(e)}"
        print(error_msg)

        # 即使发生错误，也尽量返回已获取的资格查询结果
        return {
            "status": "error",
            "message": error_msg,
            "qualification_results": qualification_results,
            "details": {
                "amount": amount,
                "periods": periods
            }
        }

def query_historical_bills():
    """
    查询信用卡历史账单

    导航至"账单明细->历史账单"页面，获取并格式化历史账单信息

    Returns:
        Dict: 包含历史账单信息的结果
    """
    try:
        # 首先尝试直接导航到"历史账单"页面
        nav_result = search_and_navigate("历史账单")

        # 如果直接导航失败，尝试先导航到"账单明细"，然后找"历史账单"
        if nav_result["status"] != "success":
            # 导航到账单明细页面
            nav_result = search_and_navigate("账单明细")

            if nav_result["status"] != "success":
                return {
                    "status": "error",
                    "message": "无法导航到账单明细页面"
                }

            # 尝试在账单明细页面中点击"历史账单"链接或按钮
            try:
                click_result = click_link_in_iframe("历史账单")
                if click_result["status"] != "success":
                    # 如果点击链接失败，尝试点击按钮
                    click_result = click_button_in_iframe("历史账单")
                    if click_result["status"] != "success":
                        return {
                            "status": "error",
                            "message": "无法在账单明细页面中找到历史账单选项"
                        }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"点击历史账单时出错: {str(e)}"
                }

        # 获取历史账单页面内容
        content_result = get_current_iframe_content()
        if content_result["status"] != "success":
            return {
                "status": "error",
                "message": "无法获取历史账单页面内容"
            }

        # 提取页面内容
        content = content_result["content"]

        # 准备返回结果
        result = {
            "status": "success",
            "message": "成功获取历史账单信息",
            "raw_content": content,
            "formatted_output": ""
        }

        # 格式化表格数据
        if "tables" in content and content["tables"]:
            formatted_tables = []

            for table_idx, table in enumerate(content["tables"]):
                if not table:  # 跳过空表格
                    continue

                # 为每个表格创建格式化输出
                formatted_table = f"表格 {table_idx + 1}:\n\n"

                # 获取表格的最大列宽
                col_widths = []
                for row in table:
                    # 确保所有行都有足够的列
                    while len(col_widths) < len(row):
                        col_widths.append(0)

                    # 更新列宽
                    for i, cell in enumerate(row):
                        if i < len(col_widths):
                            col_widths[i] = max(col_widths[i], len(str(cell)) + 2)

                # 创建表头分隔线
                header_sep = "+"
                for width in col_widths:
                    header_sep += "-" * width + "+"

                # 添加表格
                formatted_table += header_sep + "\n"

                # 添加每一行
                for row_idx, row in enumerate(table):
                    row_str = "|"
                    for i, cell in enumerate(row):
                        if i < len(col_widths):
                            cell_str = str(cell)
                            padding = col_widths[i] - len(cell_str)
                            row_str += " " + cell_str + " " * (padding - 1) + "|"

                    formatted_table += row_str + "\n"

                    # 在表头后添加分隔线
                    if row_idx == 0:
                        formatted_table += header_sep + "\n"

                # 添加表尾
                formatted_table += header_sep + "\n\n"
                formatted_tables.append(formatted_table)

            # 将所有表格合并为一个字符串
            result["formatted_output"] = "历史账单信息:\n\n" + "\n".join(formatted_tables)
        else:
            # 如果没有表格，则展示页面基本信息
            result["formatted_output"] = f"""
历史账单信息:

页面标题: {content.get('title', '无标题')}

页面内容概要:
{content.get('summary', '无内容概要')}

页面上的按钮:
{', '.join(content.get('buttons', ['无按钮'])) if content.get('buttons') else '无按钮'}

页面上的链接:
{', '.join(content.get('links', ['无链接'])) if content.get('links') else '无链接'}
"""

        # 添加原始的表格数据
        result["tables"] = content.get("tables", [])

        return result

    except Exception as e:
        error_msg = f"查询历史账单时发生错误: {str(e)}"
        print(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }
# 导出新的组合工具
combined_tools = {
    "search_and_navigate": search_and_navigate,
    "process_form_and_submit": process_form_and_submit,
    "place_installment_order_sap": place_installment_order_sap,
    "query_historical_bills":query_historical_bills
}

# 所有工具的合并字典，包括基础工具和组合工具
all_tools = {**function_tools, **combined_tools}
