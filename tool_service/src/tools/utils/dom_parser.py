# tool_service/src/tools/utils/dom_parser.py
from typing import Dict, Any, List, Optional, Union
import logging
import json
from dataclasses import dataclass, field
import asyncio
import time

logger = logging.getLogger(__name__)

@dataclass
class ViewportInfo:
    """表示视口信息"""
    width: int
    height: int

@dataclass
class CoordinateSet:
    """表示坐标集合"""
    left: float
    top: float
    right: float
    bottom: float
    width: float
    height: float

# 基础节点类，删除默认参数
@dataclass
class DOMNode:
    """DOM节点基类"""
    type: str
    # 移除有默认值的参数，在子类中定义
    # is_visible: bool = True
    # parent: Optional['DOMElementNode'] = None

# 文本节点类
@dataclass
class DOMTextNode:
    """DOM文本节点"""
    type: str = "TEXT_NODE"
    text: str = ""  # 提供默认值，避免参数顺序问题
    is_visible: bool = True
    parent: Optional['DOMElementNode'] = None
    
    def has_parent_with_highlight_index(self) -> bool:
        """检查是否有带有highlight_index的父节点"""
        current = self.parent
        while current is not None:
            if current.highlight_index is not None:
                return True
            current = current.parent
        return False
    
    def is_parent_in_viewport(self) -> bool:
        """检查父节点是否在视口内"""
        if self.parent is None:
            return False
        return self.parent.is_in_viewport
    
    def is_parent_top_element(self) -> bool:
        """检查父节点是否是顶层元素"""
        if self.parent is None:
            return False
        return self.parent.is_top_element

# 元素节点类
@dataclass
class DOMElementNode:
    """DOM元素节点"""
    type: str = "ELEMENT_NODE"
    tag_name: str = "div"  # 提供默认值
    # 其他可选参数
    id: Optional[str] = None
    class_name: Optional[str] = None
    xpath: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List[Union[DOMTextNode, 'DOMElementNode']] = field(default_factory=list)
    text: Optional[str] = None
    is_visible: bool = True
    is_interactive: bool = False
    is_top_element: bool = False
    is_in_viewport: bool = False
    shadow_root: bool = False
    highlight_index: Optional[int] = None
    viewport_coordinates: Optional[CoordinateSet] = None
    page_coordinates: Optional[CoordinateSet] = None
    viewport_info: Optional[ViewportInfo] = None
    parent: Optional['DOMElementNode'] = None
    
    def __repr__(self) -> str:
        """元素字符串表示"""
        attrs = []
        if self.id:
            attrs.append(f'id="{self.id}"')
        if self.class_name:
            attrs.append(f'class="{self.class_name}"')
        
        attr_str = " ".join(attrs)
        
        flags = []
        if self.is_interactive:
            flags.append("interactive")
        if self.is_top_element:
            flags.append("top")
        if not self.is_visible:
            flags.append("hidden")
        if self.shadow_root:
            flags.append("shadow-root")
        if self.highlight_index is not None:
            flags.append(f"highlight:{self.highlight_index}")
        if self.is_in_viewport:
            flags.append("in-viewport")
        
        flags_str = f" [{', '.join(flags)}]" if flags else ""
        
        return f"<{self.tag_name} {attr_str}{flags_str}>"
    
    def get_all_text_till_next_interactive(self, max_depth: int = -1) -> str:
        """获取直到下一个交互元素的所有文本"""
        text_parts = []

        def collect_text(node: Union[DOMTextNode, 'DOMElementNode'], current_depth: int) -> None:
            if max_depth != -1 and current_depth > max_depth:
                return

            # 如果遇到有highlight_index的元素（除了当前元素），则跳过该分支
            if isinstance(node, DOMElementNode) and node != self and node.highlight_index is not None:
                return

            if isinstance(node, DOMTextNode):
                text_parts.append(node.text)
            elif isinstance(node, DOMElementNode):
                for child in node.children:
                    collect_text(child, current_depth + 1)

        collect_text(self, 0)
        return '\n'.join(text_parts).strip()
    
    def clickable_elements_to_string(self, include_attributes: List[str] = None) -> str:
        """将可点击元素转换为字符串形式"""
        formatted_text = []

        def process_node(node: Union[DOMTextNode, 'DOMElementNode'], depth: int) -> None:
            if isinstance(node, DOMElementNode):
                # 处理带有highlight_index的元素
                if node.highlight_index is not None:
                    attributes_str = ''
                    text = node.get_all_text_till_next_interactive()
                    if include_attributes:
                        attributes = list(
                            set(
                                [
                                    str(value)
                                    for key, value in node.attributes.items()
                                    if key in include_attributes and value != node.tag_name
                                ]
                            )
                        )
                        if text in attributes:
                            attributes.remove(text)
                        attributes_str = ';'.join(attributes)
                    line = f'[{node.highlight_index}]<{node.tag_name} '
                    if attributes_str:
                        line += f'{attributes_str}'
                    if text:
                        if attributes_str:
                            line += f'>{text}'
                        else:
                            line += f'{text}'
                    line += '/>'
                    formatted_text.append(line)

                # 继续处理子节点
                for child in node.children:
                    process_node(child, depth + 1)

            elif isinstance(node, DOMTextNode):
                # 添加没有高亮父级的可见文本节点
                if not node.has_parent_with_highlight_index() and node.is_visible:
                    formatted_text.append(f'{node.text}')

        process_node(self, 0)
        return '\n'.join(formatted_text)
    
    def get_file_upload_element(self, check_siblings: bool = True) -> Optional['DOMElementNode']:
        """查找文件上传元素"""
        # 检查当前元素是否是文件输入框
        if self.tag_name == 'input' and self.attributes.get('type') == 'file':
            return self

        # 检查子元素
        for child in self.children:
            if isinstance(child, DOMElementNode):
                result = child.get_file_upload_element(check_siblings=False)
                if result:
                    return result

        # 仅对初始调用检查兄弟元素
        if check_siblings and self.parent:
            for sibling in self.parent.children:
                if sibling is not self and isinstance(sibling, DOMElementNode):
                    result = sibling.get_file_upload_element(check_siblings=False)
                    if result:
                        return result

        return None

