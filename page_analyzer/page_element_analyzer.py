import json
import time
import os
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def get_element_info(driver, url=None):
    """
    Get page element information for creating automation functions
    
    Args:
        driver: Selenium WebDriver instance
        url: Optional URL to navigate to
        
    Returns:
        List of dictionaries containing element information
    """
    if url:
        driver.get(url)
        # Wait for user confirmation that the page is fully loaded
        input("Please confirm the page is fully loaded and logged in (if needed), then press Enter to continue...")
    
    js_script = """
    function getBestSelector(element) {
        // Try ID first
        if (element.id) {
            return {
                css: '#' + element.id,
                type: 'id'
            };
        }
        
        // Try using class
        if (element.className) {
            const classes = element.className.split(/\\s+/).filter(c => c);
            if (classes.length > 0) {
                return {
                    css: '.' + classes.join('.'),
                    type: 'class'
                };
            }
        }
        
        // Try using common attributes
        const commonAttributes = ['name', 'placeholder', 'title', 'aria-label', 'data-testid', 'role'];
        for (const attr of commonAttributes) {
            if (element.getAttribute(attr)) {
                const value = element.getAttribute(attr);
                return {
                    css: `[${attr}="${value}"]`,
                    type: 'attribute',
                    attribute: attr
                };
            }
        }
        
        // Use tag name and position
        let parent = element.parentElement;
        let tagName = element.tagName.toLowerCase();
        
        if (parent) {
            // Find sibling elements of the same type
            const siblings = Array.from(parent.children);
            const sameTagSiblings = siblings.filter(el => el.tagName === element.tagName);
            
            if (sameTagSiblings.length > 1) {
                // Multiple siblings with the same tag, use nth-child
                const index = Array.from(parent.children).indexOf(element) + 1;
                return {
                    css: `${parent.tagName.toLowerCase()} > ${tagName}:nth-child(${index})`,
                    type: 'position'
                };
            } else {
                // No siblings with the same tag, use direct child selector
                return {
                    css: `${parent.tagName.toLowerCase()} > ${tagName}`,
                    type: 'direct-child'
                };
            }
        }
        
        // Fallback
        return {
            css: tagName,
            type: 'tag'
        };
    }
    
    function isInteractive(element) {
        const tag = element.tagName.toLowerCase();
        
        // Standard interactive elements
        if (['a', 'button', 'input', 'select', 'textarea', 'label'].includes(tag)) {
            return true;
        }
        
        // Check for onclick attribute
        if (element.getAttribute('onclick') !== null) {
            return true;
        }
        
        // Elements with interactive roles
        const role = element.getAttribute('role');
        if (role && ['button', 'link', 'checkbox', 'menuitem', 'tab'].includes(role)) {
            return true;
        }
        
        // Elements that typically receive focus or have tabindex
        if (element.getAttribute('tabindex') !== null) {
            return true;
        }
        
        // Check for pointer cursor style
        const computedStyle = window.getComputedStyle(element);
        if (computedStyle.cursor === 'pointer') {
            return true;
        }
        
        return false;
    }
    
    function isVisible(element) {
        const styles = window.getComputedStyle(element);
        return styles.display !== 'none' && 
               styles.visibility !== 'hidden' && 
               parseFloat(styles.opacity) > 0 &&
               element.offsetWidth > 0 &&
               element.offsetHeight > 0;
    }
    
    // Get key attributes
    function getKeyAttributes(element) {
        const result = {};
        const keyAttrs = [
            'id', 'name', 'type', 'value', 'placeholder', 'href', 'src', 
            'role', 'aria-label', 'title', 'alt', 'for', 'action', 'method',
            'data-testid', 'data-id', 'data-name'
        ];
        
        for (const attr of keyAttrs) {
            const value = element.getAttribute(attr);
            if (value) {
                result[attr] = value;
            }
        }
        
        return result;
    }
    
    // Get position information
    function getPosition(element) {
        const rect = element.getBoundingClientRect();
        return {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            isInViewport: (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= window.innerHeight &&
                rect.right <= window.innerWidth
            )
        };
    }
    
    // Get key style information
    function getKeyStyles(element) {
        const styles = window.getComputedStyle(element);
        return {
            display: styles.display,
            visibility: styles.visibility,
            position: styles.position,
            cursor: styles.cursor,
            opacity: styles.opacity
        };
    }
    
    // Get direct text content (excluding child elements' text)
    function getDirectTextContent(element) {
        let text = '';
        for (let i = 0; i < element.childNodes.length; i++) {
            const node = element.childNodes[i];
            if (node.nodeType === 3) { // TEXT_NODE
                text += node.textContent;
            }
        }
        return text.trim();
    }
    
    let results = [];
    const elements = document.querySelectorAll('*');
    
    for (let i = 0; i < elements.length; i++) {
        const el = elements[i];
        
        // Only include visible elements
        if (isVisible(el)) {
            const interactive = isInteractive(el);
            const text = el.textContent ? el.textContent.trim() : '';
            const directText = getDirectTextContent(el);
            
            // Include elements with text or that are interactive
            if (text || interactive) {
                const selector = getBestSelector(el);
                
                results.push({
                    tag: el.tagName.toLowerCase(),
                    text: text.substring(0, 100),
                    directText: directText.substring(0, 100),
                    selector: selector.css,
                    selectorType: selector.type,
                    attributes: getKeyAttributes(el),
                    position: getPosition(el),
                    keyStyles: getKeyStyles(el),
                    isInteractive: interactive,
                    isFormElement: ['input', 'select', 'textarea', 'button', 'form'].includes(el.tagName.toLowerCase()),
                    hasChildren: el.children.length > 0,
                    childCount: el.children.length
                });
            }
        }
    }
    
    // Sort results by interactivity (interactive elements first)
    results.sort((a, b) => {
        if (a.isInteractive && !b.isInteractive) return -1;
        if (!a.isInteractive && b.isInteractive) return 1;
        return 0;
    });
    
    return results;
    """
    
    try:
        element_info = driver.execute_script(js_script)
        return element_info
    except Exception as e:
        print(f"JavaScript execution error: {e}")
        return []

