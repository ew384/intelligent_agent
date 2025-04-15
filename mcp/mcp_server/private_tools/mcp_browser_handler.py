from mcp.server.fastmcp import FastMCP
import uvicorn
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
import sys
import os
from pathlib import Path
#import pdb; pdb.set_trace()
# 添加项目根目录到Python路径
current_path = Path(__file__).parent.parent.parent.parent
print(current_path)
sys.path.append(str(current_path))

# Import BaseHandler class
from tool_service.src.tools.handlers.base import BaseHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPBrowserHandler:
    """
    MCP service wrapper for BaseHandler browser automation.
    """
    
    def __init__(self):
        """Initialize the MCP service."""
        self.mcp = FastMCP("browser-automation-tools")
        self.handler = None
        self._register_tools()
    
    def set_browser_context(self, browser_context):
        """
        Set the browser context after initialization.
        
        Args:
            browser_context: The browser context to use for automation
        """
        if self.handler is None:
            self.handler = BaseHandler(browser_context)
            logger.info("Browser context has been set and BaseHandler initialized")
        else:
            logger.warning("BaseHandler already initialized, not setting new browser_context")
    
    def _register_tools(self):
        """Register all BaseHandler methods as MCP tools."""
        
        # ==================== 基础操作 ====================
        
        @self.mcp.tool()
        async def go_to_url(url: str) -> Dict[str, Any]:
            """Navigate to a URL."""
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.go_to_url({"url": url})
        
        @self.mcp.tool()
        async def click_element(index: int, auto_switch_tab: bool = True) -> Dict[str, Any]:
            """Click an element by index."""
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.click_element({"index": index, "auto_switch_tab": auto_switch_tab})
        
        @self.mcp.tool()
        async def input_text(index: int, text: str) -> Dict[str, Any]:
            """Input text into an element."""
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.input_text({"index": index, "text": text})
        
        @self.mcp.tool()
        async def extract_content(goal: str) -> Dict[str, Any]:
            """
            Extract content from the page based on a specific goal.
            
            Args:
                goal: The extraction goal (what to extract)
                
            Returns:
                The extracted content
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.extract_content({"goal": goal})
        
        @self.mcp.tool()
        async def scroll(direction: str = "down", amount: str = "medium") -> Dict[str, Any]:
            """
            Scroll the page in the specified direction and amount.
            
            Args:
                direction: The direction to scroll ("up" or "down")
                amount: The amount to scroll ("small", "medium", "large", or "page")
                
            Returns:
                Result of the scroll operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.scroll({"direction": direction, "amount": amount})
        
        @self.mcp.tool()
        async def wait(time: int = 2, selector: str = None) -> Dict[str, Any]:
            """
            Wait for a specified time or for an element to appear.
            
            Args:
                time: Time to wait in seconds
                selector: CSS selector to wait for (optional)
                
            Returns:
                Result of the wait operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            params = {"time": time}
            if selector:
                params["selector"] = selector
            return await self.handler.wait(params)
        
        # ==================== 标签页操作 ====================
        
        @self.mcp.tool()
        async def get_tabs() -> Dict[str, Any]:
            """
            Get all open tabs.
            
            Returns:
                Information about all open tabs
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.get_tabs({})
        
        @self.mcp.tool()
        async def create_tab(url: str = "about:blank") -> Dict[str, Any]:
            """
            Create a new tab.
            
            Args:
                url: The URL to navigate to in the new tab
                
            Returns:
                Information about the new tab
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.create_tab({"url": url})
        
        @self.mcp.tool()
        async def switch_tab(tab_id: str) -> Dict[str, Any]:
            """
            Switch to a specific tab by ID.
            
            Args:
                tab_id: The ID of the tab to switch to
                
            Returns:
                Result of the tab switch operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.switch_tab({"tab_id": tab_id})
        
        @self.mcp.tool()
        async def close_tab() -> Dict[str, Any]:
            """
            Close the current tab.
            
            Returns:
                Result of the tab close operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.close_tab({})
        
        # ==================== 元素查找与操作 ====================
        
        @self.mcp.tool()
        async def highlight_elements(viewport_expansion: int = 500) -> Dict[str, Any]:
            """
            Highlight elements on the page.
            
            Args:
                viewport_expansion: How much to expand the viewport for highlighting
                
            Returns:
                Result of the highlight operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.highlight_elements({"viewport_expansion": viewport_expansion})
        
        @self.mcp.tool()
        async def find_element_by_text(text: str, partial_match: bool = True) -> Dict[str, Any]:
            """
            Find elements containing the specified text.
            
            Args:
                text: The text to search for
                partial_match: Whether to use partial matching
                
            Returns:
                Elements found matching the text
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.find_element_by_text({"text": text, "partial_match": partial_match})
        
        @self.mcp.tool()
        async def find_element_by_attribute(attribute: str, value: str, partial_match: bool = True) -> Dict[str, Any]:
            """
            Find elements by attribute and value.
            
            Args:
                attribute: The attribute name to search for
                value: The attribute value to search for
                partial_match: Whether to use partial matching
                
            Returns:
                Elements found matching the attribute and value
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.find_element_by_attribute({
                "attribute": attribute,
                "value": value,
                "partial_match": partial_match
            })
        
        # ==================== 高级操作 ====================
        
        @self.mcp.tool()
        async def inject_script(script: str) -> Dict[str, Any]:
            """
            Inject and execute JavaScript on the page.
            
            Args:
                script: The JavaScript code to execute
                
            Returns:
                Result of the script execution
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.inject_script({"script": script})
        
        @self.mcp.tool()
        async def input_by_selector(selector: str, text: str) -> Dict[str, Any]:
            """
            Input text into an element identified by a CSS selector.
            
            Args:
                selector: The CSS selector to identify the element
                text: The text to input
                
            Returns:
                Result of the input operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.input_by_selector({"selector": selector, "text": text})
        
        # ==================== 组合工具 ====================
        
        @self.mcp.tool()
        async def get_or_create_tab_with_url(url: str) -> Dict[str, Any]:
            """
            Get or create a tab with the specified URL.
            
            Args:
                url: The URL to navigate to
                
            Returns:
                Information about the tab
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.get_or_create_tab_with_url({"url": url})
        
        @self.mcp.tool()
        async def find_and_click(text: str, partial_match: bool = True, auto_switch_tab: bool = True) -> Dict[str, Any]:
            """
            Find an element by text and click it.
            
            Args:
                text: The text to search for
                partial_match: Whether to use partial matching
                auto_switch_tab: Whether to auto-switch to new tab if created
                
            Returns:
                Result of the find and click operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.find_and_click_element_by_text({
                "text": text, 
                "partial_match": partial_match,
                "auto_switch_tab": auto_switch_tab
            })
        
        @self.mcp.tool()
        async def create_mask_interceptor(target_url: str) -> Dict[str, Any]:
            """
            Create a tab with data masking interceptor.
            
            Args:
                target_url: The URL to navigate to with masking
                
            Returns:
                Result of the mask interceptor creation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.create_mask_interceptor({"target_url": target_url})
        
        @self.mcp.tool()
        async def search_and_navigate(
            base_url: str, 
            search_keyword: str, 
            result_keyword: str,
            search_box_attribute: str = "placeholder", 
            search_box_value: str = "请输入您要办理的事项",
            search_button_text: str = "搜索", 
            wait_after_search: int = 2,
            partial_match: bool = True
        ) -> Dict[str, Any]:
            """
            Search for a keyword on a website and navigate to a relevant result.
            
            Args:
                base_url: The base URL of the website to search on
                search_keyword: The keyword to search for
                result_keyword: Keyword to look for in search results
                search_box_attribute: The attribute name to identify the search box (e.g., "placeholder", "name", "id")
                search_box_value: The value of the attribute to identify the search box
                search_button_text: Text on the search button
                wait_after_search: Time to wait after search (seconds)
                partial_match: Whether to use partial matching for element search
            
            Returns:
                Result of the search and navigation operation
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
                
            return await self.handler.search_and_navigate({
                "base_url": base_url,
                "search_keyword": search_keyword,
                "search_box_attribute": search_box_attribute,
                "search_box_value": search_box_value,
                "search_button_text": search_button_text,
                "result_keyword": result_keyword,
                "wait_after_search": wait_after_search,
                "partial_match": partial_match
            })
        
        # ==================== 用户交互操作 ====================
        
        @self.mcp.tool()
        async def request_user_action(
            action_type: str = "generic", 
            message: str = "请执行操作",
            description: str = "",
            options: List[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Request the user to perform an action.
            
            Args:
                action_type: Type of action (login|select|verify|input|decision)
                message: Prompt message for the user
                description: Detailed description of the action
                options: Optional list of options for the user to choose from
                
            Returns:
                Result of the user action request
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
                
            params = {
                "type": action_type,
                "message": message,
                "description": description
            }
            
            if options:
                params["options"] = options
                
            return await self.handler.request_user_action(params)
        
        @self.mcp.tool()
        async def evaluate_state(description: str = "评估当前状态") -> Dict[str, Any]:
            """
            Evaluate the current page state.
            
            Args:
                description: Description of the evaluation
                
            Returns:
                Current state information
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
            return await self.handler.evaluate_state({"description": description})
        
        # ==================== 工作流执行 ====================
        
        @self.mcp.tool()
        async def execute_workflow_step(action: str, parameters: Dict[str, Any], description: str = "") -> Dict[str, Any]:
            """
            Execute a single workflow step.
            
            Args:
                action: The action to execute
                parameters: Parameters for the action
                description: Description of the step
            
            Returns:
                Result of the step execution
            """
            if self.handler is None:
                return {"status": "error", "message": "Browser context has not been set"}
                
            # Special handling for the "done" action which might just be a marker
            if action == "done":
                return {
                    "status": "success",
                    "message": f"Workflow step completed: {description}",
                    "parameters": parameters
                }
                
            try:
                # Prepare parameters with action included for process_query
                action_params = {"action": action, **parameters}
                
                # Call process_query with the action and parameters
                result = await self.handler.process_query(action_params)
                
                # Add description to the result for better tracking
                result["step_description"] = description
                return result
            except Exception as e:
                logger.error(f"Error executing workflow step {action}: {str(e)}")
                return {
                    "status": "error", 
                    "message": f"执行操作失败: {str(e)}",
                    "step_description": description
                }
        
        @self.mcp.tool()
        async def execute_workflow(workflow_json: str) -> List[Dict[str, Any]]:
            """
            Execute an entire workflow from JSON.
            
            Args:
                workflow_json: JSON string of the workflow configuration
            
            Returns:
                List of results for each step in the workflow
            """
            if self.handler is None:
                return [{"status": "error", "message": "Browser context has not been set"}]
                
            try:
                # Parse workflow JSON
                workflow_config = json.loads(workflow_json)
                
                results = []
                
                # Get the first action in the workflow (or the specified one)
                action_id = workflow_config.get("execute_action_id")
                actions = workflow_config.get("actions", [])
                
                if not actions:
                    return [{"status": "error", "message": "No actions found in workflow"}]
                
                # Find the action to execute
                action_to_execute = None
                if action_id:
                    action_to_execute = next((a for a in actions if a.get("id") == action_id), None)
                else:
                    action_to_execute = actions[0]  # Default to first action
                
                if not action_to_execute:
                    return [{"status": "error", "message": f"Action {action_id} not found in workflow"}]
                
                logger.info(f"Executing workflow: {workflow_config.get('name', 'Unnamed workflow')}")
                logger.info(f"Selected action: {action_to_execute.get('name', 'Unnamed action')}")
                
                # Execute each step in the action
                steps = action_to_execute.get("steps", [])
                for step in steps:
                    step_id = step.get("id", "unknown")
                    action = step.get("action")
                    parameters = step.get("parameters", {})
                    description = step.get("description", "")
                    
                    logger.info(f"Executing step {step_id}: {description}")
                    
                    # Skip "done" steps as they're just markers
                    if action == "done":
                        results.append({
                            "step_id": step_id,
                            "status": "success",
                            "message": f"Workflow step {step_id} completed: {description}",
                            "parameters": parameters,
                            "description": description
                        })
                        continue
                    
                    try:
                        # Execute workflow step
                        result = await self.execute_workflow_step(action, parameters, description)
                        
                        # Add step information
                        result["step_id"] = step_id
                        results.append(result)
                        
                        # Check if step failed
                        if result.get("status") == "error":
                            logger.error(f"Step {step_id} failed: {result.get('message')}")
                            break
                    except Exception as e:
                        error_msg = f"Error executing step {step_id}: {str(e)}"
                        logger.error(error_msg)
                        results.append({
                            "step_id": step_id,
                            "status": "error",
                            "message": error_msg,
                            "description": description
                        })
                        break
                
                return results
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid workflow JSON: {str(e)}")
                return [{"status": "error", "message": f"Invalid workflow JSON: {str(e)}"}]
            except Exception as e:
                logger.error(f"Error executing workflow: {str(e)}")
                return [{"status": "error", "message": f"Error executing workflow: {str(e)}"}]
    
    def run(self, host="0.0.0.0", port=8801):
        """Run the MCP service."""
        uvicorn.run(self.mcp, host=host, port=port)

# Example of how the service can be started (not executed directly)
"""
if __name__ == "__main__":
    # In a real implementation, browser_context would be passed from outside
    service = MCPBrowserHandler()
    # service.set_browser_context(browser_context)
    service.run()
"""