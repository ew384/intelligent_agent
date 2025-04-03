import json
import time
from typing import Dict, List, Any, Optional, Callable
from .spa_tools import function_tools

class WebsiteAgentIntegration:
    """
    Integration class for connecting website tools with agent functionality
    """
    def __init__(self):
        self.tools = function_tools
        self.current_menu = None
        self.current_page_content = None
        self.last_action_result = None
        self.session_context = {}
    
    def get_tools(self) -> Dict[str, Callable]:
        """Return all tools for agent integration"""
        return self.tools
    
    async def analyze_user_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine the likely intent and required navigation
        This would typically be handled by the agent's LLM, but we provide helper functionality
        
        Args:
            query (str): The user's query
            
        Returns:
            Dict: Information about the detected intent
        """
        query_lower = query.lower()
        
        # Extract key intent indicators
        intent_keywords = {
            "分期": ["分期", "分期付款", "分期还款", "账单分期"],
            "查询": ["查询", "查看", "余额", "额度", "查一下"],
            "申请": ["申请", "办理", "开通", "激活"],
            "还款": ["还款", "还钱", "付款", "缴费"],
            "账单": ["账单", "对账单", "消费记录", "消费明细"]
        }
        
        detected_intents = []
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected_intents.append(intent)
                    break
        
        # Extract amount information
        amount = None
        amount_patterns = [
            r'(\d+)元',
            r'(\d+)块',
            r'(\d+)万',
            r'(\d+)千',
            r'(\d+,\d+)',
            r'(\d+\.\d+)元'
        ]
        
        for pattern in amount_patterns:
            import re
            match = re.search(pattern, query)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Adjust for units
                    if '万' in match.group():
                        amount *= 10000
                    elif '千' in match.group():
                        amount *= 1000
                    break
                except:
                    pass
        
        # Extract period information
        period = None
        period_patterns = [
            r'(\d+)期',
            r'(\d+)个月',
            r'分(\d+)期',
            r'(\d+)月还清'
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, query)
            if match:
                try:
                    period = int(match.group(1))
                    break
                except:
                    pass
        
        # Determine most relevant menu paths based on intent
        recommended_menu_paths = []
        if '分期' in detected_intents:
            recommended_menu_paths.extend([
                "分期业务",
                "分期业务 > 分期申请",
                "分期业务 > 账单分期"
            ])
        
        if '查询' in detected_intents:
            recommended_menu_paths.extend([
                "账户信息",
                "账户信息 > 额度查询",
                "账户信息 > 账户概览"
            ])
        
        if '还款' in detected_intents:
            recommended_menu_paths.extend([
                "还款",
                "还款 > 还款记录",
                "还款 > 还款申请"
            ])
            
        if '账单' in detected_intents:
            recommended_menu_paths.extend([
                "账单",
                "账单 > 账单查询",
                "账单 > 明细查询"
            ])
            
        # Compile results
        return {
            "detected_intents": detected_intents,
            "amount": amount,
            "period": period,
            "recommended_menu_paths": recommended_menu_paths,
            "query": query
        }
    
    async def search_appropriate_menu(self, query: str) -> Dict[str, Any]:
        """
        Search for appropriate menu items based on the user query
        
        Args:
            query (str): The user's query
            
        Returns:
            Dict: Search results and recommendations
        """
        # Extract key terms from the query
        key_terms = []
        important_terms = ["分期", "还款", "查询", "账单", "额度", "申请", "办理"]
        
        for term in important_terms:
            if term in query:
                key_terms.append(term)
        
        # If no key terms found, use basic segmentation
        if not key_terms:
            # Simple word segmentation
            words = query.split()
            key_terms = [w for w in words if len(w) >= 2]
        
        # Search results for each term
        all_results = []
        for term in key_terms:
            result = await self.tools["search_menu_items"](term)
            if result["status"] == "success" and result["content"]:
                all_results.extend(result["content"])
        
        # Deduplicate results
        unique_results = []
        seen_paths = set()
        
        for item in all_results:
            if item["path"] not in seen_paths:
                unique_results.append(item)
                seen_paths.add(item["path"])
        
        return {
            "status": "success",
            "search_terms": key_terms,
            "results": unique_results
        }
    
    async def execute_navigation_flow(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete navigation flow based on intent analysis
        
        Args:
            intent_analysis (Dict): The result of analyze_user_intent
            
        Returns:
            Dict: Results of the navigation flow
        """
        # Step 1: Search for relevant menu items
        search_results = await self.search_appropriate_menu(intent_analysis["query"])
        
        if search_results["status"] != "success" or not search_results["results"]:
            # If no direct matches, try recommended paths
            for path in intent_analysis["recommended_menu_paths"]:
                # Try to navigate to each recommended path
                result = await self.tools["navigate_to_menu"](path)
                if result["status"] == "success":
                    self.current_menu = path
                    self.current_page_content = result["content"]
                    self.last_action_result = result
                    
                    return {
                        "status": "success",
                        "message": f"Successfully navigated to {path}",
                        "current_menu": path,
                        "page_content": result["content"]
                    }
            
            return {
                "status": "error",
                "message": "Could not find appropriate menu items for this query"
            }
        
        # Step 2: Navigate to the most relevant menu
        best_match = search_results["results"][0]
        result = await self.tools["navigate_to_menu"](best_match["path"])
        
        if result["status"] != "success":
            return {
                "status": "error",
                "message": f"Failed to navigate to {best_match['path']}"
            }
        
        # Step 3: Update current state
        self.current_menu = best_match["path"]
        self.current_page_content = result["content"]
        self.last_action_result = result
        
        # Step 4: Process form fields if needed
        if intent_analysis["amount"] is not None or intent_analysis["period"] is not None:
            # Look for relevant form fields
            if result["content"] and "form_fields" in result["content"]:
                for field in result["content"]["form_fields"]:
                    # Match amount field
                    if intent_analysis["amount"] is not None and any(keyword in field["name"].lower() for keyword in ["amount", "金额", "money", "sum"]):
                        await self.tools["fill_input_in_iframe"](field["name"], str(intent_analysis["amount"]))
                    
                    # Match period field
                    if intent_analysis["period"] is not None and any(keyword in field["name"].lower() for keyword in ["period", "term", "期数", "分期", "月数"]):
                        await self.tools["fill_input_in_iframe"](field["name"], str(intent_analysis["period"]))
        
        return {
            "status": "success",
            "message": f"Successfully navigated to {best_match['path']}",
            "current_menu": best_match["path"],
            "page_content": result["content"]
        }
    
    async def process_customer_inquiry(self, query: str) -> Dict[str, Any]:
        """
        High-level function to process a customer inquiry end-to-end
        
        Args:
            query (str): The customer's inquiry
            
        Returns:
            Dict: Result of processing the inquiry
        """
        # Step 1: Analyze intent
        intent_analysis = await self.analyze_user_intent(query)
        
        # Step 2: Execute navigation flow
        nav_result = await self.execute_navigation_flow(intent_analysis)
        
        if nav_result["status"] != "success":
            return nav_result
        
        # Step 3: Determine if we need additional actions based on the page content
        additional_actions = []
        
        # Check if we're on a page with forms that need to be filled
        if (
            self.current_page_content and 
            "form_fields" in self.current_page_content and 
            self.current_page_content["form_fields"]
        ):
            additional_actions.append({
                "type": "form_filling",
                "fields": self.current_page_content["form_fields"]
            })
        
        # Check if we're on a page with buttons that should be clicked
        if (
            self.current_page_content and 
            "buttons" in self.current_page_content and 
            self.current_page_content["buttons"]
        ):
            additional_actions.append({
                "type": "button_clicking",
                "buttons": self.current_page_content["buttons"]
            })
        
        # Compile response with guidance
        return {
            "status": "success",
            "intent_analysis": intent_analysis,
            "navigation_result": nav_result,
            "additional_actions": additional_actions,
            "guidance": self._generate_guidance(intent_analysis, nav_result, additional_actions)
        }
    
    def _generate_guidance(self, intent_analysis, nav_result, additional_actions) -> str:
        """Generate guidance text based on the current state"""
        guidance = []
        
        # Add basic navigation info
        guidance.append(f"已导航至: {self.current_menu}")
        
        # Add form field guidance if needed
        if any(action["type"] == "form_filling" for action in additional_actions):
            form_action = next(action for action in additional_actions if action["type"] == "form_filling")
            required_fields = [field for field in form_action["fields"] if field.get("required")]
            
            if required_fields:
                guidance.append("\n需要填写的字段:")
                for field in required_fields:
                    guidance.append(f"- {field.get('label', field.get('name'))}")
        
        # Add button guidance if needed
        if any(action["type"] == "button_clicking" for action in additional_actions):
            button_action = next(action for action in additional_actions if action["type"] == "button_clicking")
            if button_action["buttons"]:
                guidance.append("\n可执行的操作:")
                for button in button_action["buttons"]:
                    guidance.append(f"- 点击 [{button}] 按钮")
        
        return "\n".join(guidance)
    
    async def execute_form_action(self, field_values: Dict[str, str]) -> Dict[str, Any]:
        """
        Fill out form fields with the provided values
        
        Args:
            field_values (Dict): Dictionary mapping field names to values
            
        Returns:
            Dict: Result of the form filling operation
        """
        results = []
        
        for field_name, value in field_values.items():
            result = await self.tools["fill_input_in_iframe"](field_name, value)
            results.append(result)
        
        # Get updated content
        content_result = await self.tools["get_current_iframe_content"]
        if content_result["status"] == "success":
            self.current_page_content = content_result["content"]
        
        return {
            "status": "success",
            "message": f"Filled {len(results)} form fields",
            "field_results": results,
            "current_content": self.current_page_content
        }
    
    async def execute_button_action(self, button_text: str) -> Dict[str, Any]:
        """
        Click a button in the current page
        
        Args:
            button_text (str): The text of the button to click
            
        Returns:
            Dict: Result of the button click operation
        """
        result = await self.tools["click_button_in_iframe"](button_text)
        
        if result["status"] == "success" and result["content"]:
            self.current_page_content = result["content"]
        
        self.last_action_result = result
        
        return result
    
    async def process_installment_request(self, amount: float, periods: int) -> Dict[str, Any]:
        """
        Process an installment request with the specified amount and periods
        
        Args:
            amount (float): The amount for installment
            periods (int): The number of periods
            
        Returns:
            Dict: Result of processing the installment request
        """
        # Step 1: Navigate to installment page
        nav_result = await self.tools["navigate_to_menu"]("分期业务 > 分期申请")
        
        if nav_result["status"] != "success":
            return {
                "status": "error",
                "message": "Failed to navigate to installment page"
            }
        
        self.current_menu = "分期业务 > 分期申请"
        self.current_page_content = nav_result["content"]
        
        # Step 2: Fill out form fields
        form_fields = {
            "金额": str(amount),
            "分期期数": str(periods)
        }
        
        form_result = await self.execute_form_action(form_fields)
        
        if form_result["status"] != "success":
            return {
                "status": "warning",
                "message": "Form filling had some issues",
                "form_result": form_result
            }
        
        # Step 3: Calculate installment plan
        plan_result = await self.tools["calculate_installment_plan"](amount, periods)
        
        if plan_result["status"] != "success":
            return {
                "status": "error",
                "message": "Failed to calculate installment plan",
                "plan_result": plan_result
            }
        
        # Step 4: Submit form
        button_result = await self.execute_button_action("提交")
        
        return {
            "status": "success",
            "message": "Installment request processed successfully",
            "installment_plan": plan_result["content"],
            "submission_result": button_result
        }
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get the current state of the agent
        
        Returns:
            Dict: Current state information
        """
        return {
            "current_menu": self.current_menu,
            "current_page_content": self.current_page_content,
            "last_action_result": self.last_action_result,
            "session_context": self.session_context
        }

# Create instance for easy import
agent_integration = WebsiteAgentIntegration()

# Export tools for agent consumption
agent_tools = agent_integration.get_tools()
