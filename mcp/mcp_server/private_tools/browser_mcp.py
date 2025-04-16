from mcp.server.fastmcp import FastMCP
import sys
import uvicorn
import argparse
from typing import List, Dict, Optional, Any, Union
import json
import logging
import asyncio
import os

# Add the project root to Python path to help with imports
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/../../../"))

# Import BaseHandler and necessary components for browser automation
# Update these import paths to match your project structure
from tool_service.src.tools.handlers.base import BaseHandler  # Adjust this path to where your base.py is located
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig

# Configure logging to a file instead of stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("browser_mcp.log"),
        logging.StreamHandler()  # This will still print to stderr, not stdout
    ]
)
logger = logging.getLogger(__name__)
# Initialize FastMCP
mcp = FastMCP("Browser Automation MCP Tools")
def create_parser():
    """Create and return the argument parser for MCP Server with Browser automation."""
    parser = argparse.ArgumentParser(description='FastMCP server for Browser automation')

    parser.add_argument('--chrome_debug_port',
                        type=int,
                        default=int(os.getenv('CHROME_DEBUG_PORT', 54905)),
                        help='Chrome debug port to connect to')

    parser.add_argument('--mcp_port',
                        type=int,
                        default=int(os.getenv('MCP_PORT', 8091)),
                        help='Port to run the MCP server on')
                        
    parser.add_argument('--redirect_logs',
                        action='store_true',
                        help='Redirect stdout/stderr to files to avoid interference with MCP stdio')

    return parser

# Global browser context and handler
browser_context = None
base_handler = None

async def get_browser_handler():
    """Get or create the global browser handler instance."""
    global browser_context, base_handler
    
    if base_handler is not None:
        return base_handler
        
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Configure browser connection
        browser_config = BrowserConfig(
            cdp_url=f"http://localhost:{args.chrome_debug_port}"
        )
        
        # Create Browser instance
        browser = Browser(config=browser_config)
        
        # Create BrowserContext
        browser_context = BrowserContext(browser=browser)
        
        # Initialize session
        await browser_context._initialize_session()
        
        # Initialize base handler
        base_handler = BaseHandler(browser_context)
        
        #logger.info(f"Successfully connected to Chrome on debug port {args.chrome_debug_port}")
        return base_handler
    except Exception as e:
        logger.error(f"Failed to initialize browser handler: {str(e)}")
        raise



# Helper function to parse JSON strings from parameters
def parse_json_param(param_str):
    """Parse a JSON string parameter or return None."""
    if not param_str:
        return None
    try:
        return json.loads(param_str)
    except Exception as e:
        logger.error(f"Error parsing JSON parameter: {str(e)}")
        return None

# ==================== MCP Tool Wrappers ====================

@mcp.tool()
async def go_to_url(url: str) -> Dict[str, Any]:
    """导航到指定URL
    
    Args:
        url: 要导航到的URL
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.go_to_url({"url": url})

@mcp.tool()
async def click_element(index: int, auto_switch_tab: bool = True) -> Dict[str, Any]:
    """点击指定索引的元素
    
    Args:
        index: 元素索引
        auto_switch_tab: 如果点击后打开新标签页，是否自动切换到新标签页
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.click_element({
        "index": index,
        "auto_switch_tab": auto_switch_tab
    })

@mcp.tool()
async def input_text(index: int, text: str) -> Dict[str, Any]:
    """在指定元素中输入文本
    
    Args:
        index: 元素索引
        text: 要输入的文本
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.input_text({
        "index": index,
        "text": text
    })

@mcp.tool()
async def extract_content(goal: str) -> Dict[str, Any]:
    """从页面提取内容
    
    Args:
        goal: 提取目标描述
    
    Returns:
        提取的内容
    """
    handler = await get_browser_handler()
    return await handler.extract_content({
        "goal": goal
    })

@mcp.tool()
async def scroll(direction: str = "down", amount: str = "medium") -> Dict[str, Any]:
    """滚动页面
    
    Args:
        direction: 滚动方向，可选值："up", "down"
        amount: 滚动量，可选值："small", "medium", "large", "page"
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.scroll({
        "direction": direction,
        "amount": amount
    })

