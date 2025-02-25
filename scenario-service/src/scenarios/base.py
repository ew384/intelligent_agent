# scenario-service/src/scenarios/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseScenario(ABC):
    """Base class for all scenarios"""
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Get configuration for this scenario
        
        Returns:
            Dict containing the scenario configuration including:
            - type: The scenario type identifier
            - parameters: Required parameters and their specs
            - workflow: Workflow steps configuration
        """
        pass