def save_elements_to_file(elements, filename="page_elements.json"):
    """Save element information to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(elements)} elements to {filename}")

def generate_element_constants(elements, filename="page_selectors.py"):
    """Generate page element constant selectors file"""
    # Track used constant names
    used_names = set()
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated page element selectors\n")
        f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Generate interactive element constants
        f.write("# Interactive elements\n")
        for i, el in enumerate([e for e in elements if e['isInteractive']]):
            # Create constant name
            name_base = ""
            
            # Try to get name from attributes
            for attr in ['id', 'name', 'aria-label', 'title', 'placeholder']:
                if attr in el['attributes']:
                    name_base = el['attributes'][attr]
                    break
            
            # If no suitable attribute found, use direct text
            if not name_base and el['directText']:
                name_base = el['directText']
            
            # If still no name, use tag and index
            if not name_base:
                name_base = f"{el['tag']}_{i}"
            
            # Clean name to make a valid Python constant
            const_name = ''.join(c if c.isalnum() else '_' for c in name_base)
            const_name = const_name.strip('_').upper()
            if const_name and const_name[0].isdigit():
                const_name = f"EL_{const_name}"
            
            # Prevent empty names
            if not const_name:
                const_name = f"{el['tag'].upper()}_{i}"
            
            # Limit length
            if len(const_name) > 40:
                const_name = const_name[:40]
            
            # Ensure name is unique
            counter = 1
            original_name = const_name
            while const_name in used_names:
                const_name = f"{original_name}_{counter}"
                counter += 1
            
            # Add to used names set
            used_names.add(const_name)
            
            # Write constant
            css_selector = el['selector'].replace("'", "\\'")
            f.write(f"{const_name} = '{css_selector}'  #")
            #f.write(f"{const_name} = '{css_selector}'  # {el['tag']}: {el['text'][:30]}\n")
        
        f.write("\n# Form elements\n")
        form_elements = [e for e in elements if e['isFormElement'] and not e['isInteractive']]
        for i, el in enumerate(form_elements):
            # Similar logic for form elements
            name_base = ""
            for attr in ['id', 'name', 'placeholder']:
                if attr in el['attributes']:
                    name_base = el['attributes'][attr]
                    break
            
            if not name_base:
                name_base = f"form_{el['tag']}_{i}"
            
            const_name = ''.join(c if c.isalnum() else '_' for c in name_base)
            const_name = const_name.strip('_').upper()
            if const_name and const_name[0].isdigit():
                const_name = f"FORM_{const_name}"
            
            # Prevent empty names
            if not const_name:
                const_name = f"FORM_{el['tag'].upper()}_{i}"
            
            if len(const_name) > 40:
                const_name = const_name[:40]
            
            # Ensure name is unique
            counter = 1
            original_name = const_name
            while const_name in used_names:
                const_name = f"{original_name}_{counter}"
                counter += 1
            
            # Add to used names set
            used_names.add(const_name)
            
            css_selector = el['selector'].replace("'", "\\'")
            f.write(f"{const_name} = '{css_selector}'  # {el['tag']}: {el.get('attributes', {}).get('placeholder', '')}\n")
    
    print(f"Generated page element constants to {filename}")

def print_element_summary(elements):
    """Print element summary information"""
    print(f"\n{'='*80}\nFound {len(elements)} interactive/visible elements\n{'='*80}")
    
    interactive_count = len([e for e in elements if e['isInteractive']])
    form_count = len([e for e in elements if e['isFormElement']])
    
    print(f"Interactive elements: {interactive_count}")
    print(f"Form elements: {form_count}")
    print(f"Other elements: {len(elements) - interactive_count - form_count}")
    
    print("\nMain interactive elements:")
    for i, el in enumerate([e for e in elements if e['isInteractive']][:10]):  # Only show first 10
        selector = el['selector']
        text = el['text'][:50] + ('...' if len(el['text']) > 50 else '')
        print(f"  {i+1}. [{el['tag']}] {text}")
        print(f"     Selector: {selector}")
        
        # Show key attributes
        attrs = []
        for key in ['id', 'name', 'aria-label', 'role', 'type']:
            if key in el.get('attributes', {}):
                attrs.append(f"{key}='{el['attributes'][key]}'")
        if attrs:
            print(f"     Attributes: {', '.join(attrs)}")
        print()

def create_output_dir():
    """Create output directory"""
    output_dir = "page_automation_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def copy_template_files(output_dir):
    """Copy template files to output directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create template files
    template_files = {
        "page_session.py": '''import asyncio
import logging
from typing import Optional, Any, Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PageSession')

class PageSession:
    """
    Class that handles browser session and basic page interactions
    """
    
    def __init__(self, driver, timeout=10):
        """
        Initialize page session
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Default wait timeout in seconds
        """
        self.driver = driver
        self.timeout = timeout
    
    async def navigate_to(self, url: str) -> bool:
        """
        Navigate to specified URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            # Add a small delay to let the page start loading
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Optional[Any]:
        """
        Wait for element matching selector to be present
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in seconds (uses default if None)
            
        Returns:
            WebElement if found, None otherwise
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for selector: {selector}")
            return None
        except Exception as e:
            logger.error(f"Error waiting for selector {selector}: {str(e)}")
            return None
    
    async def wait_for_clickable(self, selector: str, timeout: Optional[int] = None) -> Optional[Any]:
        """
        Wait for element matching selector to be clickable
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in seconds (uses default if None)
            
        Returns:
            WebElement if found and clickable, None otherwise
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for clickable element: {selector}")
            return None
        except Exception as e:
            logger.error(f"Error waiting for clickable element {selector}: {str(e)}")
            return None
    
    async def click(self, selector: str, wait_time: float = 0.5) -> bool:
        """
        Click element matching selector
        
        Args:
            selector: CSS selector
            wait_time: Time to wait after clicking in seconds
            
        Returns:
            Success status
        """
        try:
            element = await self.wait_for_clickable(selector)
            if not element:
                return False
                
            element.click()
            await asyncio.sleep(wait_time)
            return True
        except ElementNotInteractableException:
            # Try JavaScript click as fallback
            logger.info(f"Element not interactable, trying JavaScript click: {selector}")
            try:
                self.driver.execute_script("arguments[0].click();", 
                    self.driver.find_element(By.CSS_SELECTOR, selector))
                await asyncio.sleep(wait_time)
                return True
            except Exception as e:
                logger.error(f"JavaScript click failed: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Click failed on {selector}: {str(e)}")
            return False
    
    async def fill(self, selector: str, text: str) -> bool:
        """
        Fill form field with text
        
        Args:
            selector: CSS selector for input field
            text: Text to enter
            
        Returns:
            Success status
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return False
                
            # Clear field first
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            logger.error(f"Fill failed on {selector}: {str(e)}")
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """
        Get text content from element
        
        Args:
            selector: CSS selector
            
        Returns:
            Text content or None if element not found
        """
        try:
            element = await self.wait_for_selector(selector)
            if not element:
                return None
                
            return element.text
        except Exception as e:
            logger.error(f"Get text failed on {selector}: {str(e)}")
            return None
    
    async def query_selector(self, selector: str) -> Optional[Any]:
        """
        Find element matching selector without waiting
        
        Args:
            selector: CSS selector
            
        Returns:
            WebElement if found, None otherwise
        """
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            return None
        except Exception as e:
            logger.error(f"Query selector failed for {selector}: {str(e)}")
            return None
    
    async def query_selector_all(self, selector: str) -> List[Any]:
        """
        Find all elements matching selector
        
        Args:
            selector: CSS selector
            
        Returns:
            List of WebElements (empty if none found)
        """
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            logger.error(f"Query selector all failed for {selector}: {str(e)}")
            return []
    
    async def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in browser
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to script
            
        Returns:
            Script execution result
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Script execution failed: {str(e)}")
            return None
    
    async def refresh_page(self) -> bool:
        """
        Refresh current page
        
        Returns:
            Success status
        """
        try:
            self.driver.refresh()
            await asyncio.sleep(2)  # Wait for page to reload
            return True
        except Exception as e:
            logger.error(f"Page refresh failed: {str(e)}")
            return False
''',
        "test.py": '''import asyncio
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Import custom modules
from page_session import PageSession
from page_automation import PageAutomation

# Optional: Import specific selectors if direct access needed
# from page_selectors import *

async def run_automation():
    """
    Run automation example
    """
    print("Initializing Chrome driver...")
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print("Chrome driver initialized")
    except Exception as e:
        print(f"Failed to initialize Chrome driver: {str(e)}")
        return
    
    try:
        # Initialize session and automation classes
        print("Initializing PageSession and PageAutomation...")
        session = PageSession(driver)
        page = PageAutomation(session)
        
        # Get URL to visit
        url = input("Enter URL to automate: ")
        if not url:
            print("No URL provided, using current URL")
        else:
            # Navigate to page
            print(f"Navigating to {url}...")
            await session.navigate_to(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        await page.wait_for_page_load()
        
        # Get page title
        title = await page.get_page_title()
        print(f"Page title: {title}")
        
        # Demo of how to use automation class methods
        # Since each page generates different methods, this is a generic example
        # You need to check the generated page_automation.py file to see available methods
        
        print("\\nAvailable automation methods:")
        
        # Get all click_ and fill_ methods from PageAutomation
        automation_methods = [method for method in dir(page) 
                             if callable(getattr(page, method)) and 
                             (method.startswith('click_') or method.startswith('fill_'))]
        
        for method in automation_methods:
            print(f"  - {method}")
        
        # Let user choose method to execute
        while True:
            print("\\nSelect operation:")
            print("1. Execute click method")
            print("2. Execute fill method")
            print("3. Exit")
            
            choice = input("Enter choice (1/2/3): ")
            
            if choice == '1':
                # Show all click methods
                click_methods = [m for m in automation_methods if m.startswith('click_')]
                if not click_methods:
                    print("No click methods available")
                    continue
                
                print("Available click methods:")
                for i, method in enumerate(click_methods):
                    print(f"{i+1}. {method}")
                
                method_index = input("Select method number to execute: ")
                try:
                    method_index = int(method_index) - 1
                    if 0 <= method_index < len(click_methods):
                        method_name = click_methods[method_index]
                        print(f"Executing {method_name}...")
                        result = await getattr(page, method_name)()
                        print(f"Result: {result}")
                    else:
                        print("Invalid selection")
                except ValueError:
                    print("Please enter a valid number")
            
            elif choice == '2':
                # Show all fill methods
                fill_methods = [m for m in automation_methods if m.startswith('fill_')]
                if not fill_methods:
                    print("No fill methods available")
                    continue
                
                print("Available fill methods:")
                for i, method in enumerate(fill_methods):
                    print(f"{i+1}. {method}")
                
                method_index = input("Select method number to execute: ")
                try:
                    method_index = int(method_index) - 1
                    if 0 <= method_index < len(fill_methods):
                        method_name = fill_methods[method_index]
                        text = input("Enter text to fill: ")
                        print(f"Executing {method_name}...")
                        result = await getattr(page, method_name)(text)
                        print(f"Result: {result}")
                    else:
                        print("Invalid selection")
                except ValueError:
                    print("Please enter a valid number")
            
            elif choice == '3':
                print("Exiting program")
                break
            
            else:
                print("Invalid choice, please try again")
        
    except Exception as e:
        print(f"Error during automation: {str(e)}")
    finally:
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    # Run automation
    asyncio.run(run_automation())
'''
    }
    
    # Write template files to output directory
    for filename, content in template_files.items():
        with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"Template files copied to {output_dir}")

