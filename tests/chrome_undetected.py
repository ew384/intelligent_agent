import os
import json
import socket
import subprocess
import time
import platform
import random
from pathlib import Path
import undetected_chromedriver as uc

# 配置基本参数
chrome_binary = "/usr/bin/google-chrome"
user_data_dir = Path('./browser_data/claude')
debugging_port = 54805 
options = uc.ChromeOptions()
# 添加其他反检测选项
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--disable-extensions')
options.add_argument(f"--user-data-dir={user_data_dir}")
driver = uc.Chrome(options=options,port=debugging_port,use_subprocess=False,version_main=134)
print(f"ChromeDriver 路径: {driver.service.path}")
time.sleep(100000000)
