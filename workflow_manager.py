#!/usr/bin/env python3
"""
工作流管理工具 - 用于创建、验证和测试工作流JSON文件
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
import re
import requests
from typing import Dict, List, Any, Optional

# 默认目录
DEFAULT_WORKFLOWS_DIR = "workflows"

# 工作流JSON模板
WORKFLOW_TEMPLATE = {
    "id": "",
    "name": "",
    "description": "",
    "keywords": [],
    "version": "1.0",
    "actions": [
        {
            "id": "default_action",
            "name": "默认操作",
            "description": "默认操作描述",
            "steps": [
                {
                    "id": "step_1",
                    "action": "highlight_elements",
                    "parameters": {
                        "viewport_expansion": 500
                    },
                    "description": "高亮页面元素"
                },
                {
                    "id": "step_2",
                    "action": "done",
                    "parameters": {
                        "success": true,
                        "text": "操作完成"
                    },
                    "description": "完成操作"
                }
            ]
        }
    ]
}

def create_new_workflow(args):
    """创建新的工作流JSON文件"""
    workflow_dir = Path(args.dir)
    if not workflow_dir.exists():
        workflow_dir.mkdir(parents=True)
        print(f"创建工作流目录: {workflow_dir}")
    
    # 生成工作流ID
    workflow_id = args.id or f"workflow_{uuid.uuid4().hex[:8]}"
    
    # 创建工作流JSON
    workflow = WORKFLOW_TEMPLATE.copy()
    workflow["id"] = workflow_id
    workflow["name"] = args.name
    workflow["description"] = args.description
    workflow["keywords"] = args.keywords.split(",") if args.keywords else []
    
    # 生成文件路径
    file_path = workflow_dir / f"{workflow_id}.json"
    
    # 检查文件是否已存在
    if file_path.exists() and not args.force:
        print(f"错误: 工作流文件 {file_path} 已存在. 使用 --force 选项覆盖")
        return
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)
    
    print(f"成功创建工作流: {file_path}")
    print(f"工作流ID: {workflow_id}")
    print(f"工作流名称: {workflow['name']}")

def validate_workflow(args):
    """验证工作流JSON文件格式"""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误: 工作流文件 {file_path} 不存在")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # 检查必要字段
        required_fields = ["id", "name", "description", "keywords", "actions"]
        missing_fields = [field for field in required_fields if field not in workflow]
        
        if missing_fields:
            print(f"错误: 工作流缺少必要字段: {', '.join(missing_fields)}")
            return
        
        # 检查操作
        if not workflow["actions"]:
            print("警告: 工作流没有定义任何操作")
        
        # 检查每个操作的步骤
        for i, action in enumerate(workflow["actions"]):
            if "id" not in action:
                print(f"错误: 操作 #{i+1} 缺少ID")
            if "steps" not in action or not action["steps"]:
                print(f"警告: 操作 '{action.get('id', f'#{i+1}')}' 没有定义任何步骤")
            
            # 检查步骤
            step_ids = set()
            for j, step in enumerate(action.get("steps", [])):
                if "id" not in step:
                    print(f"警告: 操作 '{action.get('id', f'#{i+1}')}' 的步骤 #{j+1} 缺少ID")
                elif step["id"] in step_ids:
                    print(f"错误: 操作 '{action.get('id', f'#{i+1}')}' 有重复的步骤ID: {step['id']}")
                else:
                    step_ids.add(step["id"])
                
                if "action" not in step:
                    print(f"错误: 操作 '{action.get('id', f'#{i+1}')}' 的步骤 '{step.get('id', f'#{j+1}')}' 缺少action")
        
        # 检查工作流ID与文件名是否匹配
        expected_filename = f"{workflow['id']}.json"
        if file_path.name != expected_filename:
            print(f"警告: 文件名 ({file_path.name}) 与工作流ID不匹配, 建议重命名为 {expected_filename}")
        
        print(f"验证完成: 工作流 '{workflow.get('name', file_path.name)}' 格式有效")
        print(f"工作流ID: {workflow.get('id', 'unknown')}")
        print(f"包含 {len(workflow.get('actions', []))} 个操作")
        for action in workflow.get("actions", []):
            print(f"  - 操作: {action.get('id', 'unknown')}, 步骤数: {len(action.get('steps', []))}")
        
    except json.JSONDecodeError as e:
        print(f"错误: 工作流文件不是有效的JSON: {e}")
    except Exception as e:
        print(f"错误: 验证工作流时出现未知错误: {e}")

def list_workflows(args):
    """列出所有工作流"""
    workflow_dir = Path(args.dir)
    if not workflow_dir.exists():
        print(f"工作流目录 {workflow_dir} 不存在")
        return
    
    workflow_files = list(workflow_dir.glob("*.json"))
    if not workflow_files:
        print(f"工作流目录 {workflow_dir} 中没有工作流文件")
        return
    
    print(f"在 {workflow_dir} 中找到 {len(workflow_files)} 个工作流:")
    
    for file_path in workflow_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            
            print(f"\n工作流: {workflow.get('name', 'unnamed')} ({file_path.name})")
            print(f"  ID: {workflow.get('id', 'unknown')}")
            print(f"  描述: {workflow.get('description', 'no description')}")
            print(f"  关键词: {', '.join(workflow.get('keywords', []))}")
            print(f"  操作数: {len(workflow.get('actions', []))}")
            
            for action in workflow.get("actions", []):
                print(f"    - 操作: {action.get('id', 'unknown')}")
                print(f"      描述: {action.get('description', 'no description')}")
                print(f"      步骤数: {len(action.get('steps', []))}")
        
        except Exception as e:
            print(f"  ⚠️ 无法读取工作流 {file_path.name}: {e}")

def test_workflow(args):
    """通过API测试工作流"""
    # 检查API服务是否可用
    api_url = f"{args.api_base}/workflow/{args.workflow_id}/test"
    params = {
        "action_id": args.action_id,
        "session_id": args.session_id
    }
    
    try:
        print(f"正在测试工作流: {args.workflow_id}.{args.action_id}")
        response = requests.post(api_url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ 测试成功!")
            print(f"执行了 {result.get('steps_count', 0)} 个步骤")
            print("\n结果:")
            print(json.dumps(result.get('result', {}), indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ 测试失败: HTTP {response.status_code}")
            print(response.text)
    
    except requests.RequestException as e:
        print(f"\n❌ 连接API服务失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试工作流时出现未知错误: {e}")

def convert_handler_to_workflow(args):
    """将Handler类转换为工作流JSON"""
    handler_file = Path(args.handler_file)
    if not handler_file.exists():
        print(f"错误: Handler文件 {handler_file} 不存在")
        return
    
    # 读取Handler文件内容
    with open(handler_file, 'r', encoding='utf-8') as f:
        handler_content = f.read()
    
    # 提取Handler类名
    class_match = re.search(r'class\s+(\w+)\(', handler_content)
    if not class_match:
        print("错误: 无法在文件中找到Handler类定义")
        return
    
    handler_class = class_match.group(1)
    
    # 提取方法
    method_pattern = r'async\s+def\s+(\w+)\s*\('
    methods = re.findall(method_pattern, handler_content)
    
    # 过滤掉常见的基础方法
    excluded_methods = {"__init__", "process_query", "cleanup"}
    action_methods = [m for m in methods if m not in excluded_methods]
    
    if not action_methods:
        print(f"警告: 在 {handler_class} 中没有找到可转换为操作的方法")
    
    # 创建工作流模板
    workflow_id = args.id or handler_class.lower().replace("handler", "workflow")
    workflow = {
        "id": workflow_id,
        "name": args.name or re.sub(r'([A-Z])', r' \1', handler_class).replace("Handler", "").strip(),
        "description": args.description or f"从 {handler_class} 转换的工作流",
        "keywords": args.keywords.split(",") if args.keywords else [],
        "version": "1.0",
        "actions": []
    }
    
    # 为每个方法创建操作
    for method in action_methods:
        # 提取方法内容
        method_content_match = re.search(r'async\s+def\s+' + method + r'\s*\([^)]*\):\s*("""[^"]*""")?', handler_content)
        method_doc = ""
        if method_content_match and method_content_match.group(1):
            method_doc = method_content_match.group(1).strip('"\' \t\n')
        
        action = {
            "id": method,
            "name": re.sub(r'_', ' ', method).title(),
            "description": method_doc,
            "steps": [
                {
                    "id": "step_1",
                    "action": "highlight_elements",
                    "parameters": {
                        "viewport_expansion": 500
                    },
                    "description": "高亮页面元素"
                },
                {
                    "id": "step_2",
                    "action": "done",
                    "parameters": {
                        "success": True,
                        "text": "操作完成"
                    },
                    "description": "完成操作"
                }
            ]
        }
        
        workflow["actions"].append(action)
    
    # 写入文件
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    
    output_file = output_dir / f"{workflow_id}.json"
    
    # 检查文件是否已存在
    if output_file.exists() and not args.force:
        print(f"错误: 工作流文件 {output_file} 已存在. 使用 --force 选项覆盖")
        return
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)
    
    print(f"成功将 {handler_class} 转换为工作流: {output_file}")
    print(f"注意: 生成的工作流只包含基础步骤模板，需要根据Handler实际逻辑修改")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="工作流管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 创建新工作流
    create_parser = subparsers.add_parser("create", help="创建新工作流")
    create_parser.add_argument("--name", required=True, help="工作流名称")
    create_parser.add_argument("--id", help="工作流ID (默认自动生成)")
    create_parser.add_argument("--description", default="", help="工作流描述")
    create_parser.add_argument("--keywords", default="", help="关键词列表，用逗号分隔")
    create_parser.add_argument("--dir", default=DEFAULT_WORKFLOWS_DIR, help="工作流目录")
    create_parser.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    
    # 验证工作流
    validate_parser = subparsers.add_parser("validate", help="验证工作流")
    validate_parser.add_argument("file", help="工作流JSON文件路径")
    
    # 列出工作流
    list_parser = subparsers.add_parser("list", help="列出所有工作流")
    list_parser.add_argument("--dir", default=DEFAULT_WORKFLOWS_DIR, help="工作流目录")
    
    # 测试工作流
    test_parser = subparsers.add_parser("test", help="通过API测试工作流")
    test_parser.add_argument("workflow_id", help="工作流ID")
    test_parser.add_argument("action_id", help="操作ID")
    test_parser.add_argument("--session_id", default="test_session", help="会话ID")
    test_parser.add_argument("--api_base", default="http://localhost:8000", help="API基础URL")
    
    # 从Handler转换为工作流
    convert_parser = subparsers.add_parser("convert", help="将Handler类转换为工作流")
    convert_parser.add_argument("handler_file", help="Handler源文件路径")
    convert_parser.add_argument("--id", help="工作流ID (默认根据Handler名生成)")
    convert_parser.add_argument("--name", help="工作流名称 (默认根据Handler名生成)")
    convert_parser.add_argument("--description", help="工作流描述")
    convert_parser.add_argument("--keywords", default="", help="关键词列表，用逗号分隔")
    convert_parser.add_argument("--output_dir", default=DEFAULT_WORKFLOWS_DIR, help="输出目录")
    convert_parser.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_new_workflow(args)
    elif args.command == "validate":
        validate_workflow(args)
    elif args.command == "list":
        list_workflows(args)
    elif args.command == "test":
        test_workflow(args)
    elif args.command == "convert":
        convert_handler_to_workflow(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()