def generate_page_automation_class(elements, filename="page_automation.py"):
    """Generate page automation class"""
    # Collect interactive elements
    interactive_elements = [e for e in elements if e['isInteractive']]
    form_elements = [e for e in elements if e['isFormElement']]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated page automation class\n")
        f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("import logging\nimport asyncio\nimport time\n")
        f.write("from typing import Dict, Any, Optional, List, Union\n")
        f.write("from selenium.common.exceptions import TimeoutException, NoSuchElementException\n\n")
        
        f.write("# Import page element constants\n")
        f.write("from page_selectors import *\n\n")
        
        f.write("logger = logging.getLogger(__name__)\n\n")
        
        # Generate PageAutomation class
        f.write("class PageAutomation:\n")
        f.write("    \"\"\"Auto-generated page automation class\"\"\"\n\n")
        
        f.write("    def __init__(self, session):\n")
        f.write("        \"\"\"Initialize page automation\n\n")
        f.write("        Args:\n")
        f.write("            session: Browser session object that implements wait_for_selector, click, fill, etc.\n")
        f.write("        \"\"\"\n")
        f.write("        self.session = session\n")
        f.write("        self.page_loaded = False\n\n")
        
        # Generate page load check method
        f.write("    async def wait_for_page_load(self, timeout: int = 10) -> bool:\n")
        f.write("        \"\"\"Wait for page to load\n\n")
        f.write("        Args:\n")
        f.write("            timeout: Timeout in seconds\n\n")
        f.write("        Returns:\n")
        f.write("            Whether page loaded successfully\n")
        f.write("        \"\"\"\n")
        f.write("        try:\n")
        f.write("            # Try to find key elements to determine if page has loaded\n")
        
        # Select a few key elements as page load indicators
        key_elements = []
        for el in interactive_elements[:3]:  # Use first 3 interactive elements
            if el['selector']:
                key_elements.append(el['selector'])
        
        if key_elements:
            for i, selector in enumerate(key_elements):
                selector = selector.replace("'", "\\'")
                f.write(f"            element{i} = await self.session.wait_for_selector('{selector}', timeout)\n")
                f.write(f"            if element{i}:\n")
                f.write(f"                logger.info(\"Page loaded, key element detected\")\n")
                f.write(f"                self.page_loaded = True\n")
                f.write(f"                return True\n")
        
        f.write("            logger.warning(\"No key elements detected, page may not be fully loaded\")\n")
        f.write("            return False\n")
        f.write("        except TimeoutException:\n")
        f.write("            logger.error(\"Timeout waiting for page to load\")\n")
        f.write("            return False\n")
        f.write("        except Exception as e:\n")
        f.write("            logger.error(f\"Error waiting for page to load: {str(e)}\")\n")
        f.write("            return False\n\n")
        
        # Generate click methods
        for i, el in enumerate(interactive_elements):
            if el['tag'] in ['a', 'button'] or el.get('attributes', {}).get('role') == 'button' or el.get('keyStyles', {}).get('cursor') == 'pointer':
                # Create method name
                method_name_base = ""
                
                # Try to get name from attributes
                for attr in ['id', 'name', 'aria-label', 'title']:
                    if attr in el['attributes']:
                        method_name_base = el['attributes'][attr]
                        break
                
                # If no suitable attribute found, use direct text
                if not method_name_base and el['directText']:
                    method_name_base = el['directText']
                
                # If still no name, use tag and index
                if not method_name_base:
                    method_name_base = f"{el['tag']}_{i}"
                
                # Clean name to make a valid Python method name
                method_name = ''.join(c if c.isalnum() else '_' for c in method_name_base.lower())
                method_name = method_name.strip('_')
                
                # Prevent empty names
                if not method_name:
                    method_name = f"click_element_{i}"
                else:
                    method_name = f"click_{method_name}"
                
                # Limit length
                if len(method_name) > 40:
                    method_name = method_name[:40]
                
                # Selector
                selector = el['selector'].replace("'", "\\'")
                
                # Generate method
                f.write(f"    async def {method_name}(self) -> Dict[str, Any]:\n")
                f.write(f"        \"\"\"Click element: {el['text'][:50]}\n\n")
                f.write(f"        Selector: {el['selector']}\n")
                f.write(f"        Element type: {el['tag']}\n\n")
                f.write(f"        Returns:\n")
                f.write(f"            Operation result\n")
                f.write(f"        \"\"\"\n")
                f.write(f"        try:\n")
                f.write(f"            success = await self.session.click('{selector}')\n")
                f.write(f"            \n")
                f.write(f"            if not success:\n")
                f.write(f"                return {{\n")
                f.write(f"                    \"status\": \"error\",\n")
                f.write(f"                    \"message\": \"Element not found or not clickable\"\n")
                f.write(f"                }}\n")
                f.write(f"            \n")
                f.write(f"            # Wait for possible page changes\n")
                f.write(f"            await asyncio.sleep(0.5)\n")
                f.write(f"            \n")
                f.write(f"            return {{\n")
                f.write(f"                \"status\": \"success\",\n")
                f.write(f"                \"message\": \"Element clicked successfully\"\n")
                f.write(f"            }}\n")
                f.write(f"        except Exception as e:\n")
                f.write(f"            logger.error(f\"Click operation failed: {{str(e)}}\")\n")
                f.write(f"            return {{\n")
                f.write(f"                \"status\": \"error\",\n")
                f.write(f"                \"message\": f\"Click operation failed: {{str(e)}}\"\n")
                f.write(f"            }}\n\n")
        
        # Generate form fill methods
        for i, el in enumerate(form_elements):
            if el['tag'] in ['input', 'textarea']:
                # Create method name
                method_name_base = ""
                
                # Try to get name from attributes
                for attr in ['id', 'name', 'placeholder']:
                    if attr in el['attributes']:
                        method_name_base = el['attributes'][attr]
                        break
                
                # If no name, use tag and index
                if not method_name_base:
                    method_name_base = f"{el['tag']}_{i}"
                
                # Clean name
                method_name = ''.join(c if c.isalnum() else '_' for c in method_name_base.lower())
                method_name = method_name.strip('_')
                
                # Prevent empty names
                if not method_name:
                    method_name = f"fill_field_{i}"
                else:
                    method_name = f"fill_{method_name}"
                
                # Limit length
                if len(method_name) > 40:
                    method_name = method_name[:40]
                
                # Selector
                selector = el['selector'].replace("'", "\\'")
                
                # Description
                description = el.get('attributes', {}).get('placeholder', '') or el.get('attributes', {}).get('name', '') or el.get('attributes', {}).get('id', '')
                
                # Generate method
                f.write(f"    async def {method_name}(self, text: str) -> Dict[str, Any]:\n")
                f.write(f"        \"\"\"Fill form field: {description}\n\n")
                f.write(f"        Selector: {el['selector']}\n")
                f.write(f"        Element type: {el['tag']}\n\n")
                f.write(f"        Args:\n")
                f.write(f"            text: Text to input\n\n")
                f.write(f"        Returns:\n")
                f.write(f"            Operation result\n")
                f.write(f"        \"\"\"\n")
                f.write(f"        try:\n")
                f.write(f"            logger.info(f\"Filling field {description}: {{text}}\")\n")
                f.write(f"            success = await self.session.fill('{selector}', text)\n")
                f.write(f"            \n")
                f.write(f"            if not success:\n")
                f.write(f"                return {{\n")
                f.write(f"                    \"status\": \"error\",\n")
                f.write(f"                    \"message\": \"Field not found or not fillable\"\n")
                f.write(f"                }}\n")
                f.write(f"            \n")
                f.write(f"            return {{\n")
                f.write(f"                \"status\": \"success\",\n")
                f.write(f"                \"message\": \"Field filled successfully\"\n")
                f.write(f"            }}\n")
                f.write(f"        except Exception as e:\n")
                f.write(f"            logger.error(f\"Fill operation failed: {{str(e)}}\")\n")
                f.write(f"            return {{\n")
                f.write(f"                \"status\": \"error\",\n")
                f.write(f"                \"message\": f\"Fill operation failed: {{str(e)}}\"\n")
                f.write(f"            }}\n\n")
        
        # Generate utility methods
        f.write("    async def get_page_title(self) -> Optional[str]:\n")
        f.write("        \"\"\"Get page title\n\n")
        f.write("        Returns:\n")
        f.write("            Page title or None\n")
        f.write("        \"\"\"\n")
        f.write("        try:\n")
        f.write("            return await self.session.execute_script(\"return document.title;\")\n")
        f.write("        except Exception as e:\n")
        f.write("            logger.error(f\"Failed to get page title: {str(e)}\")\n")
        f.write("            return None\n\n")
        
        f.write("    async def get_element_text(self, selector: str) -> Optional[str]:\n")
        f.write("        \"\"\"Get element text\n\n")
        f.write("        Args:\n")
        f.write("            selector: CSS selector\n\n")
        f.write("        Returns:\n")
        f.write("            Element text or None\n")
        f.write("        \"\"\"\n")
        f.write("        try:\n")
        f.write("            element = await self.session.wait_for_selector(selector)\n")
        f.write("            if not element:\n")
        f.write("                return None\n")
        f.write("            return await self.session.get_text(selector)\n")
        f.write("        except Exception as e:\n")
        f.write("            logger.error(f\"Failed to get element text: {str(e)}\")\n")
        f.write("            return None\n")
    
    print(f"Generated page automation class to {filename}")

