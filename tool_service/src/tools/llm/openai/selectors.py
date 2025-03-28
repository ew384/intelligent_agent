# tool-service/src/tools/llm/openai/selectors.py
CHATGPT_SELECTORS = {
    # Login and authentication
    'login_button': 'button:has-text("Log in")',
    'logged_in_indicator': 'header button:first-child',

    # Chat interface
    'new_chat_button': 'header button:first-child',
    'prompt_textarea': '.ProseMirror',
    'send_button': '[aria-label*="send" i]',
    'response_container': '[data-message-author-role="assistant"]',
    'thinking_indicator': '[data-testid="conversation-turn-loading"]',

    # File upload
    'upload_button': '[aria-label*="upload" i]',
    'file_input': 'input[type="file"]',
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
