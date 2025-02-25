# scenario-service/src/core/registry.py
from typing import Dict, Optional, Type
from ..scenarios.base import BaseScenario
from ..scenarios.credit_card import CreditCardScenario

class ScenarioRegistry:
    """Registry for all available scenarios"""
    
    def __init__(self):
        self._scenarios: Dict[str, Type[BaseScenario]] = {}
        self._initialize_scenarios()
    
    def _initialize_scenarios(self):
        """Register all available scenarios"""
        # Register the existing credit card scenario
        self.register("credit_card", CreditCardScenario)
        
        # Register other scenarios we've implemented
        from ..scenarios.hr_recruitment import HRRecruitmentScenario
        from ..scenarios.ecommerce import ECommerceScenario
        from ..scenarios.price_comparison import PriceComparisonScenario
        
        self.register("hr_recruitment", HRRecruitmentScenario)
        self.register("ecommerce", ECommerceScenario)
        self.register("price_comparison", PriceComparisonScenario)
    
    def register(self, scenario_type: str, scenario_class: Type[BaseScenario]):
        """
        Register a scenario class
        
        Args:
            scenario_type: Unique identifier for the scenario
            scenario_class: The scenario class to register
        """
        self._scenarios[scenario_type] = scenario_class
    
    def get_scenario(self, scenario_type: str) -> Optional[BaseScenario]:
        """
        Get a scenario instance by type
        
        Args:
            scenario_type: The type of scenario to retrieve
            
        Returns:
            An instance of the requested scenario, or None if not found
        """
        scenario_class = self._scenarios.get(scenario_type)
        if scenario_class:
            return scenario_class()
        return None
    
    def list_scenarios(self) -> Dict[str, str]:
        """
        List all available scenarios
        
        Returns:
            Dict mapping scenario types to their class names
        """
        return {scenario_type: scenario_class.__name__ 
                for scenario_type, scenario_class in self._scenarios.items()}