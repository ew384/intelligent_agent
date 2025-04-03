#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本：验证spa_navigator.integrated_tools中的所有工具函数
"""

import asyncio
import json
import inspect
from typing import Dict, Any, List, Callable, Awaitable, Union
import traceback
import time

# 辅助函数：调用工具函数，自动处理同步和异步情况
async def call_tool(tool_name: str, *args, **kwargs) -> Any:
    """
    调用工具函数，自动判断是同步还是异步函数
    
    Args:
        tool_name: 工具函数名称
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        调用函数的结果
    """
    if tool_name not in all_tools:
        raise ValueError(f"工具函数 '{tool_name}' 不存在")
        
    func = all_tools[tool_name]
    
    # 判断是否为异步函数
    if asyncio.iscoroutinefunction(func) or (inspect.isgeneratorfunction(func) and 
                                            "async" in str(func)):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)

# 导入需要测试的工具
from spa_navigator.integrated_tools import all_tools

# 颜色常量，用于美化输出
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """打印带格式的标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.END}\n")

def print_subheader(text: str):
    """打印带格式的子标题"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'-' * 60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'-' * 60}{Colors.END}")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.END}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.FAIL}✗ {text}{Colors.END}")

def print_result(result: Dict[str, Any]):
    """格式化打印结果"""
    status = result.get("status", "unknown")
    if status == "success":
        print(f"{Colors.GREEN}状态: 成功{Colors.END}")
    else:
        print(f"{Colors.FAIL}状态: {status}{Colors.END}")
        
    if "message" in result:
        print(f"消息: {result['message']}")
        
    if "content" in result:
        content = result["content"]
        if isinstance(content, dict) or isinstance(content, list):
            print("内容:")
            try:
                formatted_content = json.dumps(content, ensure_ascii=False, indent=2)
                print(f"{Colors.BLUE}{formatted_content}{Colors.END}")
            except:
                print(f"{Colors.BLUE}{content}{Colors.END}")
        else:
            print(f"内容: {Colors.BLUE}{content}{Colors.END}")

# 为每个工具创建测试用例
async def test_get_menu_structure():
    """测试获取菜单结构"""
    print_subheader("测试: get_menu_structure")
    try:
        result = await call_tool("get_menu_structure")
        print_result(result)
        return result["status"] == "success"
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_search_menu_items():
    """测试搜索菜单项"""
    print_subheader("测试: search_menu_items")
    try:
        # 使用几个不同的关键词进行测试
        keywords = ["分期", "账单", "还款"]
        results = []
        
        for keyword in keywords:
            print(f"\n搜索关键词: {Colors.BOLD}{keyword}{Colors.END}")
            result = await call_tool("search_menu_items", keyword)
            print_result(result)
            results.append(result["status"] == "success")
            
        return all(results)
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_navigate_to_menu():
    """测试菜单导航"""
    print_subheader("测试: navigate_to_menu")
    try:
        # 先获取可用菜单
        menu_result = await call_tool("get_menu_structure")
        
        if menu_result["status"] != "success" or not menu_result["content"]:
            print_warning("无法获取菜单结构，使用默认菜单路径进行测试")
            menu_paths = ["分期业务", "账户信息", "账单查询"]
        else:
            # 从返回的菜单结构中提取一些路径
            menu_structure = menu_result["content"]
            menu_paths = []
            for level1 in list(menu_structure.keys())[:2]:  # 取前两个一级菜单
                menu_paths.append(level1)
                submenu = menu_structure[level1].get("submenus", {})
                if submenu:
                    level2 = list(submenu.keys())[0]  # 取第一个二级菜单
                    menu_paths.append(f"{level1} > {level2}")
        
        results = []
        for path in menu_paths:
            print(f"\n导航路径: {Colors.BOLD}{path}{Colors.END}")
            result = await call_tool("navigate_to_menu", path)
            print_result(result)
            results.append(result["status"] == "success")
            # 暂停一下，让页面有时间加载
            await asyncio.sleep(1)
            
        return any(results)  # 至少有一个成功就算通过
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_get_current_iframe_content():
    """测试获取当前iframe内容"""
    print_subheader("测试: get_current_iframe_content")
    try:
        # 先导航到一个页面
        await call_tool("navigate_to_menu", "分期业务")
        await asyncio.sleep(1)  # 等待页面加载
        
        result = await call_tool("get_current_iframe_content")
        print_result(result)
        return result["status"] == "success"
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_click_button_and_fill_input():
    """测试按钮点击和表单填写"""
    print_subheader("测试: click_button_in_iframe 和 fill_input_in_iframe")
    try:
        # 导航到分期申请页面
        await call_tool("navigate_to_menu", "分期业务 > 分期申请")
        await asyncio.sleep(1)  # 等待页面加载
        
        # 获取页面内容，查看有哪些表单字段和按钮
        content_result = await call_tool("get_current_iframe_content")
        
        if content_result["status"] != "success":
            print_warning("无法获取页面内容，使用默认字段和按钮进行测试")
            form_fields = [{"name": "金额", "label": "金额"}, {"name": "期数", "label": "期数"}]
            buttons = ["提交", "计算", "重置"]
        else:
            form_fields = content_result["content"].get("form_fields", [])
            buttons = content_result["content"].get("buttons", [])
        
        # 填写表单字段
        fill_results = []
        if form_fields:
            for field in form_fields[:2]:  # 测试前两个字段
                field_name = field.get("label") or field.get("name")
                if field_name:
                    print(f"\n填写字段: {Colors.BOLD}{field_name}{Colors.END}")
                    value = "10000" if "金额" in field_name else "12" if "期数" in field_name else "测试值"
                    result = await call_tool("fill_input_in_iframe", field_name, value)
                    print_result(result)
                    fill_results.append(result["status"] == "success")
        
        # 点击按钮
        button_results = []
        if buttons:
            # 优先测试非提交类按钮，避免表单提交
            test_buttons = [b for b in buttons if b not in ["提交", "确认"]]
            if not test_buttons:
                test_buttons = buttons[:1]  # 如果没有非提交按钮，就测试第一个
                
            for button_text in test_buttons:
                print(f"\n点击按钮: {Colors.BOLD}{button_text}{Colors.END}")
                result = await call_tool("click_button_in_iframe", button_text)
                print_result(result)
                button_results.append(result["status"] == "success")
        
        return (not fill_results or any(fill_results)) and (not button_results or any(button_results))
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_calculate_installment_plan():
    """测试分期计划计算"""
    print_subheader("测试: calculate_installment_plan")
    try:
        # 测试不同金额和期数
        test_cases = [
            {"amount": 5000, "periods": 6},
            {"amount": 10000, "periods": 12}
        ]
        
        results = []
        for case in test_cases:
            print(f"\n计算分期: {Colors.BOLD}金额={case['amount']}, 期数={case['periods']}{Colors.END}")
            result = await call_tool("calculate_installment_plan", case["amount"], case["periods"])
            print_result(result)
            results.append(result["status"] == "success")
            
        return all(results)
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_query_customer_info():
    """测试客户信息查询"""
    print_subheader("测试: query_customer_info")
    try:
        # 测试几个不同的客户ID
        customer_ids = ["1234567890", "9876543210"]
        
        results = []
        for customer_id in customer_ids:
            print(f"\n查询客户: {Colors.BOLD}ID={customer_id}{Colors.END}")
            result = await call_tool("query_customer_info", customer_id)
            print_result(result)
            results.append(result["status"] == "success")
            
        return all(results)
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_query_installment_offers():
    """测试分期优惠查询"""
    print_subheader("测试: query_installment_offers")
    try:
        # 测试几个不同的客户ID
        customer_ids = ["1234567890", "9876543210"]
        
        results = []
        for customer_id in customer_ids:
            print(f"\n查询优惠: {Colors.BOLD}客户ID={customer_id}{Colors.END}")
            result = await call_tool("query_installment_offers", customer_id)
            print_result(result)
            results.append(result["status"] == "success")
            
        return all(results)
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def test_place_installment_order():
    """测试下分期订单"""
    print_subheader("测试: place_installment_order_sap")
    try:
        # 准备测试数据
        test_case = {
            "amount": 8000,
            "periods": 12,
            "customer_info": {
                "name": "测试用户",
                "id": "1234567890"
            }
        }
        
        print(f"\n下单参数: {Colors.BOLD}金额={test_case['amount']}, 期数={test_case['periods']}{Colors.END}")
        result = await call_tool("place_installment_order_sap", 
                                test_case["amount"], 
                                test_case["periods"], 
                                test_case["customer_info"])
        print_result(result)
        return result["status"] == "success"
    except Exception as e:
        print_error(f"发生错误: {str(e)}")
        traceback.print_exc()
        return False

"][0]["path"]
        
        # 步骤2: 导航到分期页面
        print(f"{Colors.BLUE}步骤2: 导航到'{menu_path}'页面{Colors.END}")
        nav_result = await all_tools["navigate_to_menu"](menu_path)
        if nav_result["status"] != "success":
            print_error(f"无法导航到'{menu_path}'")
            return False
        await asyncio.sleep(1)  # 等待页面加载
        
        # 步骤3: 获取页面内容
        print(f"{Colors.BLUE}步骤3: 获取页面内容{Colors.END}")
        content_result = await all_tools["get_current_iframe_content"]()
        if content_result["status"] != "success":
            print_error("无法获取页面内容")
            return False
            
        # 步骤4: 填写分期表单
        print(f"{Colors.BLUE}步骤4: 填写分期表单{Colors.END}")
        amount = 6000
        periods = 12
        
        # 尝试找到金额和期数字段
        form_fields = content_result["content"].get("form_fields", [])
        amount_field = None
        period_field = None
        
        for field in form_fields:
            field_name = field.get("label") or field.get("name", "")
            if any(keyword in field_name.lower() for keyword in ["金额", "金", "额", "amount"]):
                amount_field = field_name
            elif any(keyword in field_name.lower() for keyword in ["期数", "期", "分期", "months", "period"]):
                period_field = field_name
                
        if amount_field:
            print(f"填写金额字段: {amount_field} = {amount}")
            await all_tools["fill_input_in_iframe"](amount_field, str(amount))
        else:
            print_warning("未找到金额字段，尝试填写'金额'")
            await all_tools["fill_input_in_iframe"]("金额", str(amount))
            
        if period_field:
            print(f"填写期数字段: {period_field} = {periods}")
            await all_tools["fill_input_in_iframe"](period_field, str(periods))
        else:
            print_warning("未找到期数字段，尝试填写'期数'")
            await all_tools["fill_input_in_iframe"]("期数", str(periods))
        
        # 步骤5: 计算分期计划
        print(f"{Colors.BLUE}步骤5: 计算分期计划{Colors.END}")
        plan_result = await all_tools["calculate_installment_plan"](amount, periods)
        if plan_result["status"] != "success":
            print_error("计算分期计划失败")
            return False
        
        # 获取计算结果
        total_amount = plan_result["content"]["total_amount"]
        monthly_payment = plan_result["content"]["monthly_payment"]
        fee_amount = plan_result["content"]["fee_amount"]
        
        print(f"分期总金额: {Colors.GREEN}{total_amount}元{Colors.END}")
        print(f"月供: {Colors.GREEN}{monthly_payment}元{Colors.END}")
        print(f"手续费: {Colors.GREEN}{fee_amount}元{Colors.END}")
        
        # 步骤6: 提交订单 (模拟)
        print(f"{Colors.BLUE}步骤6: 模拟提交订单{Colors.END}")
        # 这里不实际点击提交按钮，避免产生真实订单，而是使用place_installment_order_sap模拟
        customer_info = {"name": "测试用户", "id": "1234567890"}
        order_result = await all_tools["place_installment_order_sap"](amount, periods, customer_info)
        
        if order_result["status"] == "success":
            print_success(f"组合流程测试成功! 订单号: {order_result.get('order_id', 'N/A')}")
            return True
        else:
            print_warning("组合流程部分成功，提交订单失败")
            return False
        
    except Exception as e:
        print_error(f"组合流程测试发生错误: {str(e)}")
        traceback.print_exc()
        return False

async def run_tests():
    """运行所有测试"""
    print_header("中信银行信用卡分期工具功能测试")
    
    # 打印工具列表
    print("可用工具列表:")
    for i, tool_name in enumerate(all_tools.keys()):
        is_async = asyncio.iscoroutinefunction(all_tools[tool_name])
        async_str = "异步" if is_async else "同步"
        print(f"{i+1}. {tool_name} ({async_str}函数)")
    print("\n")
    
    # 定义测试和描述
    tests = [
        (test_get_menu_structure, "获取菜单结构"),
        (test_search_menu_items, "搜索菜单项"),
        (test_navigate_to_menu, "导航到指定菜单"),
        (test_get_current_iframe_content, "获取当前页面内容"),
        (test_click_button_and_fill_input, "按钮点击和表单填写"),
        (test_calculate_installment_plan, "计算分期计划"),
        (test_query_customer_info, "查询客户信息"),
        (test_query_installment_offers, "查询分期优惠"),
        (test_place_installment_order, "提交分期订单"),
        (test_combined_flow, "组合流程测试")
    ]
    
    # 统计结果
    results = {}
    start_time = time.time()
    
    # 运行测试
    for test_func, description in tests:
        print_header(f"测试: {description}")
        try:
            success = await test_func()
            results[description] = success
        except Exception as e:
            print_error(f"测试执行出错: {str(e)}")
            traceback.print_exc()
            results[description] = False
        
        # 在测试之间暂停，给系统一些恢复时间
        await asyncio.sleep(1)
    
    # 打印测试摘要
    end_time = time.time()
    duration = end_time - start_time
    
    print_header("测试结果摘要")
    print(f"总运行时间: {duration:.2f} 秒")
    print(f"运行测试: {len(tests)}")
    passed = sum(1 for success in results.values() if success)
    print(f"通过测试: {passed}")
    print(f"失败测试: {len(tests) - passed}")
    
    # 打印详细结果
    print("\n详细结果:")
    for description, success in results.items():
        if success:
            print(f"{Colors.GREEN}✓ {description} - 通过{Colors.END}")
        else:
            print(f"{Colors.FAIL}✗ {description} - 失败{Colors.END}")
    
    return all(results.values())

if __name__ == "__main__":
    try:
        import sys
        
        # 检查是否有命令行参数
        if len(sys.argv) > 1:
            # 运行单个测试
            test_name = sys.argv[1]
            print_header(f"运行单个测试: {test_name}")
            
            # 找到匹配的测试函数
            test_func = None
            for func, desc in [(test_get_menu_structure, "get_menu_structure"),
                             (test_search_menu_items, "search_menu_items"),
                             (test_navigate_to_menu, "navigate_to_menu"),
                             (test_get_current_iframe_content, "get_current_iframe_content"),
                             (test_click_button_and_fill_input, "click_button_and_fill_input"),
                             (test_calculate_installment_plan, "calculate_installment_plan"),
                             (test_query_customer_info, "query_customer_info"),
                             (test_query_installment_offers, "query_installment_offers"),
                             (test_place_installment_order, "place_installment_order"),
                             (test_combined_flow, "combined_flow")]:
                if test_name == desc:
                    test_func = func
                    break
            
            if test_func:
                result = asyncio.run(test_func())
                print(f"\n测试结果: {'成功' if result else '失败'}")
            else:
                print_error(f"找不到测试: {test_name}")
                print("可用的测试:")
                print("- get_menu_structure")
                print("- search_menu_items")
                print("- navigate_to_menu")
                print("- get_current_iframe_content")
                print("- click_button_and_fill_input")
                print("- calculate_installment_plan")
                print("- query_customer_info")
                print("- query_installment_offers")
                print("- place_installment_order")
                print("- combined_flow")
        else:
            # 运行所有测试
            asyncio.run(run_tests())
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
    except Exception as e:
        print_error(f"测试执行过程中发生未处理异常: {str(e)}")
        traceback.print_exc()
