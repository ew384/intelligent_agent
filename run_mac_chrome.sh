#!/bin/bash

# 此脚本用于启动两个完全独立的Chrome实例，每个实例使用不同的固定用户数据目录和远程调试端口。
# 这允许保存登录状态和浏览历史，同时确保浏览器实例之间的隔离。

# 设置脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
if [ -z "$SCRIPT_DIR" ]; then
  SCRIPT_DIR="$(pwd)"
fi

# 创建用户数据目录
mkdir -p "$SCRIPT_DIR/browser_data/claude_profile"
mkdir -p "$SCRIPT_DIR/browser_data/agent_profile"

# 根据操作系统查找Chrome路径
find_chrome_path() {
  local chrome_path=""
  
  # 检测操作系统类型
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if [ -d "/Applications/Google Chrome.app" ]; then
      chrome_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    fi
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    for path in "/usr/bin/google-chrome" "/usr/bin/google-chrome-stable" "/usr/bin/chromium-browser"; do
      if [ -f "$path" ]; then
        chrome_path="$path"
        break
      fi
    done
  elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win32" ]]; then
    # Windows with Git Bash or similar
    for path in "/c/Program Files/Google/Chrome/Application/chrome.exe" "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"; do
      if [ -f "$path" ]; then
        chrome_path="$path"
        break
      fi
    done
  fi
  
  echo "$chrome_path"
}

# 获取Chrome路径
CHROME_PATH=$(find_chrome_path)

if [ -z "$CHROME_PATH" ]; then
  echo "错误: 找不到Chrome浏览器。请安装Chrome或手动指定Chrome路径。"
  exit 1
fi

echo "找到Chrome路径: $CHROME_PATH"

# 检查端口是否可用
check_port() {
  local port=$1
  if command -v nc &> /dev/null; then
    nc -z localhost $port &> /dev/null
    if [ $? -eq 0 ]; then
      echo "错误: 端口 $port 已被占用。请确保没有其他Chrome实例正在使用此端口。"
      return 1
    fi
  elif command -v lsof &> /dev/null; then
    lsof -i:$port &> /dev/null
    if [ $? -eq 0 ]; then
      echo "错误: 端口 $port 已被占用。请确保没有其他Chrome实例正在使用此端口。"
      return 1
    fi
  else
    echo "警告: 无法检查端口 $port 是否可用。假设端口可用。"
  fi
  return 0
}

# 启动Chrome进程
launch_chrome() {
  local port=$1
  local user_data_dir=$2
  local instance_name=$3
  
  # 检查端口是否可用
  check_port $port
  if [ $? -ne 0 ]; then
    return 1
  fi
  
  echo "启动$instance_name Chrome实例，端口: $port"
  echo "命令: \"$CHROME_PATH\" --remote-debugging-port=$port --user-data-dir=$user_data_dir --no-first-run --no-default-browser-check"
  
  # 启动Chrome
  "$CHROME_PATH" --remote-debugging-port=$port --user-data-dir=$user_data_dir --no-first-run --no-default-browser-check &
  
  local pid=$!
  echo "$instance_name Chrome实例已启动，PID: $pid"
  return 0
}

# 先启动Claude Chrome
echo "启动Claude Chrome实例..."
launch_chrome 54805 "$SCRIPT_DIR/browser_data/claude_profile" "Claude"

# 等待5秒
echo "等待5秒..."
sleep 5

# 然后启动Agent Chrome
echo "启动Agent Chrome实例..."
launch_chrome 54905 "$SCRIPT_DIR/browser_data/agent_profile" "Agent"

echo -e "\n两个Chrome实例已启动:"
echo "Claude Chrome: 端口 54805, 用户数据目录: $SCRIPT_DIR/browser_data/claude_profile"
echo "Agent Chrome: 端口 54905, 用户数据目录: $SCRIPT_DIR/browser_data/agent_profile"
echo -e "\n使用ChromeDriver连接时，设置:"
echo "  chrome_options.add_experimental_option('debuggerAddress', 'localhost:54805') # 连接Claude Chrome"
echo "  chrome_options.add_experimental_option('debuggerAddress', 'localhost:54905') # 连接Agent Chrome"

echo -e "\n两个Chrome实例现在正在后台运行。"
echo "要关闭它们，您可以使用浏览器的关闭按钮或使用以下命令:"
echo "  pkill -f \"remote-debugging-port=548\""

# 脚本结束，但Chrome进程会在后台继续运行
