#!/usr/bin/env python3
"""
此脚本用于启动两个完全独立的Chrome实例，每个实例使用不同的固定用户数据目录和远程调试端口。
这允许保存登录状态和浏览历史，同时确保浏览器实例之间的隔离。
"""

import os
import subprocess
import time
import random
import signal
import sys
import platform
from pathlib import Path

# 查找Chrome路径
system = platform.system()
if system == "Windows":
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
elif system == "Darwin":
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
else:
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser"
    ]

chrome_binary = None
for path in chrome_paths:
    if os.path.exists(path):
        chrome_binary = path
        break

if not chrome_binary:
    print("错误: 找不到Chrome浏览器。请安装Chrome或手动指定Chrome路径。")
    sys.exit(1)

print(f"找到Chrome路径: {chrome_binary}")

# 获取脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))
if not script_dir:  # 如果获取失败，使用当前工作目录
    script_dir = os.getcwd()

# 创建固定的用户数据目录
def create_user_data_dir(profile_name):
    """创建固定的用户数据目录"""
    # 在脚本目录下创建browser_profiles目录
    profile_path = os.path.join(script_dir, "browser_data", profile_name)
    
    # 确保目录存在
    os.makedirs(profile_path, exist_ok=True)
    
    print(f"为{profile_name}使用固定用户数据目录: {profile_path}")
    return profile_path

# 检查端口是否可用
def is_port_available(port):
    """检查端口是否可用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

# 启动Chrome进程
def launch_chrome(debugging_port, user_data_dir, instance_name):
    """启动Chrome浏览器"""
    # 首先检查端口是否可用
    if not is_port_available(debugging_port):
        print(f"错误: 端口 {debugging_port} 已被占用。请确保没有其他Chrome实例正在使用此端口。")
        return None
    
    # 创建一个随机的用户代理字符串，但在实例之间保持一致
    # 这样每次启动同一个实例时都使用相同的用户代理
    user_agent_path = os.path.join(user_data_dir, ".user_agent")
    if os.path.exists(user_agent_path):
        with open(user_agent_path, 'r') as f:
            user_agent = f.read().strip()
    else:
        user_agent = f"Mozilla/5.0 (Linux; Chrome/110.0.) Chrome/CustomAgent{random.randint(10000, 99999)}"
        with open(user_agent_path, 'w') as f:
            f.write(user_agent)
    
    cmd = [
        chrome_binary,
        f"--remote-debugging-port={debugging_port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",                    # 避免首次运行向导
        "--no-default-browser-check",        # 不检查默认浏览器
        "--password-store=basic",            # 使用基本密码存储
    ]
    
    print(f"启动{instance_name} Chrome实例，端口: {debugging_port}")
    print(f"命令: {' '.join(cmd)}")
    
    # 以非阻塞方式启动Chrome
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待几秒钟让Chrome初始化
    time.sleep(2)
    
    # 检查进程是否还活着
    if process.poll() is not None:
        print(f"警告: {instance_name} Chrome进程已退出，退出码: {process.poll()}")
        stderr_output = process.stderr.read().decode('utf-8', errors='replace')
        print(f"错误输出: {stderr_output}")
        return None
    
    print(f"{instance_name} Chrome实例已启动，PID: {process.pid}")
    return process

# 主函数
def main():
    # 存储进程以便清理
    processes = []
    
    try:
        # 创建第一个Chrome实例的用户数据目录
        user_data_dir_1 = create_user_data_dir("claude_profile")
        
        # 启动第一个Chrome实例
        process_1 = launch_chrome(54805, user_data_dir_1, "Claude")
        if process_1:
            processes.append(process_1)
        
        # 等待第一个Chrome实例完全初始化
        print("等待第一个Chrome实例初始化...")
        time.sleep(5)
        
        # 创建第二个Chrome实例的用户数据目录
        user_data_dir_2 = create_user_data_dir("agent_profile")
        
        # 启动第二个Chrome实例
        process_2 = launch_chrome(54905, user_data_dir_2, "Agent")
        if process_2:
            processes.append(process_2)
        
        print("\n两个Chrome实例已启动:")
        print(f"Claude Chrome: 端口 54805, 用户数据目录: {user_data_dir_1}")
        print(f"Agent Chrome: 端口 54905, 用户数据目录: {user_data_dir_2}")
        print("\n使用ChromeDriver连接时，设置:")
        print("  chrome_options.add_experimental_option('debuggerAddress', 'localhost:54805') # 连接Claude Chrome")
        print("  chrome_options.add_experimental_option('debuggerAddress', 'localhost:54905') # 连接Agent Chrome")
        
        print("\n按Ctrl+C退出...")
        
        # 保持程序运行，直到用户按下Ctrl+C
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在关闭Chrome实例...")
    
    finally:
        # 清理进程
        for process in processes:
            try:
                if process.poll() is None:  # 确认进程还在运行
                    print(f"正在终止Chrome进程 {process.pid}...")
                    process.terminate()
                    process.wait(timeout=5)
            except:
                print(f"无法正常终止进程 {process.pid}，尝试强制关闭...")
                try:
                    process.kill()
                except:
                    pass
        
        print("清理完成，程序退出。")

if __name__ == "__main__":
    main()
