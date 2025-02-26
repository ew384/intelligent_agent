# api_gateway/src/clients/orchestrator.py
import httpx
from typing import Dict, Any

class OrchestratorClient:
    """编排服务客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建任务
        
        Args:
            task_data: 任务数据
            
        Returns:
            任务执行结果
        """
        # 尝试不同的端点路径
        possible_endpoints = [
            f"{self.base_url}/tasks",               # 直接的tasks端点 
            f"{self.base_url}/orchestrator/tasks",  # 带有orchestrator前缀
            f"{self.base_url}/internal/tasks",      # 内部tasks端点
            f"{self.base_url}/api/tasks"            # API前缀
        ]
        
        last_error = None
        for endpoint in possible_endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    # 允许重定向并禁用验证以便于调试
                    response = await client.post(
                        endpoint,
                        json=task_data,
                        timeout=30.0,
                        follow_redirects=True,  # 自动跟随重定向
                    )
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                last_error = e
                print(f"尝试端点 {endpoint} 失败: {str(e)}")
                continue
        
        # 如果所有端点都失败，则抛出最后一个错误
        raise last_error or Exception("所有端点请求都失败了")

# 创建客户端实例
orchestrator_client = OrchestratorClient()
