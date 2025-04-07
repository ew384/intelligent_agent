import os
import sys
from pathlib import Path
import json
import time
import shutil
import re
import asyncio
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Fix the import path issue by adding the parent directory to sys.path
current_path = Path(__file__).parent.parent
sys.path.append(str(current_path))
print(f"Added to path: {current_path}")

# Import browser session (assuming this is needed, modify as needed for your setup)
try:
    from tool_service.src.tools.browser.browser_session import BrowserSession
except ImportError:
    print("BrowserSession import failed. Using simplified fallback implementation.")
    
    # Define a simple fallback BrowserSession class if the import fails
    class BrowserSession:
        def __init__(self, driver, service, browser_service):
            self.driver = driver
            self.service = service
            self.browser_service = browser_service
        
        async def get_all_tabs(self):
            return self.driver.window_handles
        
        async def get_current_tab(self):
            return self.driver.current_window_handle
        
        async def switch_to_tab(self, handle):
            try:
                self.driver.switch_to.window(handle)
                return True
            except Exception as e:
                print(f"Error switching to tab: {str(e)}")
                return False

# LLM configuration templates
LLM_CONFIGS = {
    "claude": {
        "name": "Claude",
        "url_pattern": "claude.ai",
        "selectors": {
            "new_chat_button": '[data-testid="new-chat"]',
            "prompt_textarea": '[data-testid="chat-input-box"]',
            "send_button": '[data-testid="send-message-button"]',
            "response_container": '[data-message-author-role="assistant"]',
            "upload_button": '[data-testid="image-upload-button"]',
            "file_input": 'input[type="file"]',
        },
        "content_patterns": {
            "user_query": '.bg-bg-300',
            "assistant_response": '.font-claude-message, [class*="tracking"]',
            "code_block": 'pre',
        }
    },
    "chatgpt": {
        "name": "ChatGPT",
        "url_pattern": "chat.openai.com",
        "selectors": {
            "new_chat_button": 'nav a:first-child, button:has-text("New chat")',
            "prompt_textarea": 'textarea[data-id="root"], [contenteditable="true"]',
            "send_button": 'button[data-testid="send-button"], button[aria-label="Send message"]',
            "response_container": '[data-message-author-role="assistant"]',
            "upload_button": 'input[type="file"], [data-testid="upload-button"]',
            "file_input": 'input[type="file"]',
        },
        "content_patterns": {
            "user_query": '.text-base, [data-message-author-role="user"]',
            "assistant_response": '[data-message-author-role="assistant"]',
            "code_block": 'pre',
        }
    },
    "bard": {
        "name": "Bard/Gemini",
        "url_pattern": "gemini.google.com",
        "selectors": {
            "new_chat_button": '[aria-label="New chat"]',
            "prompt_textarea": '[contenteditable="true"]',
            "send_button": '[aria-label="Send"]',
            "response_container": '.gemini-response-container',
            "upload_button": 'input[type="file"]',
            "file_input": 'input[type="file"]',
        },
        "content_patterns": {
            "user_query": '.query-text',
            "assistant_response": '.response-text',
            "code_block": 'pre, .code-block',
        }
    },
    "generic": {
        "name": "Generic LLM Interface",
        "url_pattern": "",
        "selectors": {
            "new_chat_button": 'button:has-text("New"), a:has-text("New")',
            "prompt_textarea": 'textarea, [contenteditable="true"]',
            "send_button": 'button:has-text("Send"), button[type="submit"]',
            "response_container": '.response, .message, .answer',
            "upload_button": 'input[type="file"], [aria-label*="upload" i]',
            "file_input": 'input[type="file"]',
        },
        "content_patterns": {
            "user_query": '.user-message, .query',
            "assistant_response": '.assistant-message, .response, .answer',
            "code_block": 'pre, code, .code-block',
        }
    }
}

async def get_tab_by_url_pattern(browser_session, url_pattern):
    """
    Get the tab handle containing the specified URL pattern
    
    Args:
        browser_session: Browser session instance
        url_pattern: URL pattern (e.g., 'chatgpt.com')
        
    Returns:
        str: The first tab handle matching the URL pattern, or None if not found
    """
    try:
        # Get all tabs
        handles = await browser_session.get_all_tabs()
        if not handles:
            return None
            
        # Save current tab handle to restore later
        current_handle = await browser_session.get_current_tab()
        
        # Search all tabs for matching URL
        matching_handle = None
        
        for handle in handles:
            # Switch to tab
            await browser_session.switch_to_tab(handle)
            
            # Get current URL
            current_url = browser_session.driver.current_url
            
            # Check if URL contains specified pattern
            if url_pattern in current_url:
                matching_handle = handle
                break
        
        # Restore original tab
        if current_handle:
            await browser_session.switch_to_tab(current_handle)
            
        return matching_handle
    except Exception as e:
        print(f"Error getting tab by URL pattern: {str(e)}")
        return None

