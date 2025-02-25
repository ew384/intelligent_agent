# test_hr_recruitment.py
import asyncio
import httpx
import logging
import json
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HRRecruitmentTest")

async def test_hr_recruitment():
    """Test the HR recruitment scenario"""
    logger.info("Testing HR recruitment scenario")
    
    # Prepare the request data
    request_data = {
        "scenario_type": "hr_recruitment",
        "parameters": {
            "url": "https://www.zhipin.com/",
            "username": "your_username",  # Replace with actual credentials
            "password": "your_password",  # Replace with actual credentials
            "job_requirements": """
                职位：Python后端开发工程师
                要求：
                1. 熟练掌握Python编程语言和常用框架（如Django、Flask）
                2. 有至少2年的后端开发经验
                3. 熟悉SQL数据库和NoSQL数据库
                4. 了解微服务架构和API设计
                5. 有良好的代码风格和文档习惯
            """,
            "sort_criteria": [
                "技术能力匹配度",
                "工作经验",
                "教育背景",
                "项目经历"
            ]
        }
    }
    
    try:
        # Call the API gateway
        async with httpx.AsyncClient() as client:
            logger.info("Sending request to API gateway")
            
            response = await client.post(
                "http://localhost:8000/tasks",
                json=request_data,
                timeout=600  # 10 minute timeout since login and resume extraction might take time
            )
            
            if response.status_code != 200:
                logger.error(f"API gateway returned status code {response.status_code}")
                logger.error(f"Response: {response.text}")
                return
            
            result = response.json()
            
            logger.info("Response received from API gateway")
            logger.info(f"Status: {result.get('status')}")
            logger.info(f"Task ID: {result.get('task_id')}")
            
            # Pretty print the result
            logger.info("Result details:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(test_hr_recruitment())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)