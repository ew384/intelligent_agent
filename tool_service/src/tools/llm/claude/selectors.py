# tool-service/src/tools/llm/claude/selectors.py
CLAUDE_SELECTORS = {
    # Login and authentication
    'login_button': 'button:has-text("Log in")',
    'logged_in_indicator': 'a[href="/new"]',
    
    # Chat interface
    'new_chat_button': 'a[href="/new"]',
    'prompt_textarea': '.ProseMirror',
    'send_button': '[aria-label*="send" i]',
    'response_container': '[data-message-author-role="assistant"]',
    'thinking_indicator': '[data-testid="conversation-turn-loading"]',
    
    # File upload
    'upload_button': '[aria-label*="upload" i]',
    'file_input': 'input[type="file"]',  # Using the more specific input selector
    'image_preview': '[data-testid="image-preview"]',
    
    # Chat management
    'chat_list': '[data-testid="conversations-list-content"]',
    'chat_item': '[data-testid="conversation-item"]',
    'delete_chat_button': '[data-testid="delete-chat-button"]',
    'confirm_delete_button': '[data-testid="confirm-delete-button"]',
    
    # Settings
    'settings_button': '[data-testid="settings-button"]',
    'account_settings': '[data-testid="account-settings"]',
    'model_selector': '[data-testid="model-selector"]'
}