def analyze_page_selectors(driver, llm_config, output_file=None):
    """
    Analyze the LLM page to find accurate selectors for key elements
    
    Args:
        driver: Selenium WebDriver instance
        llm_config: Configuration for the specific LLM
        output_file: Path to output file for results
    
    Returns:
        Dict containing discovered selectors for key page elements
    """
    if output_file is None:
        output_file = f"{llm_config['name'].lower()}_selectors.txt"
        
    try:
        print(f"Analyzing {llm_config['name']} UI for accurate selectors...")
        
        # Create a simplified JavaScript selector analysis script
        js_script = """
        function findSelectors() {
            // Helper function to check element visibility
            function isVisible(el) {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       parseFloat(style.opacity) > 0 &&
                       el.offsetWidth > 0 && 
                       el.offsetHeight > 0;
            }
            
            // Helper function to get attributes
            function getElementAttrs(element) {
                const result = {};
                const attrs = element.attributes;
                for (let i = 0; i < attrs.length; i++) {
                    result[attrs[i].name] = attrs[i].value;
                }
                return result;
            }
            
            // Helper to generate a selector for an element
            function getSelectorForElement(element) {
                if (element.id) return '#' + element.id;
                
                // Try data attributes
                for (const attr of element.attributes) {
                    if (attr.name.startsWith('data-')) {
                        return `[${attr.name}="${attr.value}"]`;
                    }
                }
                
                // Try classes
                if (element.className && typeof element.className === 'string') {
                    const classes = element.className.split(/\\s+/).filter(Boolean);
                    if (classes.length) return '.' + classes.join('.');
                }
                
                return element.tagName.toLowerCase();
            }
            
            // 1. Find the prompt textarea / input area
            function findPromptTextarea() {
                // Common selectors to try
                const selectors = [
                    'textarea',
                    'textarea[placeholder]',
                    '[contenteditable="true"]',
                    '[data-testid="chat-input-box"]',
                    '[data-testid="message-input"]',
                    '[role="textbox"]'
                ];
                
                for (const selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (isVisible(el)) {
                                // Likely input area is in the bottom part of the screen
                                const rect = el.getBoundingClientRect();
                                if (rect.top > window.innerHeight * 0.5) {
                                    return { 
                                        selector: getSelectorForElement(el),
                                        element: el
                                    };
                                }
                            }
                        }
                    } catch (e) {
                        // Skip this selector if it causes errors
                    }
                }
                
                // Fallback: find any textarea or contenteditable div
                const allTextareas = document.querySelectorAll('textarea');
                for (const el of allTextareas) {
                    if (isVisible(el)) return { 
                        selector: getSelectorForElement(el),
                        element: el
                    };
                }
                
                const allEditableElements = document.querySelectorAll('[contenteditable="true"]');
                for (const el of allEditableElements) {
                    if (isVisible(el)) return { 
                        selector: getSelectorForElement(el),
                        element: el
                    };
                }
                
                return { selector: null, element: null };
            }
            
            // 2. Find the send button
            function findSendButton() {
                // Start by looking near the input element
                const inputResult = findPromptTextarea();
                if (inputResult.element) {
                    const input = inputResult.element;
                    
                    // Look for buttons near the input
                    let currentElement = input;
                    
                    // Try to find parent with buttons
                    while (currentElement && currentElement !== document.body) {
                        const buttons = currentElement.querySelectorAll('button');
                        for (const button of buttons) {
                            if (isVisible(button)) {
                                // Check if it looks like a send button
                                const text = button.textContent.trim().toLowerCase();
                                if (text === 'send' || text === 'submit' || button.ariaLabel?.toLowerCase().includes('send')) {
                                    return { 
                                        selector: getSelectorForElement(button),
                                        element: button
                                    };
                                }
                                
                                // Buttons with typical send icons often don't have text
                                if (!text && button.querySelector('svg')) {
                                    return { 
                                        selector: getSelectorForElement(button),
                                        element: button
                                    };
                                }
                            }
                        }
                        currentElement = currentElement.parentElement;
                    }
                }
                
                // Direct selectors
                const sendButtonSelectors = [
                    '[data-testid="send-button"]',
                    '[data-testid="send-message-button"]',
                    'button[aria-label="Send message"]',
                    'button.send-button'
                ];
                
                for (const selector of sendButtonSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (isVisible(el)) {
                                return { 
                                    selector: getSelectorForElement(el),
                                    element: el
                                };
                            }
                        }
                    } catch (e) {
                        // Skip this selector if it causes errors
                    }
                }
                
                return { selector: null, element: null };
            }
            
            // 3. Find response container
            function findResponseContainer() {
                // Common selectors to try
                const selectors = [
                    '[data-message-author-role="assistant"]',
                    '.assistant-message',
                    '.response-container',
                    '.gemini-response-container',
                    '.font-claude-message',
                    '.response'
                ];
                
                for (const selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (isVisible(el)) {
                                return { 
                                    selector: getSelectorForElement(el),
                                    element: el
                                };
                            }
                        }
                    } catch (e) {
                        // Skip this selector if it causes errors
                    }
                }
                
                // Look for elements with AI phrases
                const textPatterns = [
                    'I am an AI',
                    'As an AI',
                    'I don\\'t have personal',
                    'I don\\'t have access'
                ];
                
                for (const pattern of textPatterns) {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {
                        const node = walker.currentNode;
                        if (node.textContent.includes(pattern)) {
                            // Find parent div or similar container
                            let parent = node.parentElement;
                            while (parent && parent !== document.body) {
                                if (parent.tagName === 'DIV' || parent.tagName === 'ARTICLE' || parent.tagName === 'SECTION') {
                                    if (parent.textContent.length > 100) {
                                        return { 
                                            selector: getSelectorForElement(parent),
                                            element: parent
                                        };
                                    }
                                }
                                parent = parent.parentElement;
                            }
                        }
                    }
                }
                
                return { selector: null, element: null };
            }
            
            // 4. Find new chat button
            function findNewChatButton() {
                // Common selectors to try
                const selectors = [
                    '[data-testid="new-chat"]',
                    'button[data-testid="new-chat"]',
                    'a[href="/new"]',
                    '.new-chat',
                    'nav a:first-child',
                    'nav button:first-child'
                ];
                
                for (const selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (isVisible(el)) {
                                return { 
                                    selector: getSelectorForElement(el),
                                    element: el
                                };
                            }
                        }
                    } catch (e) {
                        // Skip this selector if it causes errors
                    }
                }
                
                // Look for buttons/links with "new chat" text
                const allButtons = document.querySelectorAll('button, a');
                for (const button of allButtons) {
                    if (isVisible(button)) {
                        const text = button.textContent.trim().toLowerCase();
                        if (text.includes('new chat') || text === 'new') {
                            return { 
                                selector: getSelectorForElement(button),
                                element: button
                            };
                        }
                    }
                }
                
                return { selector: null, element: null };
            }
            
            // 5. Find file upload elements
            function findFileUpload() {
                // Look for file inputs
                const fileInput = document.querySelector('input[type="file"]');
                if (fileInput) {
                    return { 
                        fileInput: getSelectorForElement(fileInput),
                        uploadButton: null
                    };
                }
                
                // Look for upload buttons
                const uploadSelectors = [
                    '[data-testid="image-upload-button"]',
                    '[data-testid="upload-button"]',
                    '[data-testid="file-upload-button"]',
                    '[aria-label*="upload" i]'
                ];
                
                for (const selector of uploadSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (isVisible(el)) {
                                return { 
                                    fileInput: null, 
                                    uploadButton: getSelectorForElement(el)
                                };
                            }
                        }
                    } catch (e) {
                        // Skip this selector if it causes errors
                    }
                }
                
                // Look for buttons with upload text
                const allButtons = document.querySelectorAll('button');
                for (const button of allButtons) {
                    if (isVisible(button)) {
                        const text = button.textContent.trim().toLowerCase();
                        if (text.includes('upload') || text.includes('attach')) {
                            return { 
                                fileInput: null,
                                uploadButton: getSelectorForElement(button)
                            };
                        }
                    }
                }
                
                return { fileInput: null, uploadButton: null };
            }
            
            // Return all selectors
            return {
                promptTextarea: findPromptTextarea().selector,
                sendButton: findSendButton().selector,
                responseContainer: findResponseContainer().selector,
                newChatButton: findNewChatButton().selector,
                fileUpload: findFileUpload()
            };
        }
        
        return findSelectors();
        """
        
        # Execute the JavaScript to analyze selectors
        selector_data = driver.execute_script(js_script)
        
        # Process the results
        best_selectors = {
            'new_chat_button': selector_data.get('newChatButton') or llm_config['selectors']['new_chat_button'],
            'prompt_textarea': selector_data.get('promptTextarea') or llm_config['selectors']['prompt_textarea'],
            'send_button': selector_data.get('sendButton') or llm_config['selectors']['send_button'],
            'response_container': selector_data.get('responseContainer') or llm_config['selectors']['response_container'],
            'upload_button': selector_data.get('fileUpload', {}).get('uploadButton') or llm_config['selectors']['upload_button'],
            'file_input': selector_data.get('fileUpload', {}).get('fileInput') or llm_config['selectors']['file_input']
        }
        
        # Write results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {llm_config['name']} UI Selectors Analysis\n")
            f.write(f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Write best selectors
            f.write("## Best Selectors\n\n")
            f.write("```python\n")
            f.write(f"{llm_config['name'].upper()}_SELECTORS = {{\n")
            for key, selector in best_selectors.items():
                if selector:
                    f.write(f"    '{key}': '{selector}',\n")
                else:
                    f.write(f"    '{key}': None,  # Not found\n")
            f.write("}\n")
            f.write("```\n\n")
            
            # Write updated selectors
            f.write("## Complete Updated LLM Selectors\n\n")
            f.write("```python\n")
            f.write(f"# Updated {llm_config['name']} web interface selectors\n")
            f.write(f"{llm_config['name'].upper()}_SELECTORS = {{\n")
            f.write("    # Core UI elements\n")
            
            new_chat = best_selectors.get('new_chat_button') or llm_config['selectors']['new_chat_button']
            f.write(f"    'new_chat_button': '{new_chat}',\n")
            
            textarea = best_selectors.get('prompt_textarea') or llm_config['selectors']['prompt_textarea']
            f.write(f"    'prompt_textarea': '{textarea}',\n")
            
            send = best_selectors.get('send_button') or llm_config['selectors']['send_button']
            f.write(f"    'send_button': '{send}',\n")
            
            response = best_selectors.get('response_container') or llm_config['selectors']['response_container']
            f.write(f"    'response_container': '{response}',\n")
            
            f.write("\n    # File upload\n")
            upload = best_selectors.get('upload_button') or llm_config['selectors']['upload_button']
            f.write(f"    'upload_button': '{upload}',\n")
            
            file_input = best_selectors.get('file_input') or llm_config['selectors']['file_input']
            f.write(f"    'file_input': '{file_input}',\n")
            
            f.write("}\n")
            f.write("```\n")
        
        print(f"Selector analysis complete. Results saved to {output_file}")
        print("\nBest selectors found:")
        for key, selector in best_selectors.items():
            if selector:
                print(f"- {key}: {selector}")
            else:
                print(f"- {key}: Not found")
        
        return {
            'best_selectors': best_selectors,
            'all_selectors': selector_data
        }
        
    except Exception as e:
        print(f"Error analyzing page selectors: {str(e)}")
        # Try to write error to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# ERROR: {str(e)}\n")
                f.write(f"Failed to analyze {llm_config['name']} UI selectors.")
        except:
            pass
        
        return {
            'error': str(e)
        }

def analyze_page_structure(driver, llm_config, filename=None):
    """
    Analyze page structure and save element information to file
    
    Args:
        driver: Selenium WebDriver instance
        llm_config: Configuration for the specific LLM
        filename: Output filename (optional)
    
    Returns:
        Dict containing page structure analysis
    """
    if filename is None:
        filename = f"{llm_config['name'].lower()}_page_structure.txt"
        
    try:
        # Use JavaScript to analyze page structure
        js_script = """
        function analyzePageStructure() {
            // Store analysis results
            let analysis = {
                tagCounts: {},
                classCounts: {},
                idCounts: {},
                messageElements: [],
                codeBlocks: [],
                sampleTexts: [],
                documentSections: []
            };
            
            // Analyze all elements
            function analyzeElement(element, depth = 0) {
                // Record tag type
                const tagName = element.tagName.toLowerCase();
                analysis.tagCounts[tagName] = (analysis.tagCounts[tagName] || 0) + 1;
                
                // Record class names
                if (element.className && typeof element.className === 'string') {
                    const classes = element.className.split(/\\s+/);
                    classes.forEach(cls => {
                        if (cls) {
                            analysis.classCounts[cls] = (analysis.classCounts[cls] || 0) + 1;
                        }
                    });
                }
                
                // Record IDs
                if (element.id) {
                    analysis.idCounts[element.id] = (analysis.idCounts[element.id] || 0) + 1;
                }
                
                // Check if it might be a message element
                const text = element.textContent.trim();
                if (text.length > 10 && depth < 5) {
                    const rect = element.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 30) {
                        // Check if content looks like a message
                        const isPossibleMessage = 
                            (element.tagName === 'DIV' || element.tagName === 'P') &&
                            text.length < 1000 &&
                            !element.querySelector('pre') && // Doesn't contain code blocks
                            !element.classList.contains('header') &&
                            !element.classList.contains('footer') &&
                            !element.id.includes('header') &&
                            !element.id.includes('footer');
                        
                        if (isPossibleMessage) {
                            analysis.messageElements.push({
                                tag: tagName,
                                id: element.id || '',
                                classes: element.className || '',
                                text: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
                                path: getElementPath(element),
                                rectangle: {
                                    top: rect.top,
                                    left: rect.left,
                                    width: rect.width,
                                    height: rect.height
                                }
                            });
                        }
                        
                        // Sample some text content
                        if (analysis.sampleTexts.length < 20 && text.length > 20) {
                            analysis.sampleTexts.push({
                                tag: tagName,
                                id: element.id || '',
                                classes: element.className || '',
                                text: text.substring(0, 150) + (text.length > 150 ? '...' : ''),
                                path: getElementPath(element)
                            });
                        }
                    }
                }
                
                // Check if it's a code block
                if (tagName === 'pre' || tagName === 'code' || element.classList.contains('code-block')) {
                    analysis.codeBlocks.push({
                        tag: tagName,
                        id: element.id || '',
                        classes: element.className || '',
                        text: element.textContent.substring(0, 200) + (element.textContent.length > 200 ? '...' : ''),
                        path: getElementPath(element)
                    });
                }
                
                // Check if it's a document section
                if (element.classList.contains('document') || 
                    element.id.includes('document') || 
                    tagName === 'article' ||
                    element.classList.contains('sidebar-content')) {
                    analysis.documentSections.push({
                        tag: tagName,
                        id: element.id || '',
                        classes: element.className || '',
                        text: element.textContent.substring(0, 200) + (element.textContent.length > 200 ? '...' : ''),
                        path: getElementPath(element),
                        childElements: Array.from(element.children).map(child => ({
                            tag: child.tagName.toLowerCase(),
                            classes: child.className || '',
                            text: child.textContent.trim().substring(0, 100) + (child.textContent.length > 100 ? '...' : '')
                        }))
                    });
                }
                
                // Recursively analyze child elements
                for (const child of element.children) {
                    analyzeElement(child, depth + 1);
                }
            }
            
            // Get element's CSS selector path
            function getElementPath(element) {
                if (!element || element === document.body) return 'body';
                
                let path = '';
                let current = element;
                
                while (current && current !== document.body) {
                    let selector = current.tagName.toLowerCase();
                    
                    if (current.id) {
                        selector += '#' + current.id;
                    } else if (current.className && typeof current.className === 'string') {
                        selector += '.' + current.className.trim().replace(/\\s+/g, '.');
                    }
                    
                    path = selector + (path ? ' > ' + path : '');
                    current = current.parentElement;
                }
                
                return path;
            }
            
            // Specially analyze potential conversation structure
            function analyzeConversationStructure() {
                // Try different selectors to find message container
                const selectors = [
                    '.conversation', '.chat', '.messages', '.message-container',
                    'main', 'article', '.content', '[role="main"]'
                ];
                
                let messageContainer = null;
                
                for (const selector of selectors) {
                    const container = document.querySelector(selector);
                    if (container) {
                        messageContainer = container;
                        break;
                    }
                }
                
                if (!messageContainer) {
                    // If no clear container found, try to infer based on structure
                    const elements = document.querySelectorAll('div > div > div');
                    for (const el of elements) {
                        const children = el.children;
                        if (children.length > 3) {
                            // Might be a message list
                            messageContainer = el;
                            break;
                        }
                    }
                }
                
                if (messageContainer) {
                    analysis.messageContainer = {
                        tag: messageContainer.tagName.toLowerCase(),
                        id: messageContainer.id || '',
                        classes: messageContainer.className || '',
                        path: getElementPath(messageContainer),
                        childCount: messageContainer.children.length
                    };
                    
                    // Analyze child elements
                    const children = Array.from(messageContainer.children);
                    analysis.conversationElements = children.map(child => ({
                        tag: child.tagName.toLowerCase(),
                        id: child.id || '',
                        classes: child.className || '',
                        text: child.textContent.trim().substring(0, 100) + (child.textContent.length > 100 ? '...' : ''),
                        path: getElementPath(child),
                        rect: {
                            top: child.getBoundingClientRect().top,
                            height: child.getBoundingClientRect().height
                        }
                    }));
                }
            }
            
            // Find code examples and their explanations
            function findCodeAndExplanations() {
                const codeElements = document.querySelectorAll('pre, code, .code-block');
                
                analysis.codeWithExplanations = [];
                
                codeElements.forEach(codeEl => {
                    // Look for explanations before and after
                    let explanation = '';
                    let prevSibling = codeEl.previousElementSibling;
                    let nextSibling = codeEl.nextElementSibling;
                    
                    // Check previous sibling
                    if (prevSibling && !prevSibling.tagName.match(/^(pre|code)$/i)) {
                        explanation += "Preceding explanation: " + prevSibling.textContent.trim() + "\\n";
                    }
                    
                    // Check next sibling
                    if (nextSibling && !nextSibling.tagName.match(/^(pre|code)$/i)) {
                        explanation += "Following explanation: " + nextSibling.textContent.trim();
                    }
                    
                    // Check list elements (possible usage instructions)
                    let listElement = codeEl.nextElementSibling;
                    while (listElement) {
                        if (listElement.tagName === 'OL' || listElement.tagName === 'UL') {
                            explanation += "\\nList instructions:\\n" + listElement.textContent.trim();
                            break;
                        }
                        listElement = listElement.nextElementSibling;
                    }
                    
                    analysis.codeWithExplanations.push({
                        code: {
                            tag: codeEl.tagName.toLowerCase(),
                            id: codeEl.id || '',
                            classes: codeEl.className || '',
                            text: codeEl.textContent.substring(0, 150) + (codeEl.textContent.length > 150 ? '...' : ''),
                            path: getElementPath(codeEl)
                        },
                        explanation: explanation
                    });
                });
            }
            
            // Analyze buttons and interactive elements
            function analyzeInteractiveElements() {
                const buttons = document.querySelectorAll('button, [role="button"], .button');
                
                analysis.interactiveElements = Array.from(buttons).map(button => ({
                    tag: button.tagName.toLowerCase(),
                    id: button.id || '',
                    classes: button.className || '',
                    text: button.textContent.trim(),
                    path: getElementPath(button)
                }));
            }
            
            // Start analysis
            analyzeElement(document.body);
            analyzeConversationStructure();
            findCodeAndExplanations();
            analyzeInteractiveElements();
            
            return analysis;
        }
        
        return analyzePageStructure();
        """
        
        analysis_data = driver.execute_script(js_script)
        
        # Save analysis results to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{llm_config['name']} Page Structure Analysis\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("Common Tag Statistics:\n")
            f.write("=" * 80 + "\n\n")
            
            for tag, count in sorted(analysis_data['tagCounts'].items(), key=lambda x: x[1], reverse=True):
                f.write(f"{tag}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Common Class Statistics:\n")
            f.write("=" * 80 + "\n\n")
            
            for cls, count in sorted(analysis_data['classCounts'].items(), key=lambda x: x[1], reverse=True)[:50]:
                f.write(f"{cls}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("ID Statistics:\n")
            f.write("=" * 80 + "\n\n")
            
            for id_name, count in sorted(analysis_data['idCounts'].items(), key=lambda x: x[1], reverse=True)[:50]:
                f.write(f"{id_name}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Possible Message Elements:\n")
            f.write("=" * 80 + "\n\n")
            
            for msg_element in analysis_data['messageElements']:
                f.write(f"Tag: {msg_element['tag']}\n")
                f.write(f"ID: {msg_element['id']}\n")
                f.write(f"Classes: {msg_element['classes']}\n")
                f.write(f"Path: {msg_element['path']}\n")
                f.write(f"Position: Top={msg_element['rectangle']['top']}, Left={msg_element['rectangle']['left']}, Width={msg_element['rectangle']['width']}, Height={msg_element['rectangle']['height']}\n")
                f.write(f"Text: {msg_element['text']}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Code Blocks:\n")
            f.write("=" * 80 + "\n\n")
            
            for code_block in analysis_data['codeBlocks']:
                f.write(f"Tag: {code_block['tag']}\n")
                f.write(f"ID: {code_block['id']}\n")
                f.write(f"Classes: {code_block['classes']}\n")
                f.write(f"Path: {code_block['path']}\n")
                f.write(f"Code Sample: {code_block['text']}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Code with Explanations:\n")
            f.write("=" * 80 + "\n\n")
            
            for item in analysis_data['codeWithExplanations']:
                f.write(f"Code Path: {item['code']['path']}\n")
                f.write(f"Code Sample: {item['code']['text']}\n")
                if item['explanation']:
                    f.write(f"Related Explanation: {item['explanation']}\n")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Document Sections:\n")
            f.write("=" * 80 + "\n\n")
            
            for doc in analysis_data['documentSections']:
                f.write(f"Tag: {doc['tag']}\n")
                f.write(f"ID: {doc['id']}\n")
                f.write(f"Classes: {doc['classes']}\n")
                f.write(f"Path: {doc['path']}\n")
                f.write(f"Text Sample: {doc['text']}\n")
                f.write("Child Elements:\n")
                for child in doc['childElements']:
                    f.write(f"  - {child['tag']} ({child['classes']}): {child['text']}\n")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Interactive Elements:\n")
            f.write("=" * 80 + "\n\n")
            
            for button in analysis_data['interactiveElements']:
                f.write(f"Tag: {button['tag']}\n")
                f.write(f"ID: {button['id']}\n")
                f.write(f"Classes: {button['classes']}\n")
                f.write(f"Path: {button['path']}\n")
                f.write(f"Text: {button['text']}\n\n")
            
            # Write conversation structure analysis
            if 'messageContainer' in analysis_data:
                f.write("\n" + "=" * 80 + "\n")
                f.write("Conversation Container:\n")
                f.write("=" * 80 + "\n\n")
                
                container = analysis_data['messageContainer']
                f.write(f"Tag: {container['tag']}\n")
                f.write(f"ID: {container['id']}\n")
                f.write(f"Classes: {container['classes']}\n")
                f.write(f"Path: {container['path']}\n")
                f.write(f"Child Element Count: {container['childCount']}\n\n")
                
                f.write("Conversation Elements:\n")
                for i, elem in enumerate(analysis_data.get('conversationElements', [])):
                    f.write(f"Element {i+1}:\n")
                    f.write(f"  Tag: {elem['tag']}\n")
                    f.write(f"  ID: {elem['id']}\n")
                    f.write(f"  Classes: {elem['classes']}\n")
                    f.write(f"  Path: {elem['path']}\n")
                    f.write(f"  Position: Top={elem['rect']['top']}, Height={elem['rect']['height']}\n")
                    f.write(f"  Text: {elem['text']}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("Text Samples:\n")
            f.write("=" * 80 + "\n\n")
            
            for i, sample in enumerate(analysis_data['sampleTexts']):
                f.write(f"Sample {i+1}:\n")
                f.write(f"Tag: {sample['tag']}\n")
                f.write(f"ID: {sample['id']}\n")
                f.write(f"Classes: {sample['classes']}\n")
                f.write(f"Path: {sample['path']}\n")
                f.write(f"Text: {sample['text']}\n\n")
        
        print(f"Page structure analysis saved to {filename}")
        return analysis_data
    
    except Exception as e:
        print(f"Error analyzing page structure: {str(e)}")
        return None

def extract_page_content(driver, llm_config, filename=None):
    """
    Extract page content including conversation, code blocks, and document references
    
    Args:
        driver: Selenium WebDriver instance
        llm_config: Configuration for the specific LLM
        filename: Output filename (optional)
    
    Returns:
        Dict containing extracted content
    """
    if filename is None:
        filename = f"{llm_config['name'].lower()}_content.txt"
        
    try:
        print(f"Extracting content from {llm_config['name']} chat interface...")
        
        # First, extract code versions using a separate JavaScript function
        js_code_extraction = """
        async function extractAllCodeVersions() {
            // Map to store all code versions
            const codeVersions = new Map();
            
            // Find all code version buttons
            const codeButtons = Array.from(document.querySelectorAll('button.flex.text-left.font-styrene.rounded-xl'));
            const codeButtonsFiltered = codeButtons.filter(btn => 
                btn.textContent.includes('Code') && 
                (btn.textContent.includes('Version') || btn.textContent.includes('∙'))
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
                        const codeElement = sidebarCodeContainer.querySelector('code.language-python');
                        if (codeElement) {
                            const fullCodeText = codeElement.textContent.trim();
                            if (fullCodeText) {
                                // Store code with its version info
                                codeVersions.set(buttonText, {
                                    language: 'python',
                                    code: fullCodeText,
                                    buttonLabel: buttonText,
                                    version: versionLabel
                                });
                                console.log(`Extracted code for: ${buttonText} (${versionLabel})`);
                            }
                        }
                    }
                } catch (buttonError) {
                    console.error("Error processing button:", buttonError);
                }
            }
            
            return Array.from(codeVersions.entries());
        }
        
        return extractAllCodeVersions();
        """
        
        # Execute the code extraction script
        code_versions = driver.execute_script(js_code_extraction)
        
        # Now extract the conversation structure
        js_content_extraction = """
        function getFormattedContent() {
            // Store content
            let content = {
                conversationTurns: [],
                uiElements: []
            };
            
            // Get external code versions map
            const codeVersionsMap = new Map(arguments[0]);
            
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
                                if (buttonText.includes('Code') && (buttonText.includes('Version') || buttonText.includes('∙'))) {
                                    // Look for the corresponding code in our map
                                    if (codeVersionsMap.has(buttonText)) {
                                        const codeData = codeVersionsMap.get(buttonText);
                                        currentTurn.codeBlocks.push({
                                            language: codeData.language || 'python',
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
                        
                        // 1. Find inline code blocks (not folded ones)
                        const codeBlocks = element.querySelectorAll('pre');
                        for (const codeBlock of codeBlocks) {
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
                                        language: language || 'python', // Default to python
                                        code: codeText,
                                        isInline: true
                                    });
                                }
                            }
                        }
                        
                        // 2. Find document references
                        const docButtons = element.querySelectorAll('button[class*="font-styrene"][class*="border-0"]');
                        for (const docButton of docButtons) {
                            // Extract document title
                            const docTitle = docButton.textContent.replace(/Click to open document.*$/, '').trim();
                            
                            // Try to find document content
                            let docContent = [];
                            
                            // Check if there's a sidebar on the page that might contain document content
                            const sidebarContent = document.querySelector('div[class*="fixed"][class*="right-0"][class*="flex"][class*="w-full"]');
                            if (sidebarContent) {
                                // Extract paragraphs from the sidebar
                                const docTextElements = sidebarContent.querySelectorAll('p');
                                for (const textEl of docTextElements) {
                                    docContent.push(textEl.textContent.trim());
                                }
                            }
                            
                            // Add the document to the current turn
                            if (docTitle) {
                                currentTurn.documents.push({
                                    title: docTitle,
                                    content: docContent
                                });
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
        
        return getFormattedContent(arguments[0]);
        """
        
        # Execute the JavaScript with the code versions as argument
        content_data = driver.execute_script(js_content_extraction, code_versions)
        
        # Check for errors
        if isinstance(content_data, dict) and 'error' in content_data:
            print(f"JavaScript execution error: {content_data['error']}")
            return None
        
        # Save extracted content to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{llm_config['name']} Conversation Content\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Write conversation turns
            for turn in content_data.get('conversationTurns', []):
                f.write("=" * 80 + "\n")
                f.write(f"TURN {turn['turnIndex'] + 1}: USER QUERY\n")
                f.write("=" * 80 + "\n\n")
                
                # Write user query
                f.write(turn['query'] + "\n\n")
                
                f.write("-" * 80 + "\n")
                f.write("ASSISTANT RESPONSE:\n")
                f.write("-" * 80 + "\n\n")
                
                # Write assistant responses
                for response in turn.get('responses', []):
                    f.write(response + "\n\n")
                
                # Write code blocks
                if turn.get('codeBlocks'):
                    f.write("-" * 80 + "\n")
                    f.write("CODE BLOCKS:\n")
                    f.write("-" * 80 + "\n\n")
                    
                    for i, code_block in enumerate(turn['codeBlocks']):
                        f.write(f"Code Block {i+1}")
                        
                        if 'version' in code_block:
                            f.write(f" ({code_block['version']})")
                        
                        if 'language' in code_block:
                            f.write(f" - {code_block['language']}")
                            
                        f.write(":\n\n")
                        f.write("```\n")
                        f.write(code_block['code'] + "\n")
                        f.write("```\n\n")
                
                # Write code explanations
                if turn.get('codeExplanations'):
                    f.write("-" * 80 + "\n")
                    f.write("CODE EXPLANATIONS / INSTRUCTIONS:\n")
                    f.write("-" * 80 + "\n\n")
                    
                    for i, explanation in enumerate(turn['codeExplanations']):
                        f.write(f"Explanation {i+1}:\n")
                        f.write(explanation + "\n\n")
                
                # Write document references
                if turn.get('documents'):
                    f.write("-" * 80 + "\n")
                    f.write("DOCUMENT REFERENCES:\n")
                    f.write("-" * 80 + "\n\n")
                    
                    for i, doc in enumerate(turn['documents']):
                        f.write(f"Document {i+1}: {doc['title']}\n")
                        
                        if doc.get('content'):
                            f.write("Content sample:\n")
                            content_sample = "\n".join(doc['content'][:3])
                            if len(doc['content']) > 3:
                                content_sample += "\n...(truncated)..."
                            f.write(content_sample + "\n\n")
                
                f.write("\n\n")
        
        print(f"Content extraction complete. Results saved to {filename}")
        return content_data
        
    except Exception as e:
        print(f"Error extracting page content: {str(e)}")
        
        # Try to write error to file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"ERROR: {str(e)}\n")
                f.write(f"Failed to extract {llm_config['name']} content.")
        except:
            pass
            
        return None

def create_output_dir(llm_name):
    """Create output directory for specific LLM"""
    output_dir = f"llm_page_analysis_{llm_name.lower()}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def detect_llm_provider(driver):
    """
    Detect which LLM provider's interface we're looking at
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        str: LLM provider key ('claude', 'chatgpt', 'bard', etc.) or 'generic'
    """
    try:
        # Check URL for obvious patterns
        current_url = driver.current_url.lower()
        
        if 'claude.ai' in current_url:
            return 'claude'
        elif 'chat.openai.com' in current_url:
            return 'chatgpt'
        elif 'gemini.google.com' in current_url or 'bard.google.com' in current_url:
            return 'bard'
        
        # Check page content for LLM-specific elements
        page_source = driver.page_source.lower()
        page_title = driver.title.lower()
        
        if 'claude' in page_title or 'anthropic' in page_title or 'claude' in page_source:
            return 'claude'
        elif 'chatgpt' in page_title or 'openai' in page_title or 'gpt' in page_source:
            return 'chatgpt'
        elif 'gemini' in page_title or 'bard' in page_title or 'google ai' in page_title:
            return 'bard'
        
        # If still not detected, try browser structure analysis
        for llm_key, config in LLM_CONFIGS.items():
            if llm_key == 'generic':
                continue
                
            # Check if selectors match
            matches = 0
            for selector_key, selector in config['selectors'].items():
                try:
                    elements = driver.find_elements("css selector", selector)
                    if elements:
                        matches += 1
                except:
                    continue
            
            # If we found multiple matches, this is likely our LLM
            if matches >= 2:
                return llm_key
        
        # Default to generic if we can't identify
        return 'generic'
    except Exception as e:
        print(f"Error detecting LLM provider: {str(e)}")
        return 'generic'

def main():
    """Main function to run the LLM page analyzer"""
    parser = argparse.ArgumentParser(description='Analyze LLM web interfaces')
    parser.add_argument('--url', type=str, help='URL pattern to find (e.g., "claude.ai", "chatgpt.com")', default=None)
    parser.add_argument('--llm', type=str, help='LLM provider (claude, chatgpt, bard, or generic)', default=None)
    parser.add_argument('--browser-port', type=int, help='Chrome debugging port', default=54805)
    parser.add_argument('--chromedriver', type=str, help='Path to chromedriver', default=None)
    parser.add_argument('--output-dir', type=str, help='Output directory', default=None)
    args = parser.parse_args()
    
    try:
        # Set up Chrome driver
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{args.browser_port}")
        
        if args.chromedriver:
            service = Service(args.chromedriver)
        else:
            # Try to use webdriver-manager or look for chromedriver in common locations
            try:
                service = Service(ChromeDriverManager().install())
            except Exception as e:
                print(f"Error using ChromeDriverManager: {e}")
                
                # Check common locations
                common_paths = [
                    "/home/endian/.local/share/undetected_chromedriver/undetected_chromedriver",  # From original code
                ]
                
                for path in common_paths:
                    expanded_path = os.path.expanduser(path)
                    if os.path.exists(expanded_path):
                        service = Service(expanded_path)
                        break
                else:
                    raise Exception("Could not find chromedriver. Please specify path with --chromedriver.")
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Create BrowserSession
        class SimpleBrowserService:
            def __init__(self):
                self.screenshots_dir = None
                self.cookies_manager = None
        
        browser_service = SimpleBrowserService()
        browser_session = BrowserSession(driver, service, browser_service)
        
        # If URL pattern is provided, find and switch to that tab
        if args.url:
            print(f"Looking for tab containing {args.url}...")
            loop = asyncio.get_event_loop()
            target_handle = loop.run_until_complete(get_tab_by_url_pattern(browser_session, args.url))
            
            if target_handle:
                print(f"Found tab containing {args.url}: {target_handle}")
                # Switch to tab
                loop.run_until_complete(browser_session.switch_to_tab(target_handle))
            else:
                print(f"No tab found containing {args.url}")
                return None
        
        # Print all tabs info (for debugging)
        loop = asyncio.get_event_loop()
        all_handles = loop.run_until_complete(browser_session.get_all_tabs())
        print(f"All tabs: {all_handles}")
        
        # Detect LLM provider if not specified
        llm_key = args.llm if args.llm else detect_llm_provider(driver)
        print(f"Detected LLM provider: {llm_key}")
        
        # Get LLM config
        if llm_key in LLM_CONFIGS:
            llm_config = LLM_CONFIGS[llm_key]
        else:
            print(f"Unknown LLM provider: {llm_key}. Using generic configuration.")
            llm_config = LLM_CONFIGS['generic']
            llm_config['name'] = llm_key.capitalize()
        
        # Create output directory
        output_dir = args.output_dir if args.output_dir else create_output_dir(llm_config['name'])
        print(f"Output directory: {output_dir}")
        
        # Extract page content
        print("\nExtracting page content...")
        content_file = os.path.join(output_dir, f"{llm_config['name'].lower()}_content.txt")
        extract_page_content(driver, llm_config, content_file)
        
        # Analyze page structure
        print("\nAnalyzing page structure...")
        structure_file = os.path.join(output_dir, f"{llm_config['name'].lower()}_structure.txt")
        analyze_page_structure(driver, llm_config, structure_file)
        
        # Analyze page selectors
        print("\nAnalyzing page selectors...")
        selectors_file = os.path.join(output_dir, f"{llm_config['name'].lower()}_selectors.txt")
        analyze_page_selectors(driver, llm_config, selectors_file)
        
        print("\nAnalysis complete!")
        return True
    
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
