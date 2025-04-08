import os
import json
import socket
import subprocess
import time
import platform
import random
from pathlib import Path

# 配置基本参数
chrome_binary = "/usr/bin/google-chrome"
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