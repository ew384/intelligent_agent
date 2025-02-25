# tool-service/src/tools/llm/claude/auth_handler.py
from typing import Dict, Any, AsyncGenerator
import logging
import time
import json
from playwright.async_api import Page, TimeoutError
from ...common.cookies_manager import CookiesManager
from .selectors import CLAUDE_SELECTORS

logger = logging.getLogger(__name__)

class ClaudeAuthHandler:
    """Handles authentication and interaction with Claude AI"""
    
    def __init__(self, page: Page):
        """
        Initialize Claude auth handler
        
        Args:
            page: Playwright page object
        """
        self.page = page
        self.cookies_manager = None  # Will be set by the service
        self.domain = "claude.ai"
        self.logged_in = False
        
    async def handle_login(self) -> Dict[str, Any]:
        """
        Handle the login process for Claude
        
        Returns:
            Dict with login status
        """
        try:
            # First try to use cookies for login
            if self.cookies_manager:
                await self._restore_session()
                
                # Check if we're already logged in
                is_logged_in = await self._check_logged_in()
                if is_logged_in:
                    self.logged_in = True
                    logger.info("Successfully logged in to Claude with cookies")
                    return {"status": "success", "message": "Logged in with cookies"}
            
            # If cookie login failed, we'd need to handle manual login
            logger.info("Cookie login failed, waiting for manual login")
            
            # Wait for manual login (this is necessary because Claude uses OAuth)
            is_logged_in = await self._wait_for_manual_login()
            if is_logged_in:
                self.logged_in = True
                
                # Save cookies after successful login
                if self.cookies_manager:
                    await self._save_session()
                    
                return {"status": "success", "message": "Logged in manually"}
            else:
                return {"status": "error", "message": "Login timeout"}
                
        except Exception as e:
            logger.error(f"Claude login error: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    async def _restore_session(self) -> bool:
        """
        Try to restore session using cookies
        
        Returns:
            Boolean indicating success
        """
        if not self.cookies_manager:
            return False
            
        # Load cookies for Claude domain
        cookies = self.cookies_manager.load_cookies(self.domain)
        if not cookies:
            return False
            
        # Add cookies to the browser
        await self.page.context.add_cookies(cookies)
        
        # Refresh the page to apply cookies
        await self.page.goto("https://claude.ai")
        
        return True
        
    async def _save_session(self) -> bool:
        """
        Save current session cookies
        
        Returns:
            Boolean indicating success
        """
        if not self.cookies_manager:
            return False
            
        cookies = await self.page.context.cookies()
        return self.cookies_manager.save_cookies(self.domain, cookies)
        
    async def _check_logged_in(self) -> bool:
        """
        Check if we're currently logged in to Claude
        
        Returns:
            Boolean indicating logged in status
        """
        try:
            # Wait for either the login button (not logged in) or chat button (logged in)
            logged_in = await self.page.wait_for_selector(
                CLAUDE_SELECTORS['logged_in_indicator'],
                timeout=5000
            )
            return logged_in is not None
        except TimeoutError:
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
            # Display message on page to alert user
            await self.page.evaluate("""() => {
                const div = document.createElement('div');
                div.id = 'login-message';
                div.style = 'position: fixed; top: 0; left: 0; right: 0; background: red; color: white; padding: 10px; text-align: center; z-index: 9999;';
                div.innerText = 'Please log in to Claude manually';
                document.body.appendChild(div);
            }""")
            
            # Wait for logged in indicator
            await self.page.wait_for_selector(
                CLAUDE_SELECTORS['logged_in_indicator'],
                timeout=timeout
            )
            
            # Remove the message
            await self.page.evaluate("""() => {
                const div = document.getElementById('login-message');
                if (div) div.remove();
            }""")
            
            return True
            
        except TimeoutError:
            return False
            
    async def handle_chat_stream(self, image_path: str = None, prompt: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle chat interaction with Claude
        
        Args:
            image_path: Optional path to image to upload
            prompt: Text prompt to send
            
        Yields:
            Dict containing response chunks
        """
        try:
            if not self.logged_in:
                yield {"status": "error", "message": "Not logged in"}
                return
                
            # Start a new chat if needed
            new_chat_button = await self.page.query_selector(CLAUDE_SELECTORS['new_chat_button'])
            if new_chat_button:
                await new_chat_button.click()
                
            # Upload image if provided
            if image_path:
                await self._upload_image(image_path)
                
            # Enter prompt text
            if prompt:
                await self.page.fill(CLAUDE_SELECTORS['prompt_textarea'], prompt)
                
                # Send the message
                await self.page.click(CLAUDE_SELECTORS['send_button'])
                
                # Wait for response to start
                await self.page.wait_for_selector(CLAUDE_SELECTORS['response_container'], timeout=60000)
                
                # Monitor response until it's complete
                response_text = ""
                is_complete = False
                
                while not is_complete:
                    # Get current response text
                    response_element = await self.page.query_selector(CLAUDE_SELECTORS['response_container'])
                    new_text = await response_element.text_content()
                    
                    # If text has changed, yield the new part
                    if new_text != response_text:
                        # Yield only the new content
                        new_content = new_text[len(response_text):]
                        response_text = new_text
                        
                        yield {
                            "status": "streaming",
                            "content": new_content,
                            "complete": False
                        }
                    
                    # Check if response is complete
                    thinking_indicator = await self.page.query_selector(CLAUDE_SELECTORS['thinking_indicator'])
                    is_complete = thinking_indicator is None
                    
                    if not is_complete:
                        # Wait briefly before checking again
                        await self.page.wait_for_timeout(500)
                
                # Final yield with complete flag
                yield {
                    "status": "success",
                    "content": response_text,
                    "complete": True
                }
            
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
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
            # Click the upload button
            upload_button = await self.page.query_selector(CLAUDE_SELECTORS['upload_button'])
            if not upload_button:
                return False
                
            # Set up file input handling
            file_chooser = await Promise.create()
            self.page.once('filechooser', lambda chooser: file_chooser.resolve(chooser))
            
            # Click the upload button
            await upload_button.click()
            
            # Wait for file chooser and select file
            chooser = await file_chooser
            await chooser.set_files(image_path)
            
            # Wait for upload to complete
            await self.page.wait_for_selector(CLAUDE_SELECTORS['image_preview'], timeout=30000)
            
            return True
            
        except Exception as e:
            logger.error(f"Image upload error: {str(e)}")
            return False