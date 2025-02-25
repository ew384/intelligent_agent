# tool-service/src/tools/llm/claude/selectors.py

# Selectors for Claude.ai web interface
CLAUDE_SELECTORS = {
    # Login and authentication
    'login_button': 'button:has-text("Log in")',
    'logged_in_indicator': '[data-testid="new-chat"]',
    
    # Chat interface
    'new_chat_button': '[data-testid="new-chat"]',
    'prompt_textarea': '[data-testid="chat-input-box"]',
    'send_button': '[data-testid="send-message-button"]',
    'response_container': '[data-testid="conversation-turn-response"]',
    'thinking_indicator': '[data-testid="conversation-turn-loading"]',
    
    # File upload
    'upload_button': '[data-testid="image-upload-button"]',
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