class DOMParser:
    """
    DOM解析器：用于提取、分析和操作网页DOM元素的通用工具
    
    基于buildDomTree.js的实现，整合了传入的dom相关代码，
    提供了一套统一的接口来处理不同网站的DOM结构。
    """
    
    @staticmethod
    async def extract_dom_elements(session, highlight_elements=False, viewport_expansion=0, focus_highlight_index=-1, debug=False):
        """
        提取页面DOM元素（实现原_get_dom_elements功能，且更加通用）
        
        Args:
            session: 浏览器会话对象
            highlight_elements: 是否高亮元素
            viewport_expansion: 视口扩展范围（像素）
            focus_highlight_index: 聚焦高亮的元素索引
            
        Returns:
            DOM元素树结构
        """
        try:
            # 引入完整版buildDomTree.js
            build_dom_tree_js = """
            (
              args = {
                doHighlightElements: arguments[0],
                focusHighlightIndex: arguments[1],
                viewportExpansion: arguments[2],
                debugMode: false,
              }
            ) => {
              const { doHighlightElements, focusHighlightIndex, viewportExpansion, debugMode } = args;
              let highlightIndex = 0; // Reset highlight index
              
              // DOM解析逻辑...
              // 这里是buildDomTree.js的完整内容
              
              // 简化版实现，用于示例
              function buildDomTree(node) {
                // 简化的DOM树构建逻辑
                const elements = [];
                
                function processNode(el) {
                  if (!el) return null;
                  
                  // 处理元素节点
                  if (el.nodeType === Node.ELEMENT_NODE) {
                    const rect = el.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    const isInteractive = el.tagName.toLowerCase() === 'a' || 
                                         el.tagName.toLowerCase() === 'button' ||
                                         el.onclick !== null;
                    
                    // 获取XPath
                    let xpath = '';
                    let currentEl = el;
                    while (currentEl && currentEl !== document.body) {
                      const index = Array.from(currentEl.parentNode.children)
                                     .filter(child => child.tagName === currentEl.tagName)
                                     .indexOf(currentEl) + 1;
                      xpath = `/${currentEl.tagName.toLowerCase()}[${index}]${xpath}`;
                      currentEl = currentEl.parentNode;
                    }
                    xpath = `/body${xpath}`;
                    
                    const nodeData = {
                      type: 'ELEMENT_NODE',
                      tagName: el.tagName.toLowerCase(),
                      attributes: {},
                      isVisible: isVisible,
                      isInteractive: isInteractive,
                      xpath: xpath,
                      children: []
                    };
                    
                    // 获取属性
                    Array.from(el.attributes).forEach(attr => {
                      nodeData.attributes[attr.name] = attr.value;
                    });
                    
                    // 如果是交互元素，添加高亮索引
                    if (isVisible && isInteractive) {
                      nodeData.highlightIndex = highlightIndex++;
                    }
                    
                    // 处理子节点
                    Array.from(el.childNodes).forEach(child => {
                      const childData = processNode(child);
                      if (childData) {
                        nodeData.children.push(childData);
                      }
                    });
                    
                    return nodeData;
                  }
                  
                  // 处理文本节点
                  else if (el.nodeType === Node.TEXT_NODE && el.textContent.trim()) {
                    return {
                      type: 'TEXT_NODE',
                      text: el.textContent.trim(),
                      isVisible: true
                    };
                  }
                  
                  return null;
                }
                
                return processNode(document.body);
              }
              
              return {
                rootId: 'root',
                map: { 'root': buildDomTree(document.body) }
              };
            };
            """
            
            # 执行DOM解析脚本获取页面元素
            dom_result = await session.execute_script(build_dom_tree_js, [highlight_elements, focus_highlight_index, viewport_expansion])
            if debug:
                try:
                    import os
                    import json
                    from datetime import datetime
                    
                    # Create debug directory if it doesn't exist
                    debug_dir = os.path.join(os.getcwd(), "debug_dom")
                    os.makedirs(debug_dir, exist_ok=True)
                    
                    # Get current page URL for filename
                    current_url = await session.execute_script("return window.location.href")
                    url_filename = "".join(c if c.isalnum() else "_" for c in current_url)[:50]
                    
                    # Create filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{url_filename}.json"
                    filepath = os.path.join(debug_dir, filename)
                    
                    # Save DOM data
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump({
                            "url": current_url,
                            "timestamp": timestamp,
                            "dom_result": dom_result
                        }, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"Saved DOM debug information to {filepath}")
                except Exception as debug_error:
                    logger.error(f"Failed to save DOM debug information: {str(debug_error)}")
            # 从JavaScript返回的结果中提取DOM树
            root_id = dom_result.get('rootId')
            dom_map = dom_result.get('map', {})
            
            # 构建DOM元素树
            element_tree = None
            element_map = {}
            
            # 帮助函数：递归构建元素树
            def build_element_tree(node_id):
                node_data = dom_map.get(node_id)
                if not node_data:
                    return None
                
                # 处理文本节点
                if node_data.get('type') == 'TEXT_NODE':
                    text_node = DOMTextNode(
                        text=node_data.get('text', ''),
                        is_visible=node_data.get('isVisible', True),
                        parent=None
                    )
                    element_map[node_id] = text_node
                    return text_node
                
                # 处理元素节点
                element = DOMElementNode(
                    tag_name=node_data.get('tagName', 'div'),
                    id=node_data.get('attributes', {}).get('id'),
                    class_name=node_data.get('attributes', {}).get('class'),
                    xpath=node_data.get('xpath'),
                    attributes=node_data.get('attributes', {}),
                    text=node_data.get('innerText', ''),
                    is_visible=node_data.get('isVisible', True),
                    is_interactive=node_data.get('isInteractive', False),
                    is_top_element=node_data.get('isTopElement', False),
                    is_in_viewport=node_data.get('isInViewport', False),
                    shadow_root=node_data.get('shadowRoot', False),
                    highlight_index=node_data.get('highlightIndex'),
                    children=[],
                    parent=None
                )
                
                element_map[node_id] = element
                
                # 处理子节点
                for child_id in node_data.get('children', []):
                    child = build_element_tree(child_id)
                    if child:
                        child.parent = element
                        element.children.append(child)
                
                return element
            
            # 构建元素树，从根节点开始
            if root_id:
                element_tree = build_element_tree(root_id)
            
            # 汇总交互式元素
            interactive_elements = []
            for node_id, node in dom_map.items():
                if node.get('isInteractive') and node.get('highlightIndex') is not None:
                    element_data = element_map.get(node_id)
                    if element_data:
                        interactive_elements.append(element_data)
            
            # 排序交互式元素，按highlight_index
            interactive_elements.sort(key=lambda e: e.highlight_index if e.highlight_index is not None else 999999)
            
            return {
                'url': await session.execute_script('window.location.href'),
                'title': await session.execute_script('document.title'),
                'element_tree': element_tree,
                'interactive_elements': interactive_elements,
                'dom_map': dom_map  # 保留原始数据，以备后用
            }
        except Exception as e:
            logger.error(f"提取DOM元素失败: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'error': str(e)}

    @staticmethod
    async def capture_page_elements(session, debug=True):
        """
        Capture all visible text and clickable elements on the page
        
        Args:
            session: Browser session object
            debug: Whether to save debug information
            
        Returns:
            Dictionary with text content and clickable elements
        """
        try:
            # Simple script to extract basic page information
            js_script = """
            () => {
                // Get page info
                const pageInfo = {
                    url: window.location.href,
                    title: document.title,
                    bodyText: document.body.innerText
                };
                
                // Get all links
                const links = [];
                const allLinks = document.querySelectorAll('a');
                for (let i = 0; i < allLinks.length; i++) {
                    const link = allLinks[i];
                    if (link.offsetWidth > 0 && link.offsetHeight > 0) { // Only visible links
                        links.push({
                            text: link.innerText.trim(),
                            href: link.href,
                            id: link.id,
                            className: link.className
                        });
                    }
                }
                
                // Get all buttons
                const buttons = [];
                const allButtons = document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]');
                for (let i = 0; i < allButtons.length; i++) {
                    const button = allButtons[i];
                    if (button.offsetWidth > 0 && button.offsetHeight > 0) { // Only visible buttons
                        buttons.push({
                            text: button.innerText.trim() || button.value,
                            id: button.id,
                            className: button.className,
                            type: button.type
                        });
                    }
                }
                
                // All divs with click handlers
                const clickableDivs = [];
                const allDivs = document.querySelectorAll('div');
                for (let i = 0; i < allDivs.length; i++) {
                    const div = allDivs[i];
                    if (div.onclick || div.getAttribute('onclick') || 
                        div.classList.contains('clickable') || 
                        div.style.cursor === 'pointer') {
                        if (div.offsetWidth > 0 && div.offsetHeight > 0) { // Only visible divs
                            clickableDivs.push({
                                text: div.innerText.trim(),
                                id: div.id,
                                className: div.className
                            });
                        }
                    }
                }
                
                // Get all text content by element
                const textElements = [];
                function processNode(node, level = 0) {
                    if (node.nodeType === Node.TEXT_NODE) {
                        const text = node.textContent.trim();
                        if (text) {
                            // Check if text node's parent element is visible
                            const parentEl = node.parentElement;
                            if (parentEl && parentEl.offsetWidth > 0 && parentEl.offsetHeight > 0) {
                                textElements.push({
                                    text: text,
                                    level: level,
                                    tag: parentEl.tagName.toLowerCase(),
                                    id: parentEl.id,
                                    className: parentEl.className
                                });
                            }
                        }
                    } else if (node.nodeType === Node.ELEMENT_NODE) {
                        // Process child nodes
                        for (let i = 0; i < node.childNodes.length; i++) {
                            processNode(node.childNodes[i], level + 1);
                        }
                    }
                }
                
                processNode(document.body);
                
                return {
                    pageInfo: pageInfo,
                    links: links,
                    buttons: buttons,
                    clickableDivs: clickableDivs,
                    textElements: textElements
                };
            }
            """
            
            page_elements = await session.execute_script(js_script)
            
            # Save debugging information if enabled
            if debug:
                try:
                    import os
                    import json
                    from datetime import datetime
                    
                    # Create debug directory if it doesn't exist
                    debug_dir = os.path.join(os.getcwd(), "debug_dom")
                    os.makedirs(debug_dir, exist_ok=True)
                    
                    # Get current page URL for filename
                    current_url = page_elements["pageInfo"]["url"] if page_elements and "pageInfo" in page_elements else "unknown"
                    url_filename = "".join(c if c.isalnum() else "_" for c in current_url)[:50]
                    
                    # Create filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{url_filename}_elements.json"
                    filepath = os.path.join(debug_dir, filename)
                    
                    # Save elements data
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump({
                            "timestamp": timestamp,
                            "page_elements": page_elements
                        }, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"Saved page elements to {filepath}")
                except Exception as debug_error:
                    logger.error(f"Failed to save page elements: {str(debug_error)}")
            
            return page_elements
        except Exception as e:
            logger.error(f"Failed to capture page elements: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    async def find_interactive_elements(session, text_filter=None, tag_filter=None, highlight=True):
        """
        查找页面中的交互元素
        
        Args:
            session: 浏览器会话对象
            text_filter: 文本过滤条件
            tag_filter: 标签过滤条件
            highlight: 是否高亮元素
            
        Returns:
            交互元素列表
        """
        try:
            # 获取页面DOM元素
            dom_result = await DOMParser.extract_dom_elements(session, highlight_elements=highlight)
            
            if 'error' in dom_result:
                return {'error': dom_result['error']}
            
            # 过滤交互元素
            interactive_elements = dom_result.get('interactive_elements', [])
            
            filtered_elements = []
            for element in interactive_elements:
                # 应用文本过滤
                if text_filter and element.text:
                    if isinstance(text_filter, str):
                        if text_filter.lower() not in element.text.lower():
                            continue
                    elif callable(text_filter):
                        if not text_filter(element.text):
                            continue
                
                # 应用标签过滤
                if tag_filter:
                    if isinstance(tag_filter, str):
                        if element.tag_name != tag_filter:
                            continue
                    elif isinstance(tag_filter, list):
                        if element.tag_name not in tag_filter:
                            continue
                    elif callable(tag_filter):
                        if not tag_filter(element.tag_name):
                            continue
                
                filtered_elements.append(element)
            
            return {
                'elements': filtered_elements,
                'count': len(filtered_elements)
            }
        except Exception as e:
            logger.error(f"查找交互元素失败: {str(e)}")
            return {'error': str(e)}
    
    # Enhanced find_element_by_text method for dom_parser.py
    @staticmethod
    async def find_element_by_text(session, text, exact_match=False, highlight=True):
        """
        Enhanced method to find elements by text content
        """
        try:
            # Create a more robust JavaScript function based on complete-page-analyzer.py approach
            js_script = """
            (text, exactMatch) => {
                const textToFind = text;
                const potentialElements = [];
                
                // First approach: direct text search with multiple tag targets
                const directTextSearch = () => {
                    // Common interactive elements
                    const interactiveElements = document.querySelectorAll('a, button, [role="button"], .navbar-first-menu, li, div.clickable, [class*="menu-item"], [onclick], [class*="btn"]');
                    
                    for (const element of interactiveElements) {
                        if (!element.offsetWidth || !element.offsetHeight) continue; // Skip invisible elements
                        
                        const elementText = element.innerText || element.textContent;
                        if (!elementText) continue;
                        
                        const textMatches = exactMatch 
                            ? elementText.trim() === textToFind 
                            : elementText.includes(textToFind);
                        
                        if (textMatches) {
                            // Get computed style to check visibility
                            const style = window.getComputedStyle(element);
                            if (style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0) {
                                // Create detailed element info
                                const rect = element.getBoundingClientRect();
                                
                                potentialElements.push({
                                    element: element,
                                    tagName: element.tagName.toLowerCase(),
                                    id: element.id || null,
                                    className: element.className || null,
                                    text: elementText.trim(),
                                    isVisible: true,
                                    rect: {
                                        top: rect.top,
                                        left: rect.left,
                                        width: rect.width,
                                        height: rect.height
                                    },
                                    attributes: {}
                                });
                            }
                        }
                    }
                };
                
                };
                
                // Helper function to check if element is interactive
                function isInteractive(element) {
                    const tag = element.tagName.toLowerCase();
                    if (['a', 'button', 'input', 'select', 'textarea'].includes(tag)) return true;
                    if (element.getAttribute('role') === 'button') return true;
                    if (element.onclick) return true;
                    if (element.className && (
                        element.className.includes('btn') || 
                        element.className.includes('button') ||
                        element.className.includes('link') ||
                        element.className.includes('menu') ||
                        element.className.includes('nav')
                    )) return true;
                    
                    const style = window.getComputedStyle(element);
                    return style.cursor === 'pointer';
                }
                
                // Run both search approaches
                directTextSearch();
                textNodeSearch();
                
                // Sort elements by visibility and position (top to bottom, left to right)
                potentialElements.sort((a, b) => {
                    // First sort by top position
                    if (a.rect.top !== b.rect.top) {
                        return a.rect.top - b.rect.top;
                    }
                    // Then by left position
                    return a.rect.left - b.rect.left;
                });
                
                // Highlight the element if requested
                if (potentialElements.length > 0 && ${highlight}) {
                    const element = potentialElements[0].element;
                    const rect = element.getBoundingClientRect();
                    
                    // Create highlight container if it doesn't exist
                    let container = document.getElementById("highlight-container");
                    if (!container) {
                        container = document.createElement("div");
                        container.id = "highlight-container";
                        container.style.position = "fixed";
                        container.style.pointerEvents = "none";
                        container.style.top = "0";
                        container.style.left = "0";
                        container.style.width = "100%";
                        container.style.height = "100%";
                        container.style.zIndex = "9999";
                        document.body.appendChild(container);
                    }
                    
                    // Create highlight box
                    const highlight = document.createElement("div");
                    highlight.style.position = "fixed";
                    highlight.style.border = "2px solid #FF0000";
                    highlight.style.backgroundColor = "rgba(255, 0, 0, 0.2)";
                    highlight.style.top = rect.top + "px";
                    highlight.style.left = rect.left + "px";
                    highlight.style.width = rect.width + "px";
                    highlight.style.height = rect.height + "px";
                    
                    // Create label
                    const label = document.createElement("div");
                    label.style.position = "fixed";
                    label.style.top = (rect.top - 20) + "px";
                    label.style.left = rect.left + "px";
                    label.style.backgroundColor = "#FF0000";
                    label.style.color = "#FFFFFF";
                    label.style.padding = "2px 5px";
                    label.style.borderRadius = "3px";
                    label.textContent = "Found: " + text;
                    
                    container.appendChild(highlight);
                    container.appendChild(label);
                }
                
                return potentialElements;
            }
            """
            
            # Execute the script to find elements
            elements_found = await session.execute_script(js_script, [text, exact_match])
            
            if not elements_found or len(elements_found) == 0:
                logger.warning(f"No elements found with text: {text}")
                return []
            
            # Convert JavaScript results to Python DOM elements
            dom_elements = []
            for element_data in elements_found:
                element = DOMElementNode(
                    tag_name=element_data.get('tagName', 'div'),
                    id=element_data.get('id'),
                    class_name=element_data.get('className'),
                    text=element_data.get('text', ''),
                    is_visible=element_data.get('isVisible', True),
                    is_interactive=True
                )
                
                # Convert rectangle information to viewport coordinates
                rect = element_data.get('rect', {})
                if rect:
                    element.viewport_coordinates = CoordinateSet(
                        left=rect.get('left', 0),
                        top=rect.get('top', 0),
                        right=rect.get('left', 0) + rect.get('width', 0),
                        bottom=rect.get('top', 0) + rect.get('height', 0),
                        width=rect.get('width', 0),
                        height=rect.get('height', 0)
                    )
                
                dom_elements.append(element)
            
            return dom_elements
            
        except Exception as e:
            logger.error(f"通过文本查找元素失败: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    @staticmethod
    async def find_element_by_selector(session, selector, highlight=True):
        """
        通过CSS选择器查找元素
        
        Args:
            session: 浏览器会话对象
            selector: CSS选择器
            highlight: 是否高亮元素
            
        Returns:
            匹配的元素
        """
        try:
            # 使用session的查询选择器功能
            element = await session.query_selector(selector)
            
            if not element:
                return None
            
            # 获取元素属性
            element_info = await session.execute_script("""
            (element) => {
                if (!element) return null;
                
                // 获取元素边界
                const rect = element.getBoundingClientRect();
                
                // 获取所有属性
                const attributes = {};
                for (const attr of element.attributes) {
                    attributes[attr.name] = attr.value;
                }
                
                // 检查元素可见性
                const style = window.getComputedStyle(element);
                const isVisible = (
                    rect.width > 0 && 
                    rect.height > 0 && 
                    style.display !== 'none' && 
                    style.visibility !== 'hidden' && 
                    parseFloat(style.opacity) > 0
                );
                
                // 构建XPath
                function getXPath(element) {
                    const segments = [];
                    let current = element;
                    
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let index = 0;
                        let sibling = current.previousSibling;
                        
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && 
                                sibling.tagName === current.tagName) {
                                index++;
                            }
                            sibling = sibling.previousSibling;
                        }
                        
                        const tagName = current.tagName.toLowerCase();
                        const segment = index > 0 ? `${tagName}[${index + 1}]` : tagName;
                        segments.unshift(segment);
                        
                        current = current.parentNode;
                        if (current === document.body) break;
                    }
                    
                    return '/html/body/' + segments.join('/');
                }
                
                return {
                    tagName: element.tagName.toLowerCase(),
                    id: element.id || null,
                    className: element.className || null,
                    attributes: attributes,
                    text: element.innerText?.trim() || null,
                    isVisible: isVisible,
                    xpath: getXPath(element),
                    rect: {
                        left: rect.left,
                        top: rect.top,
                        right: rect.right,
                        bottom: rect.bottom,
                        width: rect.width,
                        height: rect.height
                    }
                };
            }
            """, element)
            
            if not element_info:
                return None
            
            # 如果需要高亮元素
            if highlight:
                await session.execute_script("""
                (selector) => {
                    const element = document.querySelector(selector);
                    if (!element) return;
                    
                    // 创建高亮容器
                    let container = document.getElementById("playwright-highlight-container");
                    if (!container) {
                        container = document.createElement("div");
                        container.id = "playwright-highlight-container";
                        container.style.position = "fixed";
                        container.style.pointerEvents = "none";
                        container.style.top = "0";
                        container.style.left = "0";
                        container.style.width = "100%";
                        container.style.height = "100%";
                        container.style.zIndex = "2147483647";
                        document.body.appendChild(container);
                    }
                    
                    // 获取元素位置
                    const rect = element.getBoundingClientRect();
                    
                    // 创建高亮覆盖层
                    const overlay = document.createElement("div");
                    overlay.style.position = "fixed";
                    overlay.style.border = "2px solid #FF0000";
                    overlay.style.backgroundColor = "#FF00001A";
                    overlay.style.pointerEvents = "none";
                    overlay.style.boxSizing = "border-box";
                    
                    overlay.style.top = `${rect.top}px`;
                    overlay.style.left = `${rect.left}px`;
                    overlay.style.width = `${rect.width}px`;
                    overlay.style.height = `${rect.height}px`;
                    
                    // 创建标签
                    const label = document.createElement("div");
                    label.style.position = "fixed";
                    label.style.background = "#FF0000";
                    label.style.color = "white";
                    label.style.padding = "1px 4px";
                    label.style.borderRadius = "4px";
                    label.style.fontSize = "12px";
                    label.textContent = "SELECT";
                    
                    // 放置标签
                    const labelWidth = 50;
                    const labelHeight = 16;
                    
                    let labelTop = rect.top + 2;
                    let labelLeft = rect.left + rect.width - labelWidth - 2;
                    
                    if (rect.width < labelWidth + 4 || rect.height < labelHeight + 4) {
                        labelTop = rect.top - labelHeight - 2;
                        labelLeft = rect.left + rect.width - labelWidth;
                    }
                    
                    label.style.top = `${labelTop}px`;
                    label.style.left = `${labelLeft}px`;
                    
                    // 添加到容器
                    container.appendChild(overlay);
                    container.appendChild(label);
                }
                """, selector)
            
            # 创建DOM元素对象
            rect = element_info.get('rect', {})
            coordinates = None
            if rect:
                coordinates = CoordinateSet(
                    left=rect.get('left', 0),
                    top=rect.get('top', 0),
                    right=rect.get('right', 0),
                    bottom=rect.get('bottom', 0),
                    width=rect.get('width', 0),
                    height=rect.get('height', 0)
                )
            
            return DOMElementNode(
                tag_name=element_info.get('tagName', 'div'),
                id=element_info.get('id'),
                class_name=element_info.get('className'),
                xpath=element_info.get('xpath'),
                attributes=element_info.get('attributes', {}),
                text=element_info.get('text'),
                is_visible=element_info.get('isVisible', True),
                is_interactive=True,  # 假设通过选择器选择的元素是交互式的
                is_top_element=True,  # 假设通过选择器选择的元素是顶层的
                is_in_viewport=True,  # 假设通过选择器选择的元素在视口内
                viewport_coordinates=coordinates
            )
        except Exception as e:
            logger.error(f"通过选择器查找元素失败: {str(e)}")
            return None
    
    @staticmethod
    def get_element_selector(element):
        """
        为元素生成最佳CSS选择器
        
        Args:
            element: DOM元素
            
        Returns:
            CSS选择器
        """
        if not element:
            return None
        
        # 优先使用ID
        if element.id:
            return f"#{element.id}"
        
        # 使用特定属性
        if element.attributes:
            for attr_name in ['data-testid', 'data-id', 'name', 'aria-label']:
                if attr_name in element.attributes and element.attributes[attr_name]:
                    value = element.attributes[attr_name].replace('"', '\\"')
                    return f"{element.tag_name}[{attr_name}=\"{value}\"]"
        
        # 使用类
        if element.class_name:
            classes = element.class_name.split()
            if classes:
                # 使用第一个类
                return f"{element.tag_name}.{classes[0]}"
        
        # 使用XPath作为最后手段
        if element.xpath:
            return element.xpath
        
        # 默认返回标签选择器
        return element.tag_name
    
    @staticmethod
    async def clear_highlights(session):
        """
        清除页面上的所有高亮效果
        
        Args:
            session: 浏览器会话对象
            
        Returns:
            是否成功清除
        """
        try:
            await session.execute_script("""
            () => {
                const container = document.getElementById("playwright-highlight-container");
                if (container) {
                    container.remove();
                    return true;
                }
                return false;
            }
            """)
            return True
        except Exception as e:
            logger.error(f"清除高亮效果失败: {str(e)}")
            return False
    
    @staticmethod
    async def get_page_metadata(session):
        """
        获取页面元数据信息
        
        Args:
            session: 浏览器会话对象
            
        Returns:
            页面元数据
        """
        try:
            metadata = await session.execute_script("""
            () => {
                // 获取URL和标题
                const url = window.location.href;
                const title = document.title;
                
                // 获取meta标签
                const metaTags = {};
                const metaElements = document.querySelectorAll('meta');
                for (const meta of metaElements) {
                    const name = meta.getAttribute('name') || meta.getAttribute('property');
                    const content = meta.getAttribute('content');
                    if (name && content) {
                        metaTags[name] = content;
                    }
                }
                
                // 获取favicon
                let favicon = null;
                const faviconElement = document.querySelector('link[rel="icon"], link[rel="shortcut icon"]');
                if (faviconElement) {
                    favicon = faviconElement.href;
                }
                
                // 获取Open Graph数据
                const openGraph = {};
                for (const meta of document.querySelectorAll('meta[property^="og:"]')) {
                    const property = meta.getAttribute('property');
                    const content = meta.getAttribute('content');
                    if (property && content) {
                        openGraph[property.substring(3)] = content;
                    }
                }
                
                // 获取视口信息
                const viewport = {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY
                };
                
                return {
                    url,
                    title,
                    metaTags,
                    favicon,
                    openGraph,
                    viewport
                };
            }
            """)
            
            return metadata
        except Exception as e:
            logger.error(f"获取页面元数据失败: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    async def click_element(session, element, wait_time=2):
        """
        点击元素
        
        Args:
            session: 浏览器会话对象
            element: 要点击的DOM元素
            wait_time: 点击后等待时间
            
        Returns:
            是否成功点击
        """
        try:
            if not element:
                return False
            
            # 获取元素选择器
            selector = DOMParser.get_element_selector(element)
            if not selector:
                return False
            
            # 尝试使用XPath
            if selector.startswith('/'):
                result = await session.execute_script(f"""
                () => {{
                    try {{
                        const element = document.evaluate("{selector}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        if (!element) return false;
                        
                        // 滚动到视图
                        element.scrollIntoView({{ behavior: 'auto', block: 'center' }});
                        
                        // 点击元素
                        element.click();
                        return true;
                    }} catch (e) {{
                        console.error('XPath点击失败:', e);
                        return false;
                    }}
                }}
                """)
            else:
                # 使用CSS选择器
                result = await session.execute_script(f"""
                () => {{
                    try {{
                        const element = document.querySelector("{selector}");
                        if (!element) return false;
                        
                        // 滚动到视图
                        element.scrollIntoView({{ behavior: 'auto', block: 'center' }});
                        
                        // 点击元素
                        element.click();
                        return true;
                    }} catch (e) {{
                        console.error('选择器点击失败:', e);
                        return false;
                    }}
                }}
                """)
            
            if result:
                await asyncio.sleep(wait_time)
                return True
            
            return False
        except Exception as e:
            logger.error(f"点击元素失败: {str(e)}")
            return False