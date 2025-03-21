from typing import Dict, Any, AsyncGenerator
import logging
import time
import json
import asyncio
from .selectors import CLAUDE_SELECTORS
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ClaudeAuthHandler:
    """Handles authentication and interaction with Claude AI"""
    
    def __init__(self, session):
        """
        Initialize Claude auth handler
        
        Args:
            session: Browser session object
        """
        self.session = session
        self.domain = "claude.ai"
        self.logged_in = False
        
    async def handle_login(self) -> Dict[str, Any]:
        """
        Handle the login process for Claude
        
        Returns:
            Dict with login status
        """
        try:
            # 检查是否已登录
            is_logged_in = await self._check_logged_in()
            if is_logged_in:
                self.logged_in = True
                logger.info("已通过cookie成功登录Claude")
                return {"status": "success", "message": "已使用cookie登录"}
            
            # 如果cookie登录失败，我们需要处理手动登录
            logger.info("Cookie登录失败，等待手动登录")
            
            # 等待手动登录
            is_logged_in = await self._wait_for_manual_login()
            if is_logged_in:
                self.logged_in = True
                return {"status": "success", "message": "已手动登录"}
            else:
                return {"status": "error", "message": "登录超时"}
                
        except Exception as e:
            logger.error(f"Claude登录错误: {str(e)}")
            return {"status": "error", "message": str(e)}
            
            
    async def _check_logged_in(self) -> bool:
        """
        Check if we're currently logged in to Claude
        
        Returns:
            Boolean indicating logged in status
        """
        try:
            # Try multiple CSS selectors that could indicate being logged in
            selectors = [
                CLAUDE_SELECTORS['logged_in_indicator'],
                "header", 
                ".main-container",
                "[role='main']"
            ]
            
            for selector in selectors:
                try:
                    element = await self.session.wait_for_selector(
                        selector,
                        timeout=2000  # Shorter timeouts for each attempt
                    )
                    if element is not None:
                        return True
                except:
                    continue
                    
            # If we didn't find any indicators, check if we're on the login page
            login_button = await self.session.query_selector("button:has-text('Log in')")
            return login_button is None  # If no login button, we're probably logged in
                
        except Exception as e:
            self.logger.warning(f"Error checking login status: {str(e)}")
            return False

    async def _wait_for_manual_login(self, timeout: int = 300000) -> bool:
        """
        Wait for user to manually log in
        
        Args:
            timeout: Maximum time to wait in milliseconds (default 5 minutes)
            
        Returns:
            Boolean indicating success
        """
        try:
            # 显示消息告知用户
            #await self.session.execute_script("""() => {
            #    const div = document.createElement('div');
            #    div.id = 'login-message';
            #    div.style = 'position: fixed; top: 0; left: 0; right: 0; background: red; color: white; padding: 10px; text-align: center; z-index: 9999;';
            #    div.innerText = '请登录Claude';
            #    document.body.appendChild(div);
            #}""")
            #
            ## 提示用户手动登录
            print("请在浏览器中登录Claude，然后按回车继续...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
            # 检查是否登录成功
            is_logged_in = await self._check_logged_in()
            
            # 移除消息
            await self.session.execute_script("""() => {
                const div = document.getElementById('login-message');
                if (div) div.remove();
            }""")
            
            return is_logged_in
            
        except Exception as e:
            logger.error(f"等待手动登录出错: {str(e)}")
            return False
            


    async def handle_chat_stream(self, prompt: str = None, image_path: str = None, stream: bool = True, new_chat: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle chat interaction with Claude
    
        Args:
            image_path: Optional path to image to upload
            prompt: Text prompt to send
            stream: Whether to stream responses (True) or wait for complete response (False)
            new_chat: Whether to start a new chat
    
        Yields:
            Dict containing response chunks
        """
        try:
            # Start a new chat if requested
            if new_chat:
                logger.info("开始新聊天")
                new_chat_button = await self.session.query_selector(CLAUDE_SELECTORS['new_chat_button'])
                if new_chat_button:
                    await self.session.click(CLAUDE_SELECTORS['new_chat_button'])
                    await asyncio.sleep(2)
                else:
                    logger.warning("未找到新聊天按钮")
    
            # Enter the prompt
            if prompt:
                # Find the textarea
                textarea = await self.session.query_selector("div.ProseMirror")
                if not textarea:
                    yield {"status": "error", "message": "找不到输入框"}
                    return
    
                # Type the prompt
                #await self.session.fill("div.ProseMirror", prompt) 
                # Use JavaScript to simulate paste behavior

                if not isinstance(prompt, str):
                    prompt = str(prompt)
                
                # Use JavaScript to simulate paste behavior
                paste_script = """
                function simulatePaste(message) {
                    // Get the ProseMirror editor element
                    const editor = document.querySelector('div.ProseMirror');
                    if (!editor) return false;
                
                    // Focus the editor
                    editor.focus();
                
                    // Clear existing content (optional)
                    editor.innerHTML = '';
                
                    // Set the content using innerHTML and trigger input event
                    editor.innerHTML = message.replace(/\\n/g, '<br>');
                
                    // Dispatch an input event to notify the application of changes
                    const inputEvent = new Event('input', { bubbles: true });
                    editor.dispatchEvent(inputEvent);
                
                    // Also dispatch a change event
                    const changeEvent = new Event('change', { bubbles: true });
                    editor.dispatchEvent(changeEvent);
                
                    return true;
                }
                return simulatePaste(arguments[0]);
                """
                # Execute the script
                success = await self.session.execute_script(paste_script, prompt)

                if not success:
                    yield {"status": "error", "message": "无法粘贴内容到输入框"}
                    return
                # Click the send button
                send_button = await self.session.query_selector("button[aria-label='Send Message']")
                if not send_button:
                    send_button = await self.session.query_selector("button.bg-accent-main-100")
    
                if not send_button:
                    yield {"status": "error", "message": "找不到发送按钮"}
                    return
    
                await self.session.click(send_button)
                logger.info("已发送消息")
    
                # Wait longer for initial response - artifacts can take time to generate
                await asyncio.sleep(8)
                # Check for loading indicators and wait for them to disappear
                is_loading = True
                loading_attempts = 0
                max_loading_attempts = 20  # Maximum number of attempts to wait for loading to complete
                
                while is_loading and loading_attempts < max_loading_attempts:
                    is_loading = await self.session.execute_script("""
                        return Boolean(
                            document.querySelector('.animate-pulse') || 
                            document.querySelector('[aria-label="Loading"]') ||
                            document.querySelector('.typing-indicator')
                        );
                    """)
                    
                    if is_loading:
                        loading_attempts += 1
                        logger.info(f"等待Claude响应生成完成... ({loading_attempts}/{max_loading_attempts})")
                        await asyncio.sleep(2)
                    else:
                        # Once loading indicators disappear, wait a bit more for content to stabilize
                        await asyncio.sleep(2)
                
                # Get the full page HTML for comprehensive BeautifulSoup analysis
                html_content = await self.session.execute_script("return document.documentElement.outerHTML;")
                
                # Use BeautifulSoup to parse the HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements to clean up the text extraction
                for script in soup(["script", "style", "noscript"]):
                    script.decompose()
                
                # Extract all messages to find the conversation structure
                all_messages = []
                
                # Try to find message containers with author roles
                message_containers = soup.select('li.flex.flex-col')
                
                for container in message_containers:
                    # Determine if this is a user or assistant message
                    is_user = bool(container.select_one('[data-message-author-role="human"]'))
                    is_assistant = bool(container.select_one('[data-message-author-role="assistant"]'))
                    
                    # Extract the text content
                    message_text = container.get_text(separator=' ', strip=True)
                    
                    # Save message info
                    if message_text:
                        all_messages.append({
                            "role": "user" if is_user else "assistant" if is_assistant else "unknown",
                            "content": message_text
                        })
                
                # If we found at least one message pair, we can try to match the prompt and extract the response
                if len(all_messages) >= 2:
                    # Find the last user message with our prompt
                    last_user_index = -1
                    for i, msg in enumerate(all_messages):
                        if msg["role"] == "user" and prompt in msg["content"]:
                            last_user_index = i
                    
                    # If we found our prompt, extract the assistant's response that follows
                    if last_user_index >= 0 and last_user_index + 1 < len(all_messages):
                        assistant_response = all_messages[last_user_index + 1]
                        if assistant_response["role"] == "assistant":
                            logger.info("提取了助手对最近提示的响应")
                            yield {
                                "status": "success",
                                "content": assistant_response["content"],
                                "complete": True,
                                "messages": all_messages  # Include full conversation history
                            }
                            return
                
                # If the above approach didn't work, we'll try a more direct approach
                # Extract all content from the page
                full_text = soup.get_text(separator=' ', strip=True)
                
                # Try to find the prompt in the full text and extract content that follows
                if prompt in full_text:
                    prompt_index = full_text.find(prompt)
                    if prompt_index >= 0:
                        # Get text after the prompt
                        after_prompt = full_text[prompt_index + len(prompt):].strip()
                        
                        # Split into lines and clean up
                        lines = after_prompt.split('\n')
                        clean_lines = []
                        
                        # Filter out UI elements and other noise
                        for line in lines:
                            line = line.strip()
                            if (line and 
                                'retry' not in line.lower() and 
                                'edit' not in line.lower() and
                                'thumb' not in line.lower() and
                                'choose style' not in line.lower() and
                                'claude can make mistakes' not in line.lower()):
                                clean_lines.append(line)
                        
                        # Join the filtered lines
                        response_text = ' '.join(clean_lines)
                        
                        # If we got a substantial response, return it
                        if response_text and len(response_text) > 20:
                            logger.info("从提示后提取文本内容")
                            yield {
                                "status": "success",
                                "content": response_text,
                                "complete": True
                            }
                            return
                
                # Final attempt: try to find the last substantial message
                prose_elements = soup.select('div.prose, div.whitespace-pre-wrap, pre')
                if prose_elements:
                    last_content = prose_elements[-1].get_text(strip=True)
                    if last_content and len(last_content) > 20 and prompt not in last_content:
                        logger.info("从prose元素提取内容")
                        yield {
                            "status": "success",
                            "content": last_content,
                            "complete": True
                        }
                        return
                
                # If we still don't have good content, report an error
                yield {"status": "error", "message": "无法获取Claude的有效响应内容"}

        except Exception as e:
            logger.error(f"聊天错误: {str(e)}")
            yield {"status": "error", "message": str(e)}
                
    

    async def _upload_image(self, image_path: str) -> bool:
        """
        Upload an image to Claude
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Boolean indicating success
        """
        try:
            # 点击上传按钮
            upload_button = await self.session.query_selector(CLAUDE_SELECTORS['upload_button'])
            if not upload_button:
                return False
            
            # 设置文件输入处理
            file_input_selector = 'input[type="file"]'
            file_input = await self.session.query_selector(file_input_selector)
            
            if not file_input:
                # 如果没有文件输入，可能需要点击按钮触发它
                await self.session.click(CLAUDE_SELECTORS['upload_button'])
                file_input = await self.session.wait_for_selector(file_input_selector, timeout=5000)
            
            if file_input:
                # 使用JavaScript设置文件
                await self.session.execute_script(
                    """
                    const input = arguments[0];
                    const filePath = arguments[1];
                    
                    // 创建一个自定义事件
                    const dataTransfer = new DataTransfer();
                    const file = new File([''], filePath.split('/').pop(), { type: 'image/png' });
                    dataTransfer.items.add(file);
                    input.files = dataTransfer.files;
                    
                    // 触发change事件
                    const event = new Event('change', { bubbles: true });
                    input.dispatchEvent(event);
                    """,
                    file_input, image_path
                )
                
                # 等待上传完成
                await self.session.wait_for_selector(CLAUDE_SELECTORS['image_preview'], timeout=30000)
                return True
            else:
                logger.error("找不到文件输入元素")
                return False
                
        except Exception as e:
            logger.error(f"图片上传错误: {str(e)}")
            return False

    async def debug_page_elements(self):
        """
        Debug function to print page structure and elements
        """
        try:
            # Get all message elements
            logger.info("Analyzing page structure...")
    
            # Get HTML structure of messages
            page_html = await self.session.execute_script("""
                // Get the main chat container
                const chatContainer = document.querySelector('main');
                if (!chatContainer) return 'Chat container not found';
    
                // Function to get a simplified DOM representation
                function getElementInfo(element, depth = 0) {
                    if (!element) return '';
    
                    const indent = '  '.repeat(depth);
                    const classes = Array.from(element.classList || []).join('.');
                    const tagName = element.tagName.toLowerCase();
                    const id = element.id ? `#${element.id}` : '';
                    const roleAttr = element.getAttribute('data-message-author-role') || '';
                    const role = roleAttr ? `[data-message-author-role="${roleAttr}"]` : '';
    
                    // Get text content (truncated if needed)
                    let textContent = element.textContent?.trim() || '';
                    if (textContent.length > 50) {
                        textContent = textContent.substring(0, 47) + '...';
                    }
    
                    // Create element representation
                    let info = `${indent}<${tagName}${id}${classes ? '.' + classes : ''}${role}>`;
                    if (textContent) {
                        info += ` "${textContent}"`;
                    }
    
                    // Get child elements, but limit depth and number to avoid huge output
                    if (depth < 10) {
                        const children = Array.from(element.children).slice(0, 20);
                        if (children.length > 0) {
                            info += '\\n';
                            for (const child of children) {
                                info += getElementInfo(child, depth + 1) + '\\n';
                            }
                        }
                    }
    
                    return info;
                }
    
                // Get info for the chat container and its key children
                return getElementInfo(chatContainer);
            """)
    
            logger.info("Page structure:")
            logger.info(page_html)
    
            # Find all potential message containers
            message_containers = await self.session.execute_script("""
                // Find all potential message containers
                const messages = document.querySelectorAll('li, div.prose, div.whitespace-pre-wrap');
    
                // Get information about each message
                const messageInfo = [];
                messages.forEach((message, index) => {
                    const text = message.textContent.trim();
                    if (text.length < 10) return; // Skip very short text elements
    
                    const classes = Array.from(message.classList).join('.');
                    const hasUserIndicator = message.querySelector('[data-message-author-role="human"]') !== null;
                    const hasClaudeIndicator = message.querySelector('[data-message-author-role="assistant"]') !== null;
    
                    messageInfo.push({
                        index,
                        selector: message.tagName.toLowerCase() + (classes ? '.' + classes : ''),
                        length: text.length,
                        preview: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
                        isUser: hasUserIndicator,
                        isAssistant: hasClaudeIndicator
                    });
                });
    
                return messageInfo;
            """)
    
            logger.info("Potential message containers:")
            for container in message_containers:
                logger.info(f"Index: {container['index']}")
                logger.info(f"Selector: {container['selector']}")
                logger.info(f"Type: {'User' if container['isUser'] else 'Assistant' if container['isAssistant'] else 'Unknown'}")
                logger.info(f"Length: {container['length']}")
                logger.info(f"Preview: {container['preview']}")
                logger.info("-" * 50)
    
            # Try to find a better selector for Claude's responses
            claude_selectors = await self.session.execute_script("""
                // List of possible DOM attributes that might indicate a Claude response
                const roleAttributes = [
                    'data-message-author-role="assistant"',
                    'data-author="claude"',
                    'data-message-role="assistant"',
                    'aria-label*="Claude"'
                ];
    
                // List of possible class name patterns that might indicate a Claude response
                const classPatterns = [
                    'prose',
                    'whitespace-pre-wrap',
                    'message',
                    'assistant',
                    'claude'
                ];
    
                // Check for elements matching role attributes
                let roleMatches = [];
                roleAttributes.forEach(attr => {
                    const attrName = attr.split('=')[0];
                    const attrValue = attr.includes('=') ? attr.split('=')[1].replace(/"/g, '') : '';
                    const attrSelector = attrValue ? `[${attrName}="${attrValue}"]` : `[${attrName}]`;
    
                    const matches = document.querySelectorAll(attrSelector);
                    if (matches.length > 0) {
                        roleMatches.push({
                            selector: attrSelector,
                            count: matches.length
                        });
                    }
                });
    
                // Check for elements with class patterns
                let classMatches = [];
                classPatterns.forEach(pattern => {
                    const matches = document.querySelectorAll(`[class*="${pattern}"]`);
                    if (matches.length > 0) {
                        classMatches.push({
                            selector: `[class*="${pattern}"]`,
                            count: matches.length
                        });
                    }
                });
    
                return {
                    roleMatches,
                    classMatches
                };
            """)
    
            logger.info("Potential Claude response selectors:")
            logger.info("Role-based selectors:")
            for selector in claude_selectors['roleMatches']:
                logger.info(f"Selector: {selector['selector']} (Count: {selector['count']})")
    
            logger.info("Class-based selectors:")
            for selector in claude_selectors['classMatches']:
                logger.info(f"Selector: {selector['selector']} (Count: {selector['count']})")
    
        except Exception as e:
            logger.error(f"Debug error: {str(e)}")
