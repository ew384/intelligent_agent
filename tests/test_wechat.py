import asyncio
import httpx
import logging
import json
import sys
import os
from pathlib import Path
import time
async def send_wechat_message():
    processed_params = {
        "contact_name": "陈浩",
        "message": "测试微信数据接口 "
    }

    async with httpx.AsyncClient() as client:
        tool_response = await client.post(
            "http://localhost:8003/tools/wechat/search_and_send",
            json=processed_params,
            timeout=300.0
        )

    tool_response.raise_for_status()
    return tool_response.json()

#sent bill to person via wechat
async def send_bill_via_wechat():
    request_data = {
            "scenario_type": "credit_card",
            "parameters": {
                "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html",
                "notify_wechat": True,
                "wechat_contact": "陈浩"
            }
        }
    async with httpx.AsyncClient() as client:
        logger.info("发送请求到API网关")
    
        response = await client.post(
            "http://localhost:8000/tasks",
            json=request_data,
            timeout=300  # 5分钟超时，因为登录可能需要时间
        )
    return response.json()

# Run the async function
if __name__ == "__main__":
    result = asyncio.run(send_wechat_message())
    print(result)
