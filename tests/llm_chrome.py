import os
import json
import socket
import subprocess
import time
import platform
import random
from pathlib import Path

# 配置基本参数
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
        #"/usr/local/bin/chrome-for-testing",
        #"/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ]

# 查找第一个存在的路径
for path in chrome_paths:
    if os.path.exists(path):
        chrome_binary = path
        break
user_data_dir = Path('./browser_data/claude')
debugging_port = 54805

cmd = [
    chrome_binary,
    f"--remote-debugging-port={debugging_port}",
    #f"--user-data-dir={user_data_dir}",
    #"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    #"--disable-extensions",
    "--enable-unsafe-swiftshader",
    #"--disable-component-extensions-with-background-pages",
    #"--disable-background-networking"
]
# 以非阻塞方式启动Chrome
debug_process = subprocess.Popen(cmd)