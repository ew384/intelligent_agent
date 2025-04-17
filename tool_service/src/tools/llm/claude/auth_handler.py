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
        pass
            
            
    async def _check_logged_in(self) -> bool:
        """
        Check if we're currently logged in to Claude
        
        Returns:
            Boolean indicating logged in status
        """
        pass

    async def _wait_for_manual_login(self, timeout: int = 300000) -> bool:
        """
        Wait for user to manually log in
        
        Args:
            timeout: Maximum time to wait in milliseconds (default 5 minutes)
            
        Returns:
            Boolean indicating success
        """
        pass
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
            file_input = await self.session.query_selector(CLAUDE_SELECTORS['file_input'])
             
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
                try:
                    file_input = self.session.find_element_by_css_selector(CLAUDE_SELECTORS['file_input'])
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
                        send_button_enabled = await self.session.execute_script(f"""
                            const sendBtn = document.querySelector('{CLAUDE_SELECTORS["send_button"]}');
                            return sendBtn && !sendBtn.disabled;
                        """                        )
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
                    await self.session.execute_script(f"""
                        const sendBtn = document.querySelector('{CLAUDE_SELECTORS["send_button"]}');
                        if (sendBtn && !sendBtn.disabled) {{
                            sendBtn.click();
                            return true;
                        }}
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
        """Extract the page content including folded code blocks and multiple versions"""
        try:
            # First, let's extract document content by clicking each document button
            documents_data = await self.session.execute_script("""
            async function extractAllDocumentContent() {
                // Map to store all document content
                const documentsData = new Map();
                
                // Find all document buttons
                const docButtons = Array.from(document.querySelectorAll('button[class*="font-styrene"][class*="border-0"]'));
                const docButtonsFiltered = docButtons.filter(btn => 
                    btn.textContent.includes('Document') || 
                    (btn.textContent.toLowerCase().includes('doc') && !btn.textContent.toLowerCase().includes('code'))
                );
                
                // Process each button sequentially
                for (const button of docButtonsFiltered) {
                    try {
                        const buttonText = button.textContent.trim();
                        const docTitle = buttonText.replace(/Click to open document.*$/, '').trim();
                        
                        // Click the button to display document in sidebar
                        button.click();
                        
                        // Wait for sidebar to update
                        await new Promise(r => setTimeout(r, 500));
                        
                        // Extract document content from the sidebar
                        const sidebarContainer = document.querySelector('.max-md\\\\:absolute.top-0.right-0.bottom-0.left-0.z-20');
                        if (sidebarContainer) {
                            // Extract paragraphs, lists, and other content
                            const contentElements = sidebarContainer.querySelectorAll('p, li, pre, code, h1, h2, h3, h4, h5, h6');
                            let docContent = [];
                            
                            for (const el of contentElements) {
                                // Skip elements that are part of a navigation or control UI
                                if (el.closest('[role="navigation"]') || el.closest('[role="button"]')) {
                                    continue;
                                }
                                
                                const text = el.textContent.trim();
                                if (text) {
                                    docContent.push({
                                        type: el.tagName.toLowerCase(),
                                        text: text
                                    });
                                }
                            }
                            
                            // Try to get the raw document content if it's code or JSON
                            const codeBlock = sidebarContainer.querySelector('pre code');
                            let rawContent = null;
                            let documentType = 'text';
                            
                            if (codeBlock) {
                                rawContent = codeBlock.textContent.trim();
                                // Try to determine if it's JSON
                                try {
                                    JSON.parse(rawContent);
                                    documentType = 'json';
                                } catch (e) {
                                    // If there's a language class, use that
                                    if (codeBlock.className && codeBlock.className.includes('language-')) {
                                        documentType = codeBlock.className.match(/language-([a-zA-Z0-9]+)/)[1];
                                    }
                                }
                            }
                            
                            // Store document with its content
                            documentsData.set(buttonText, {
                                title: docTitle,
                                content: docContent,
                                rawContent: rawContent,
                                type: documentType,
                                buttonLabel: buttonText
                            });
                            console.log(`Extracted document content for: ${buttonText}`);
                        }
                        
                        // Close the sidebar by clicking outside
                        const mainArea = document.querySelector('.flex-1.flex.flex-col.gap-3');
                        if (mainArea) {
                            mainArea.click();
                            await new Promise(r => setTimeout(r, 300));
                        }
                    } catch (buttonError) {
                        console.error("Error processing document button:", buttonError);
                    }
                }
                
                return Array.from(documentsData.entries());
            }
            
            return await extractAllDocumentContent();
            """)
            
            # Now extract code blocks by clicking each code button
            code_versions = await self.session.execute_script("""
            async function extractAllCodeVersions() {
                // Map to store all code versions
                const codeVersions = new Map();
                
                // Find all code version buttons
                const codeButtons = Array.from(document.querySelectorAll('button.flex.text-left.font-styrene.rounded-xl'));
                const codeButtonsFiltered = codeButtons.filter(btn => 
                    btn.textContent.includes('Code') || 
                    btn.textContent.includes('∙')
                );
                
                // Process each button sequentially
                for (const button of codeButtonsFiltered) {
                    try {
                        const buttonText = button.textContent.trim();
                        
                        // Extract version information
                        let versionLabel = "Version 1";
                        if (buttonText.includes('Version')) {
                            const versionMatch = buttonText.match(/Version\\s*(\\d+)/i);
                            if (versionMatch) {
                                versionLabel = `Version ${versionMatch[1]}`;
                            }
                        } else if (buttonText.includes('∙')) {
                            const parts = buttonText.split('∙');
                            if (parts.length > 1) {
                                versionLabel = parts[1].trim();
                            }
                        }
                        
                        // Click the button to display code in sidebar
                        button.click();
                        
                        // Wait for sidebar to update
                        await new Promise(r => setTimeout(r, 500));
                        
                        // Extract code from the sidebar
                        const sidebarCodeContainer = document.querySelector('.max-md\\\\:absolute.top-0.right-0.bottom-0.left-0.z-20');
                        if (sidebarCodeContainer) {
                            // Try to find a code element with a language class
                            const codeElements = sidebarCodeContainer.querySelectorAll('code[class*="language-"]');
                            let fullCodeText = "";
                            let language = "";
                            
                            if (codeElements.length > 0) {
                                // Use the first code element with a language
                                const codeElement = codeElements[0];
                                fullCodeText = codeElement.textContent.trim();
                                
                                // Extract language from class
                                const langMatch = codeElement.className.match(/language-([a-zA-Z0-9]+)/);
                                if (langMatch) {
                                    language = langMatch[1];
                                }
                            } else {
                                // Look for any pre > code combination
                                const preElement = sidebarCodeContainer.querySelector('pre code');
                                if (preElement) {
                                    fullCodeText = preElement.textContent.trim();
                                    // Default to assuming it's a general code block
                                    language = "text";
                                    
                                    // Try to determine if it's JSON
                                    try {
                                        JSON.parse(fullCodeText);
                                        language = 'json';
                                    } catch (e) {
                                        // Not JSON, default to text
                                    }
                                }
                            }
                            
                            if (fullCodeText) {
                                // Store code with its version info
                                codeVersions.set(buttonText, {
                                    language: language || 'text',
                                    code: fullCodeText,
                                    buttonLabel: buttonText,
                                    version: versionLabel
                                });
                                console.log(`Extracted code for: ${buttonText} (${versionLabel})`);
                            }
                        }
                        
                        // Close the sidebar by clicking outside
                        const mainArea = document.querySelector('.flex-1.flex.flex-col.gap-3');
                        if (mainArea) {
                            mainArea.click();
                            await new Promise(r => setTimeout(r, 300));
                        }
                    } catch (buttonError) {
                        console.error("Error processing code button:", buttonError);
                    }
                }
                
                return Array.from(codeVersions.entries());
            }
            
            return await extractAllCodeVersions();
            """)
            
            # Now extract the conversation structure with our extracted data
            js_script = """
            function getFormattedContent() {
                // Store content
                let content = {
                    conversationTurns: [],
                    uiElements: []
                };
                
                // Get external code versions map
                const codeVersionsMap = new Map(arguments[0]);
                
                // Get external document content map
                const documentsMap = new Map(arguments[1]);
                
                // More reliable way to find the conversation area
                const mainContentArea = document.querySelector('div.flex-1.flex.flex-col.gap-3');
                if (!mainContentArea) {
                    return { error: "Cannot find main content area" };
                }
                
                // Get all direct children, which should be conversation turns
                const conversationElements = Array.from(mainContentArea.children);
                
                // Initialize variables to track the current conversation turn
                let currentTurn = null;
                let turnIndex = 0;
                
                for (const element of conversationElements) {
                    // Check if the element contains a user query (usually has a specific background color)
                    const isUserQuery = element.querySelector('.bg-bg-300');
                    
                    if (isUserQuery) {
                        // If there was a previous turn, add it to the results
                        if (currentTurn) {
                            content.conversationTurns.push(currentTurn);
                            turnIndex++;
                        }
                        
                        // Extract user query text, excluding possible edit buttons
                        let queryText = isUserQuery.textContent.trim();
                        queryText = queryText.replace(/Edit$/, '').trim();
                        
                        // Remove user name prefix (e.g., "E")
                        queryText = queryText.replace(/^[A-Z]\\s*/, '');
                        
                        // Create a new conversation turn
                        currentTurn = {
                            turnIndex: turnIndex,
                            query: queryText,
                            responses: [],
                            codeBlocks: [],
                            documents: [],
                            codeExplanations: []
                        };
                    } else {
                        // If there's no current turn, skip
                        if (!currentTurn) continue;
                        
                        // Check if it's Claude's reply (usually has specific style features)
                        const hasResponseContent = element.querySelector('.font-claude-message') || 
                                                element.querySelector('[class*="tracking"]');
                        
                        if (hasResponseContent) {
                            // Process reply content
                            
                            // Look for code block buttons that reference folded code
                            const codeBlockButtons = element.querySelectorAll('button.flex.text-left.font-styrene.rounded-xl');
                            for (const button of codeBlockButtons) {
                                try {
                                    const buttonText = button.textContent.trim();
                                    // Check if this is a code block button
                                    if (buttonText.includes('Code') || buttonText.includes('∙')) {
                                        // Look for the corresponding code in our map
                                        if (codeVersionsMap.has(buttonText)) {
                                            const codeData = codeVersionsMap.get(buttonText);
                                            currentTurn.codeBlocks.push({
                                                language: codeData.language || 'text',
                                                code: codeData.code,
                                                version: codeData.version,
                                                buttonLabel: buttonText
                                            });
                                        } else {
                                            // If code not found, add placeholder
                                            let versionLabel = "Version 1";
                                            if (buttonText.includes('Version')) {
                                                const versionMatch = buttonText.match(/Version\\s*(\\d+)/i);
                                                if (versionMatch) {
                                                    versionLabel = `Version ${versionMatch[1]}`;
                                                }
                                            } else if (buttonText.includes('∙')) {
                                                const parts = buttonText.split('∙');
                                                if (parts.length > 1) {
                                                    versionLabel = parts[1].trim();
                                                }
                                            }
                                            
                                            currentTurn.codeBlocks.push({
                                                language: 'unknown',
                                                code: `[Code block referenced but not found: ${buttonText}]`,
                                                version: versionLabel,
                                                buttonLabel: buttonText
                                            });
                                        }
                                    }
                                } catch (buttonError) {
                                    console.error("Error processing code button:", buttonError);
                                }
                            }
                            
                            // 1. Process document buttons and add their content 
                            const docButtons = element.querySelectorAll('button[class*="font-styrene"][class*="border-0"]');
                            for (const docButton of docButtons) {
                                try {
                                    const buttonText = docButton.textContent.trim();
                                    
                                    // Look for the document in our extracted map
                                    if (documentsMap.has(buttonText)) {
                                        const docData = documentsMap.get(buttonText);
                                        currentTurn.documents.push({
                                            title: docData.title,
                                            content: docData.content,
                                            rawContent: docData.rawContent,
                                            type: docData.type,
                                            buttonLabel: buttonText
                                        });
                                    } else {
                                        // If not found in map, extract what we can from the button
                                        const docTitle = buttonText.replace(/Click to open document.*$/, '').trim();
                                        currentTurn.documents.push({
                                            title: docTitle,
                                            content: [],
                                            buttonLabel: buttonText
                                        });
                                    }
                                } catch (buttonError) {
                                    console.error("Error processing document button:", buttonError);
                                }
                            }
                            
                            // 2. Find inline code blocks (not folded ones)
                            const codeBlocks = element.querySelectorAll('pre');
                            for (const codeBlock of codeBlocks) {
                                // Skip if it's inside a button (likely a preview)
                                if (codeBlock.closest('button')) continue;
                                
                                // Get code language
                                let language = '';
                                const codeElement = codeBlock.querySelector('code');
                                if (codeElement && codeElement.className) {
                                    const match = codeElement.className.match(/language-([a-zA-Z0-9]+)/);
                                    if (match) {
                                        language = match[1];
                                    }
                                }
                                
                                // Get code text
                                let codeText = codeBlock.textContent || "";
                                
                                // Remove "Copy" and language identifiers
                                codeText = codeText.replace(/^(python|javascript|html|css|json)\\s*Copy\\s*/i, '');
                                codeText = codeText.replace(/Copy$/i, '').trim();
                                
                                // Add the code block to the current turn if it's not empty
                                if (codeText.trim()) {
                                    // Check if this is a duplicate of a folded code block we already added
                                    let isDuplicate = false;
                                    for (const existingBlock of currentTurn.codeBlocks) {
                                        // Only mark as duplicate if it's a subset (might be a preview)
                                        if (existingBlock.code.includes(codeText)) {
                                            isDuplicate = true;
                                            break;
                                        }
                                    }
                                    
                                    if (!isDuplicate) {
                                        currentTurn.codeBlocks.push({
                                            language: language || 'text', 
                                            code: codeText,
                                            isInline: true
                                        });
                                    }
                                }
                            }
                            
                            // 3. Extract code explanations and usage instructions
                            let codeExplanations = [];
                            
                            // Find all lists (ordered and unordered)
                            const listItems = element.querySelectorAll('ol li, ul li');
                            for (const item of listItems) {
                                // Check not in a code block
                                if (!item.closest('pre')) {
                                    const itemText = item.textContent.trim();
                                    if (itemText && !codeExplanations.includes(itemText)) {
                                        codeExplanations.push(itemText);
                                    }
                                }
                            }
                            
                            // Get complete ordered and unordered lists
                            const orderedLists = element.querySelectorAll('ol');
                            for (const list of orderedLists) {
                                // Check not in a code block
                                if (!list.closest('pre')) {
                                    const listText = list.textContent.trim();
                                    if (listText && !codeExplanations.includes(listText)) {
                                        codeExplanations.push(listText);
                                    }
                                }
                            }
                            
                            const unorderedLists = element.querySelectorAll('ul');
                            for (const list of unorderedLists) {
                                // Check not in a code block
                                if (!list.closest('pre')) {
                                    const listText = list.textContent.trim();
                                    if (listText && !codeExplanations.includes(listText)) {
                                        codeExplanations.push(listText);
                                    }
                                }
                            }
                            
                            // Find paragraphs and divs that might contain usage instructions
                            const explanationParagraphs = element.querySelectorAll('p, div');
                            for (const para of explanationParagraphs) {
                                const text = para.textContent.trim();
                                
                                // Specific keywords in paragraphs, if not in a code block
                                if ((text.includes('To use this code') || 
                                    text.includes('Install') || 
                                    text.includes('Set your API') || 
                                    text.includes('Run the script') ||
                                    text.includes('adjust parameters') ||
                                    text.includes('This demo shows')) && 
                                    !para.closest('pre') && 
                                    !para.querySelector('pre') &&
                                    !text.includes('Claude can make mistakes')) {
                                    
                                    // Exclude already added (avoid duplicates)
                                    if (!codeExplanations.includes(text)) {
                                        codeExplanations.push(text);
                                    }
                                }
                            }
                            
                            // Add to current turn
                            currentTurn.codeExplanations = codeExplanations;
                            
                            // 5. Extract response text (excluding code blocks, buttons, and captured explanations)
                            let responseText = '';
                            
                            // Create a temporary container to hold all content, filter out code areas
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = element.innerHTML;
                            
                            // Remove all code blocks, buttons, and other UI elements
                            const elementsToRemove = [
                                ...tempDiv.querySelectorAll('pre'),
                                ...tempDiv.querySelectorAll('button'),
                                ...tempDiv.querySelectorAll('ol'),
                                ...tempDiv.querySelectorAll('ul')
                            ];
                            
                            for (const el of elementsToRemove) {
                                if (el.parentNode) {
                                    el.parentNode.removeChild(el);
                                }
                            }
                            
                            // Remove UI element text
                            responseText = tempDiv.textContent.trim()
                                .replace(/Retry/g, '')
                                .replace(/Copy/g, '')
                                .replace(/Edit/g, '')
                                .replace(/Claude can make mistakes. Please double-check responses./g, '')
                                .trim();
                                
                            // Remove excess blank lines
                            responseText = responseText.replace(/\\n{3,}/g, '\\n\\n');
                            
                            // Add to the current turn's responses
                            if (responseText.trim()) {
                                currentTurn.responses.push(responseText);
                            }
                            
                            // Look for "Claude hit the max length" messages
                            if (responseText.includes("Claude hit the max length") || 
                                responseText.includes("has paused its response")) {
                                currentTurn.hitMaxLength = true;
                            }
                        }
                    }
                }
                
                // Add the last turn (if any)
                if (currentTurn) {
                    content.conversationTurns.push(currentTurn);
                }
                
                // Post-process turns to mark "continue" queries
                for (let i = 1; i < content.conversationTurns.length; i++) {
                    const prevTurn = content.conversationTurns[i-1];
                    const currentTurn = content.conversationTurns[i];
                    
                    // If previous turn hit max length and current is "continue" or similar
                    if (prevTurn.hitMaxLength && 
                        (currentTurn.query.toLowerCase() === "continue" || 
                        currentTurn.query.toLowerCase() === "继续" ||
                        currentTurn.query.toLowerCase().includes("continue"))) {
                        currentTurn.isContinuation = true;
                        currentTurn.continuesFrom = i - 1;
                    }
                }
                
                return content;
            }
            
            return getFormattedContent(arguments[0], arguments[1]);
            """
            
            # Execute the script with the extracted code versions and documents
            content_data = await self.session.execute_script(js_script, code_versions, documents_data)
            
            # Check for errors
            if isinstance(content_data, dict) and 'error' in content_data:
                logger.error(f"JavaScript execution error: {content_data['error']}")
                return None
            
            return content_data
            
        except Exception as e:
            logger.error(f"Error extracting page content: {str(e)}")
            return None