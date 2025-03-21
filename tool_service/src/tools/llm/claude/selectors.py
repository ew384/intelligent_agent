# tool-service/src/tools/llm/claude/selectors.py
# tool-service/src/tools/llm/claude/selectors.py

# Selectors for Claude.ai web interface
CLAUDE_SELECTORS = {
    # Login and authentication
    'login_button': 'button:contains("Log in")',
    'logged_in_indicator': 'div.ProseMirror',

    # Chat interface
    'new_chat_button': '.text-sm.hover\\:bg-bg-400.group.-mx-1\\.5.flex.items-center.gap-1.rounded-md.px-1\\.5.py-1\\.5.transition-colors.duration-75.text-text-100.\\!text-accent-main-000',
    'prompt_textarea': 'div.ProseMirror',  # Simplified selector
    'send_button': 'button[aria-label="Send Message"]',  # Using the aria-label instead of classes
    'response_container': 'div[data-message-author-role="assistant"], li.flex.flex-col.gap-3.pb-5',
    'thinking_indicator': 'div.animate-pulse, div[data-thinking="true"]',

    # File upload
    'upload_button': 'button[aria-label="Attach files"]',
    'image_preview': 'div[data-image-preview="true"]',

    # Chat management
    'chat_list': '.text-sm.hover\\:bg-bg-400.group.-mx-1\\.5',  # Escaping colons and periods
    'chat_item': 'a.text-sm',  # Simplified selector
    'delete_chat_button': 'button[aria-label="Delete chat"]',
    'confirm_delete_button': 'button:contains("Delete")',

    # Settings
    'settings_button': 'button[aria-label="Settings"]',
    'account_settings': 'div[aria-label="Account settings"]',
    'model_selector': 'button:contains("3.7 Sonnet")'  # Based on the visible model button
}