@mcp.tool()
async def wait(time: float = 2, selector: Optional[str] = None) -> Dict[str, Any]:
    """等待一段时间或元素出现
    
    Args:
        time: 等待时间（秒）
        selector: 等待的元素选择器（可选）
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    params = {"time": time}
    if selector:
        params["selector"] = selector
    return await handler.wait(params)

@mcp.tool()
async def get_tabs() -> Dict[str, Any]:
    """获取所有标签页信息
    
    Returns:
        标签页列表
    """
    handler = await get_browser_handler()
    return await handler.get_tabs({})

@mcp.tool()
async def create_tab(url: str = "about:blank") -> Dict[str, Any]:
    """创建新标签页
    
    Args:
        url: 新标签页的URL，默认为空白页
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.create_tab({"url": url})

@mcp.tool()
async def switch_tab(tab_id: str) -> Dict[str, Any]:
    """切换到指定标签页
    
    Args:
        tab_id: 标签页ID
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.switch_tab({
        "tab_id": tab_id
    })

@mcp.tool()
async def close_tab() -> Dict[str, Any]:
    """关闭当前标签页
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.close_tab({})

@mcp.tool()
async def highlight_elements(viewport_expansion: int = 500) -> Dict[str, Any]:
    """高亮可点击元素
    
    Args:
        viewport_expansion: 视口扩展像素
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.highlight_elements({
        "viewport_expansion": viewport_expansion
    })

@mcp.tool()
async def find_element_by_text(text: str, partial_match: bool = True, highlight_elements: bool = True) -> Dict[str, Any]:
    """根据文本查找元素
    
    Args:
        text: 要查找的文本
        partial_match: 是否使用部分匹配
        highlight_elements: 是否先高亮元素
    
    Returns:
        找到的元素列表
    """
    handler = await get_browser_handler()
    return await handler.find_element_by_text({
        "text": text,
        "partial_match": partial_match,
        "highlight_elements": highlight_elements
    })

@mcp.tool()
async def find_element_by_attribute(attribute: str, value: str, partial_match: bool = True, highlight_elements: bool = True) -> Dict[str, Any]:
    """根据属性查找元素
    
    Args:
        attribute: 属性名
        value: 属性值
        partial_match: 是否使用部分匹配
        highlight_elements: 是否先高亮元素
    
    Returns:
        找到的元素列表
    """
    handler = await get_browser_handler()
    return await handler.find_element_by_attribute({
        "attribute": attribute,
        "value": value,
        "partial_match": partial_match,
        "highlight_elements": highlight_elements
    })

@mcp.tool()
async def inject_script(script: str) -> Dict[str, Any]:
    """注入JavaScript脚本到页面
    
    Args:
        script: JavaScript脚本内容
    
    Returns:
        执行结果
    """
    handler = await get_browser_handler()
    return await handler.inject_script({
        "script": script
    })

@mcp.tool()
async def input_by_selector(selector: str, text: str) -> Dict[str, Any]:
    """通过选择器在指定元素中输入文本
    
    Args:
        selector: CSS选择器或XPath
        text: 要输入的文本
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.input_by_selector({
        "selector": selector,
        "text": text
    })

