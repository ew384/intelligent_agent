from typing import Dict, Any, AsyncGenerator
import logging
import time
import json
import os
import random
import uuid
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
    # Alternative approach preserving more information
    async def _start_new_chat(self):
        """
        Start a new chat conversation by clicking the new chat button
        
        Returns:
            Boolean indicating success
        """
        try:
            logger.info("Starting new chat via button click")
            
            # Check if we need to start a new chat
            current_url = await self.session.execute_script("return window.location.href")
            if "/new" in current_url:
                logger.info("Already on new chat page")
                return True
                
            # Find and click the new chat button using the selector from CLAUDE_SELECTORS
            new_chat_selector = CLAUDE_SELECTORS['new_chat_button']
            
            # Wait for the button to be visible
            await self.session.wait_for_selector(new_chat_selector)
            
            # Add a small random delay before clicking to simulate human behavior
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Click the button
            await self.session.click(new_chat_selector)
            
            # Wait for page to load
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Verify we're on the new chat page
            current_url = await self.session.execute_script("return window.location.href")
            if "/new" in current_url:
                logger.info("Started new chat successfully via button click")
                return True
            else:
                logger.warning(f"Button click completed but URL doesn't contain /new: {current_url}")
                
                # Fall back to direct navigation if button click doesn't work
                logger.info("Falling back to direct navigation")
                await self.session.goto("https://claude.ai/new")
                await asyncio.sleep(3)
                return True
                
        except Exception as e:
            logger.error(f"Error starting new chat: {str(e)}")
            return False

    async def _upload_files(self, file_paths):
        """
        Upload one or more files to Claude using JavaScript to directly set the file
        
        Args:
            file_paths: Path or list of paths to files to upload
                
        Returns:
            Boolean indicating success
        """
        try:
            if not file_paths:
                return False
                
            # Convert single path to list
            if isinstance(file_paths, str):
                file_paths = [file_paths]
            
            # First, try to ensure file input is available without clicking button
            # (Often the file input exists but is hidden)
            file_input = await self.session.query_selector('input[type="file"]')
            
            if not file_input:
                logger.warning("File input not immediately found, trying alternative approaches")
                
                # Try clicking the upload button using JavaScript
                js_click_result = await self.session.execute_script("""
                    // Try multiple selector approaches
                    const selectors = [
                        '[aria-label*="upload" i]',
                        '[data-testid="file-upload"]',
                        'button:has-text("Upload")',
                        'button svg[*|href*="upload"]'
                    ];
                    
                    for (const selector of selectors) {
                        const button = document.querySelector(selector);
                        if (button) {
                            console.log("Found upload button with selector: " + selector);
                            button.click();
                            return true;
                        }
                    }
                    
                    return false;
                """)
                
                if not js_click_result:
                    logger.warning("Could not find upload button with any known selectors")
                
                await asyncio.sleep(1)
                
                # Try to find the file input again
                #file_input = await self.session.query_selector('input[type="file"]')
                try:
                    file_input = self.session.find_element_by_css_selector('input[type="file"]')
                except:
                    logger.error("Could not find file input element after multiple attempts")

            
            # Now that we have the file input, upload the files
            logger.info(f"Uploading {len(file_paths)} files")
            for file_path in file_paths:
                file_input.send_keys(os.path.abspath(file_path))
                logger.info(f"File {file_path} upload succeeded")

            # Wait for uploads to complete
            await asyncio.sleep(3)  # Give it some time to process
                    
        except Exception as e:
            logger.error(f"Error uploading files: {str(e)}")
            return False
        return True

    async def get_chat_id(self):
        try:
            chat_id = await self.session.execute_script("""
                const url = window.location.href;
                const match = url.match(/claude\\.ai\\/chat\\/([^?#]+)/);
                return match ? match[1] : null;
            """)
            
            if chat_id:
                logger.info(f"获取到会话 ID: {chat_id}")
                return chat_id
            else:
                logger.warning("无法从 URL 获取会话 ID")
                return None
        except Exception as e:
            logger.error(f"获取会话 ID 时出错: {str(e)}")
            return None
        
    async def handle_chat_stream(self, prompt: str = None, file_paths = None, stream: bool = True, new_chat: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle chat interaction with Claude
        
        Args:
            file_paths: Optional paths to upload
            prompt: Text prompt to send
            stream: Whether to stream responses (True) or wait for complete response (False)
            new_chat: Whether to start a new chat
        
        Yields:
            Dict containing response chunks or final structured content
        """
        try:
            # Start a new chat if requested
            if new_chat:
                logger.info("Starting new chat")
                success = await self._start_new_chat()
                if not success:
                    yield {"status": "error", "message": "Could not start new chat"}
                    return
                    
            # Upload files if provided
            if file_paths:
                logger.info(file_paths)
                logger.info(f"Uploading files: {file_paths}")
                success = await self._upload_files(file_paths)
                if not success:
                    yield {"status": "error", "message": "Failed to upload files"}
                    return

            # Enter the prompt
            if prompt:
                # Find the textarea
                textarea = await self.session.query_selector("div.ProseMirror")
                if not textarea:
                    yield {"status": "error", "message": "找不到输入框"}
                    return

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

                send_button_enabled = False
                retry_count = 0
                while retry_count < 20 and not send_button_enabled:
                    try:
                        # Use JavaScript to check if the button is enabled
                        send_button_enabled = await self.session.execute_script("""
                            const sendBtn = document.querySelector('button[aria-label="Send Message"]');
                            return sendBtn && !sendBtn.disabled;
                        """)
                        
                        if send_button_enabled:
                            break
                            
                        await asyncio.sleep(1)
                        retry_count += 1
                    except Exception as e:
                        logger.warning(f"Error checking send button state: {str(e)}")
                        retry_count += 1
                        
                if not send_button_enabled:
                    yield {"status": "error", "message": "发送按钮未启用，可能是输入框为空或Claude正在处理"}
                    return
                    
                try:
                    # Click the send button using JavaScript instead of Playwright's click
                    await self.session.execute_script("""
                        const sendBtn = document.querySelector('button[aria-label="Send Message"]');
                        if (sendBtn && !sendBtn.disabled) {
                            sendBtn.click();
                            return true;
                        }
                        return false;
                    """)
                    logger.info("已发送消息")
                except Exception as e:
                    logger.error(f"点击发送按钮失败: {str(e)}")
                    yield {"status": "error", "message": "发送消息失败"}
                    return

                # Wait for response to complete
                try:
                    # Wait for Claude to finish generating a response
                    # More reliable way to detect response completion using JavaScript
                    js_detect_completion = """
                    function checkResponseComplete() {
                        // Check if "thinking" indicator is gone
                        const thinkingIndicator = document.querySelector('.animate-pulse');
                        if (thinkingIndicator) return false;
                        
                        // Check if input area is enabled again
                        const textArea = document.querySelector('div.ProseMirror[contenteditable="true"]');
                        const sendButton = document.querySelector('button[aria-label="Send Message"]:not([disabled])');
                        
                        // Check for regenerate button by looking for buttons with certain text content
                        let regenerateButton = null;
                        const buttons = Array.from(document.querySelectorAll('button'));
                        for (const button of buttons) {
                            if (button.textContent.includes('Regenerate') || 
                                button.textContent.includes('重新生成') ||
                                button.textContent.includes('Retry')) {
                                regenerateButton = button;
                                break;
                            }
                        }
                        
                        // If text area is enabled OR regenerate button exists, response is complete
                        return (textArea && sendButton) || regenerateButton;
                    }
                    return checkResponseComplete();
                    """
                    
                    # Wait for response to complete with timeout
                    retry_count = 0
                    max_retries = 60  # About 2 minutes of waiting
                    
                    while retry_count < max_retries:
                        is_complete = await self.session.execute_script(js_detect_completion)
                        if is_complete:
                            logger.info("Claude响应已完成")
                            break
                        
                        await asyncio.sleep(2)
                        retry_count += 1
                    
                    # Extra wait to ensure all content is fully loaded
                    await asyncio.sleep(2)
                    
                    # Now extract the page content
                    page_content = await self._extract_page_content()
                    
                    if page_content and "conversationTurns" in page_content:
                        # Format the content as desired
                        formatted_content = {
                            "status": "success",
                            "content": {}
                        }
                        
                        # Add each conversation round to the result
                        '''
                        for i, turn in enumerate(page_content["conversationTurns"]):
                            round_key = f"round {i+1}"
                            formatted_content["content"][round_key] = {
                                "query": turn.get("query", ""),
                                "response": "\n".join(turn.get("responses", [])),
                                "codeBlocks": turn.get("codeBlocks", []),
                                "documents": turn.get("documents", []),
                                "codeExplanations": turn.get("codeExplanations", [])
                            }
                        '''
                        messages = []
                        # Add each conversation round as a message
                        for turn in page_content["conversationTurns"]:
                            # Add user message
                            if turn.get("query", ""):
                                messages.append({
                                    "role": "user",
                                    "content": turn.get("query", "")
                                })
                            
                            # Add assistant message
                            if turn.get("responses", []):
                                messages.append({
                                    "role": "assistant",
                                    "content": {
                                        "response": turn.get("responses", []),
                                        "codeBlocks": turn.get("codeBlocks", []),
                                        "documents": turn.get("documents", []),
                                        "codeExplanations": turn.get("codeExplanations", [])
                                    }
                                })
                        
                        # Create the simplified response object
                        chat_id = await self.get_chat_id()
                        logger.info(f"当前会话 ID: {chat_id}")
                        openai_format = {
                            "id": "chatcmpl-" + str(chat_id),
                            "created": int(time.time()),
                            "model": "Claude 3.7 Sonnet",
                            "messages":messages
                        }
                        yield openai_format

                    else:
                        logger.error("无法提取页面内容")
                    
                except Exception as e:
                    logger.error(f"提取内容时出错: {str(e)}")
                    
                # If we still don't have good content, report an error
            else:
                yield {"status": "error", "message": "无法获取Claude的有效响应内容"}

        except Exception as e:
            logger.error(f"聊天错误: {str(e)}")
            yield {"status": "error", "message": str(e)}
    
    async def _extract_page_content(self):
        """Extract the page content similar to extract_page_content function"""
        try:
            # Use JavaScript to extract content and preserve formatting
            js_script = """
            function getFormattedContent() {
                // 存储内容
                let content = {
                    conversationTurns: [],
                    uiElements: []
                };
                
                // 更可靠的方式查找对话区域
                const mainContentArea = document.querySelector('div.flex-1.flex.flex-col.gap-3');
                if (!mainContentArea) {
                    return { error: "无法找到主要内容区域" };
                }
                
                // 获取所有直接子元素，它们应该是对话轮次
                const conversationElements = Array.from(mainContentArea.children);
                
                // 初始化变量来跟踪当前的对话轮次
                let currentTurn = null;
                
                for (const element of conversationElements) {
                    // 检查元素是否包含用户查询（通常有特定的背景色）
                    const isUserQuery = element.querySelector('.bg-bg-300');
                    
                    if (isUserQuery) {
                        // 如果有之前的轮次，将其添加到结果中
                        if (currentTurn) {
                            content.conversationTurns.push(currentTurn);
                        }
                        
                        // 提取用户查询文本，排除可能的编辑按钮
                        let queryText = isUserQuery.textContent.trim();
                        queryText = queryText.replace(/Edit$/, '').trim();
                        
                        // 移除用户名前缀（例如："E"）
                        queryText = queryText.replace(/^[A-Z]\\s*/, '');
                        
                        // 创建新的对话轮次
                        currentTurn = {
                            query: queryText,
                            responses: [],
                            codeBlocks: [],
                            documents: [],
                            codeExplanations: []
                        };
                    } else {
                        // 如果没有当前轮次，跳过
                        if (!currentTurn) continue;
                        
                        // 检查是否是 Claude 的回复（通常有特定的样式特征）
                        const hasResponseContent = element.querySelector('.font-claude-message') || 
                                                element.querySelector('[class*="tracking"]');
                        
                        if (hasResponseContent) {
                            // 处理回复内容
                            
                            // 1. 查找代码块
                            const codeBlocks = element.querySelectorAll('pre');
                            for (const codeBlock of codeBlocks) {
                                // 获取代码语言
                                let language = '';
                                const codeElement = codeBlock.querySelector('code');
                                if (codeElement && codeElement.className) {
                                    const match = codeElement.className.match(/language-([a-zA-Z0-9]+)/);
                                    if (match) {
                                        language = match[1];
                                    }
                                }
                                
                                // 获取代码文本
                                let codeText = codeBlock.textContent || "";
                                
                                // 移除"Copy"和语言标识
                                codeText = codeText.replace(/^(python|javascript|html|css|json)\\s*Copy\\s*/i, '');
                                
                                // 将代码块添加到当前轮次
                                if (codeText.trim()) {
                                    currentTurn.codeBlocks.push({
                                        language: language || 'python', // 默认为python
                                        code: codeText
                                    });
                                }
                            }
                            
                            // 2. 查找文档引用
                            const docButtons = element.querySelectorAll('button[class*="font-styrene"][class*="border-0"]');
                            for (const docButton of docButtons) {
                                // 提取文档标题
                                const docTitle = docButton.textContent.replace(/Click to open document.*$/, '').trim();
                                
                                // 尝试找到文档内容
                                let docContent = [];
                                
                                // 检查页面上是否有侧边栏，其中可能包含文档内容
                                const sidebarContent = document.querySelector('div[class*="fixed"][class*="right-0"][class*="flex"][class*="w-full"]');
                                if (sidebarContent) {
                                    // 从侧边栏中提取段落
                                    const docTextElements = sidebarContent.querySelectorAll('p');
                                    for (const textEl of docTextElements) {
                                        docContent.push(textEl.textContent.trim());
                                    }
                                }
                                
                                // 添加文档到当前轮次
                                if (docTitle) {
                                    currentTurn.documents.push({
                                        title: docTitle,
                                        content: docContent
                                    });
                                }
                            }
                            
                            // 3. 提取代码说明和使用说明 - 改进的捕获方式
                            let codeExplanations = [];
                            
                            // 整个响应元素作为容器，查找所有可能的说明文本
                            const allExplanationTexts = [];
                            
                            // 查找所有列表（有序和无序）
                            const listItems = element.querySelectorAll('ol li, ul li');
                            for (const item of listItems) {
                                // 检查不在代码块内
                                if (!item.closest('pre')) {
                                    allExplanationTexts.push(item.textContent.trim());
                                }
                            }
                            
                            // 如果找到列表项，添加为代码说明
                            if (listItems.length > 0) {
                                const orderedLists = element.querySelectorAll('ol');
                                for (const list of orderedLists) {
                                    // 检查不在代码块内
                                    if (!list.closest('pre')) {
                                        codeExplanations.push(list.textContent.trim());
                                    }
                                }
                                
                                const unorderedLists = element.querySelectorAll('ul');
                                for (const list of unorderedLists) {
                                    // 检查不在代码块内
                                    if (!list.closest('pre')) {
                                        codeExplanations.push(list.textContent.trim());
                                    }
                                }
                            }
                            
                            // 查找可能包含使用说明的段落和div
                            const explanationParagraphs = element.querySelectorAll('p, div');
                            for (const para of explanationParagraphs) {
                                const text = para.textContent.trim();
                                
                                // 特定关键词的段落，如果不在代码块中
                                if ((text.includes('To use this code') || 
                                    text.includes('Install') || 
                                    text.includes('Set your API') || 
                                    text.includes('Run the script') ||
                                    text.includes('adjust parameters') ||
                                    text.includes('This demo shows')) && 
                                    !para.closest('pre') && 
                                    !para.querySelector('pre') &&
                                    !text.includes('Claude can make mistakes')) {
                                    
                                    // 排除已经添加的（避免重复）
                                    if (!codeExplanations.includes(text)) {
                                        codeExplanations.push(text);
                                    }
                                }
                            }
                            
                            // 添加到当前轮次
                            currentTurn.codeExplanations = codeExplanations;
                            
                            // 4. 更全面地捕获说明文本
                            // 创建一个临时的容器来保存所有内容，过滤掉代码区域
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = element.innerHTML;
                            
                            // 移除所有代码块，以便我们可以获取剩余文本
                            const codeToRemove = tempDiv.querySelectorAll('pre');
                            for (const code of codeToRemove) {
                                if (code.parentNode) {
                                    code.parentNode.removeChild(code);
                                }
                            }
                            
                            // 查找特定的段落文本模式
                            const remainingText = tempDiv.textContent;
                            const usageMatch = remainingText.match(/To use this code:([\\s\\S]*?)(?=\\n\\n|$)/);
                            if (usageMatch && usageMatch[1]) {
                                const usageText = usageMatch[1].trim();
                                if (usageText && !codeExplanations.includes(usageText)) {
                                    codeExplanations.push("To use this code:" + usageText);
                                }
                            }
                            
                            // 查找其他关键说明段落
                            const demoMatch = remainingText.match(/This demo shows([\\s\\S]*?)(?=\\n\\n|$)/);
                            if (demoMatch && demoMatch[0]) {
                                const demoText = demoMatch[0].trim();
                                if (demoText && !codeExplanations.includes(demoText)) {
                                    codeExplanations.push(demoText);
                                }
                            }
                            
                            // 5. 提取回复文本（排除代码块、按钮和已捕获的说明）
                            let responseText = '';
                            
                            // 查找所有段落元素
                            const allParagraphs = element.querySelectorAll('p');
                            for (const para of allParagraphs) {
                                // 排除代码块内的段落、文档引用按钮内的文本和明显的说明文本
                                const paraText = para.textContent.trim();
                                if (!para.closest('pre') && 
                                    !para.closest('button') && 
                                    !paraText.includes('To use this code') &&
                                    !paraText.includes('This demo shows') &&
                                    !paraText.includes('Claude can make mistakes')) {
                                    
                                    responseText += paraText + '\\n\\n';
                                }
                            }
                            
                            // 如果没有找到段落元素或文本为空，尝试从主元素提取
                            if (!responseText.trim()) {
                                // 复制内容
                                const tempTextDiv = document.createElement('div');
                                tempTextDiv.innerHTML = element.innerHTML;
                                
                                // 移除代码块、按钮和其他UI元素
                                const elementsToRemove = [
                                    ...tempTextDiv.querySelectorAll('pre'),
                                    ...tempTextDiv.querySelectorAll('button'),
                                    ...tempTextDiv.querySelectorAll('ol'),
                                    ...tempTextDiv.querySelectorAll('ul')
                                ];
                                
                                for (const el of elementsToRemove) {
                                    if (el.parentNode) {
                                        el.parentNode.removeChild(el);
                                    }
                                }
                                
                                // 移除UI元素文本
                                responseText = tempTextDiv.textContent.trim()
                                    .replace(/Retry/g, '')
                                    .replace(/Copy/g, '')
                                    .replace(/Edit/g, '')
                                    .replace(/Claude can make mistakes. Please double-check responses./g, '')
                                    .trim();
                            }
                            
                            // 移除多余的空行
                            responseText = responseText.replace(/\\n{3,}/g, '\\n\\n');
                            
                            // 添加到当前轮次的回复
                            if (responseText.trim()) {
                                currentTurn.responses.push(responseText);
                            }
                        }
                    }
                }
                
                // 添加最后一个轮次（如果有）
                if (currentTurn) {
                    content.conversationTurns.push(currentTurn);
                }
                
                // 收集页面头部信息作为UI元素
                const headerElement = document.querySelector('header');
                if (headerElement) {
                    content.uiElements.push({
                        type: 'header',
                        text: headerElement.textContent.trim()
                    });
                }
                
                // 收集页面底部的免责声明
                const disclaimerElement = document.querySelector('div[class*="Claude can make mistakes"]');
                if (disclaimerElement) {
                    content.uiElements.push({
                        type: 'disclaimer',
                        text: disclaimerElement.textContent.trim()
                    });
                }
                
                return content;
            }
            
            return getFormattedContent();
            """
            
            content_data = await self.session.execute_script(js_script)
            
            # 检查是否有错误
            if isinstance(content_data, dict) and 'error' in content_data:
                logger.error(f"JavaScript执行错误: {content_data['error']}")
                return None
            
            return content_data
            
        except Exception as e:
            logger.error(f"提取页面内容时出错: {str(e)}")
            return None


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
