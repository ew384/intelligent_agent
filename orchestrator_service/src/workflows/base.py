# orchestrator-service/src/workflows/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
#**Purpose**: Coordinate workflow execution
class BaseWorkflow(ABC):
    """Base class for all workflows"""
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the workflow with the given parameters
        
        Args:
            parameters: The parameters required for the workflow
            
        Returns:
            Dict containing the results of the workflow execution
        """
        pass