@mcp.tool()
async def get_or_create_tab_with_url(url: str) -> Dict[str, Any]:
    """获取或创建包含指定URL的标签页
    
    Args:
        url: 要查找或导航的URL
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.get_or_create_tab_with_url({
        "url": url
    })

@mcp.tool()
async def search_and_navigate(base_url: str, search_keyword: str, result_keyword: str, 
                            search_box_attribute: str = "placeholder", 
                            search_box_value: str = "请输入您要办理的事项",
                            search_button_text: str = "搜索",
                            wait_after_search: float = 2,
                            partial_match: bool = True) -> Dict[str, Any]:
    """在网站上搜索关键词并导航到相关结果
    
    Args:
        base_url: 要搜索的网站URL
        search_keyword: 搜索关键词
        result_keyword: 结果页面中要查找的关键词
        search_box_attribute: 搜索框的属性名称
        search_box_value: 搜索框的属性值
        search_button_text: 搜索按钮的文本
        wait_after_search: 搜索后等待时间（秒）
        partial_match: 是否使用部分匹配
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.search_and_navigate({
        "base_url": base_url,
        "search_keyword": search_keyword,
        "result_keyword": result_keyword,
        "search_box_attribute": search_box_attribute,
        "search_box_value": search_box_value,
        "search_button_text": search_button_text,
        "wait_after_search": wait_after_search,
        "partial_match": partial_match
    })

@mcp.tool()
async def find_and_click_element_by_text(text: str, partial_match: bool = True, auto_switch_tab: bool = True) -> Dict[str, Any]:
    """根据文本查找并点击元素
    
    Args:
        text: 要查找的文本
        partial_match: 是否使用部分匹配
        auto_switch_tab: 如果点击后打开新标签页，是否自动切换到新标签页
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.find_and_click_element_by_text({
        "text": text,
        "partial_match": partial_match,
        "auto_switch_tab": auto_switch_tab
    })

@mcp.tool()
async def create_mask_interceptor(target_url: str) -> Dict[str, Any]:
    """创建带有数据遮罩的标签页
    
    Args:
        target_url: 要导航到的URL
    
    Returns:
        操作结果
    """
    handler = await get_browser_handler()
    return await handler.create_mask_interceptor({
        "target_url": target_url
    })

@mcp.tool()
async def request_user_action(type: str = "generic", message: str = "请执行操作", 
                            description: str = "", options: List[str] = None) -> Dict[str, Any]:
    """请求用户手动执行操作
    
    Args:
        type: 交互类型 (login|select|verify|input|decision)
        message: 给用户的提示消息
        description: 详细说明
        options: 可选的选项列表
    
    Returns:
        操作结果
    """
    if options is None:
        options = []
    
    handler = await get_browser_handler()
    return await handler.request_user_action({
        "type": type,
        "message": message,
        "description": description,
        "options": options
    })

@mcp.tool()
async def evaluate_state(description: str = "评估当前状态") -> Dict[str, Any]:
    """评估当前页面状态
    
    Args:
        description: 状态描述
    
    Returns:
        当前页面状态
    """
    handler = await get_browser_handler()
    return await handler.evaluate_state({
        "description": description
    })

async def cleanup():
    """清理资源"""
    global base_handler
    if base_handler:
        try:
            await base_handler.cleanup()
            #logger.info("Successfully cleaned up browser resources")
        except Exception as e:
            logger.error(f"Error cleaning up browser resources: {str(e)}")


def main():
    """入口点"""
    parser = create_parser()
    args = parser.parse_args()
    """
    # Redirect stdout and stderr to avoid interference with MCP's stdio transport
    if args.redirect_logs:
        sys.stdout = open('mcp_stdout.log', 'w')
        sys.stderr = open('mcp_stderr.log', 'w')
    
    # 初始化浏览器处理器
    try:
        asyncio.run(go_to_url("https://www.baidu.com"))
        #asyncio.run(create_tab("https://www.baidu.com"))
        logger.info("Successfully initialized browser handler")
    except Exception as e:
        logger.error(f"Failed to initialize browser handler: {str(e)}")
        return

    # 启动MCP服务器
    logger.info(f"Starting Browser MCP Server on port {args.mcp_port} ...")
    
    # 注册清理函数
    import atexit
    atexit.register(lambda: asyncio.run(cleanup()))
    """
    # 使用stdio作为传输方式
    mcp.run(transport='stdio')

if __name__ == "__main__":
    # 启动MCP服务器
    main()