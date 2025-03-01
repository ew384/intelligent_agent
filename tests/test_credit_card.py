# tests/test_credit_card.py
import asyncio
import httpx
import logging
import json
import sys
import os
from pathlib import Path
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CreditCardTest")

async def test_credit_card():
    """Test the credit card scenario"""
    logger.info("测试信用卡账单查询场景")
    
    # 创建截图保存目录
    screenshots_dir = Path("./test_results")
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    # 准备请求数据
    request_data = {
        "scenario_type": "credit_card",
        "parameters": {
            "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html"
        }
    }
    
    try:
        # 调用API网关
        async with httpx.AsyncClient() as client:
            logger.info("发送请求到API网关")
            
            response = await client.post(
                "http://localhost:8000/tasks",
                json=request_data,
                timeout=300  # 5分钟超时，因为登录可能需要时间
            )
            
            if response.status_code != 200:
                logger.error(f"API网关返回状态码 {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return
            
            result = response.json()
            time.sleep(100)
            logger.info("从API网关收到响应")
            logger.info(f"状态: {result.get('status')}")
            logger.info(f"任务ID: {result.get('task_id')}")
            

            # 显示账单信息
            if result.get('status') == 'success':
                bill_info = result.get('result', {}).get('bill_info', {})
                if bill_info:
                    pass
                    '''
                    # 保存账单信息到文件
                    with open(screenshots_dir / "bill_info.json", "w", encoding="utf-8") as f:
                        json.dump(bill_info, f, ensure_ascii=False, indent=2)
                    logger.info(f"已保存账单信息到: {screenshots_dir / 'bill_info.json'}")
                    
                    # 如果有截图路径，复制截图
                    screenshot_path = result.get('result', {}).get('screenshot_path')
                    if screenshot_path and os.path.exists(screenshot_path):
                        import shutil
                        dest_path = screenshots_dir / "bill_screenshot.png"
                        shutil.copy(screenshot_path, dest_path)
                        logger.info(f"已保存账单截图到: {dest_path}")
                    '''
                else:
                    logger.warning("没有找到账单信息")
            else:
                logger.error(f"查询失败: {result.get('message', '未知错误')}")
            
            # 格式化打印完整结果
            logger.info("\n----- 完整响应 -----")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")

async def test_credit_card_direct():
    """直接测试Tool Service的信用卡处理器"""
    logger.info("直接测试信用卡处理器")
    
    try:
        # 调用Tool Service
        async with httpx.AsyncClient() as client:
            logger.info("发送请求到Tool Service")
            
            response = await client.post(
                "http://localhost:8003/tools/browser/credit-card",
                json={
                    "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html"
                },
                timeout=300  # 5分钟超时
            )
            
            if response.status_code != 200:
                logger.error(f"Tool Service返回状态码 {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return
            
            result = response.json()
            
            # 显示账单信息
            if result.get('status') == 'success':
                bill_info = result.get('bill_info', {})
                if bill_info:
                    logger.info("\n----- 账单信息 -----")
                    logger.info(f"账单金额: {bill_info.get('amount', '未找到')}")
                    logger.info(f"账单日期: {bill_info.get('bill_date', '未找到')}")
                    logger.info(f"到期还款日: {bill_info.get('due_date', '未找到')}")
                else:
                    logger.warning("没有找到账单信息")
            else:
                logger.error(f"查询失败: {result.get('message', '未知错误')}")
            
            # 格式化打印完整结果
            logger.info("\n----- 完整响应 -----")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")

async def check_cookies_status():
    """检查cookies状态"""
    logger.info("检查cookies保存状态")
    
    try:
        # 查找cookies文件
        cookies_dir = Path("./browser_data/cookies")
        if not cookies_dir.exists():
            logger.warning(f"Cookies目录不存在: {cookies_dir}")
            return
            
        cookies_files = list(cookies_dir.glob("*_cookies.json"))
        if not cookies_files:
            logger.warning("没有找到cookies文件")
            return
            
        logger.info(f"找到 {len(cookies_files)} 个cookies文件:")
        
        for cookie_file in cookies_files:
            try:
                with open(cookie_file, 'r') as f:
                    cookies = json.load(f)
                    
                cookie_count = len(cookies)
                domain = cookie_file.stem.replace('_cookies', '').replace('_', '.')
                
                logger.info(f"  - {domain}: {cookie_count} 个cookies")
                
                # 显示cookies的过期时间
                valid_cookies = 0
                for cookie in cookies:
                    if 'expires' in cookie:
                        expires = cookie.get('expires')
                        if expires:
                            # 转换为可读格式
                            import datetime
                            try:
                                if isinstance(expires, (int, float)):
                                    expires_date = datetime.datetime.fromtimestamp(expires)
                                    if expires_date > datetime.datetime.now():
                                        valid_cookies += 1
                            except:
                                pass
                
                logger.info(f"    有效cookies: {valid_cookies}/{cookie_count}")
                
            except Exception as e:
                logger.error(f"读取cookies文件 {cookie_file} 失败: {str(e)}")
                
    except Exception as e:
        logger.error(f"检查cookies状态出错: {str(e)}")

if __name__ == "__main__":
    try:
        # 选择要运行的测试
        if len(sys.argv) > 1 and sys.argv[1] == "direct":
            # 直接测试模式
            asyncio.run(test_credit_card_direct())
        elif len(sys.argv) > 1 and sys.argv[1] == "cookies":
            # 检查cookies状态
            asyncio.run(check_cookies_status())
        else:
            # 默认完整流程测试
            asyncio.run(test_credit_card())
            
        # 完成后等待一下，以便查看结果
        time.sleep(1)
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"未预期的错误: {str(e)}")
        sys.exit(1)
