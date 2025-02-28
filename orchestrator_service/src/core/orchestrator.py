# orchestrator-service/src/core/orchestrator.py
from typing import Dict, Optional, Type
from ..workflows.base import BaseWorkflow
from ..workflows.credit_card import CreditCardWorkflow
from ..workflows.hr_recruitment import HRRecruitmentWorkflow
from ..workflows.ecommerce import ECommerceWorkflow
from ..workflows.price_comparison import PriceComparisonWorkflow

class TaskOrchestrator:
    """Orchestrates tasks by selecting appropriate workflows"""
    
    def __init__(self):
        self._workflows: Dict[str, Type[BaseWorkflow]] = {}
        self._initialize_workflows()
    
    def _initialize_workflows(self):
        """Register all available workflows"""
        # Register the existing credit card workflow
        self.register("credit_card", CreditCardWorkflow)
        self.register("hr_recruitment", HRRecruitmentWorkflow)
        self.register("ecommerce", ECommerceWorkflow)
        self.register("price_comparison", PriceComparisonWorkflow)
    
    def register(self, scenario_type: str, workflow_class: Type[BaseWorkflow]):
        """
        Register a workflow class for a scenario type
        
        Args:
            scenario_type: The scenario type this workflow handles
            workflow_class: The workflow class to register
        """
        self._workflows[scenario_type] = workflow_class
    
    def get_workflow(self, scenario_type: str) -> Optional[BaseWorkflow]:
        """
        Get a workflow instance for the given scenario type
        
        Args:
            scenario_type: The type of scenario to get a workflow for
            
        Returns:
            An instance of the appropriate workflow, or None if not found
        """
        workflow_class = self._workflows.get(scenario_type)
        if workflow_class:
            return workflow_class()
        return None
