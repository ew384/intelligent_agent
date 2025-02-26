from abc import ABC, abstractmethod
from typing import Dict, Any
from playwright.async_api import Page

class BaseHandler(ABC):
    def __init__(self, page: Page):
        self.page = page
    
    @abstractmethod
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理查询的抽象方法"""
        pass