def main():
    url = input("Enter URL to analyze (or press Enter to analyze current page): ")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    # Initialize Chrome driver
    driver = webdriver.Chrome(service=Service('/usr/local/bin/chromedriver'), options=chrome_options)
    
    try:
        if url:
            driver.get(url)
            print(f"Analyzing: {url}")
        else:
            print("Analyzing current page")
        
        # Wait for user to confirm page is fully loaded
        input("Please confirm the page is fully loaded and logged in (if needed), then press Enter to continue...")
        
        # Create output directory
        output_dir = create_output_dir()
        
        # Get element information
        print("Collecting page element information...")
        elements = get_element_info(driver)
        
        # Print summary
        print_element_summary(elements)
        
        # Save to files
        json_file = os.path.join(output_dir, "page_elements.json")
        save_elements_to_file(elements, json_file)
        
        # Generate constants and automation class
        selectors_file = os.path.join(output_dir, "page_selectors.py")
        automation_file = os.path.join(output_dir, "page_automation.py")
        
        print("\nGenerating page element constants and automation class...")
        generate_element_constants(elements, selectors_file)
        generate_page_automation_class(elements, automation_file)
        
        # Copy template files for PageSession and test.py
        print("\nGenerating PageSession class and test script...")
        copy_template_files(output_dir)
        
        print(f"\nAnalysis complete! All files saved to {output_dir} directory")
        print(f"- Element data: {json_file}")
        print(f"- Selector constants: {selectors_file}")
        print(f"- Automation class: {automation_file}")
        print(f"- Page session class: {os.path.join(output_dir, 'page_session.py')}")
        print(f"- Test script: {os.path.join(output_dir, 'test.py')}")
        print(f"\nYou can test the generated automation code by running:")
        print(f"cd {output_dir}")
        print(f"python test.py")
        
    finally:
        # Close browser
        driver.quit()

if __name__ == "__main__":
    main()
