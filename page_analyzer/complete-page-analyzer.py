import json
import time
import os
import shutil
import re
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
        const commonAttributes = ['name', 'placeholder', 'title', 'aria-label', 'data-testid', 'role', 'data-id', 'data-name'];
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
    
    // Get key attributes (only include essential attributes)
    function getKeyAttributes(element) {
        const result = {};
        const keyAttrs = [
            'id', 'name', 'type', 'value', 'placeholder', 'href', 
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
    
    // Get key style information - only essential ones
    function getKeyStyles(element) {
        const styles = window.getComputedStyle(element);
        return {
            display: styles.display,
            visibility: styles.visibility,
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
    
    // Get element path for hierarchy understanding
    function getElementPath(element, maxDepth = 5) {
        let path = [];
        let current = element;
        let depth = 0;
        
        while (current && current.tagName && depth < maxDepth) {
            let identifier = current.tagName.toLowerCase();
            
            if (current.id) {
                identifier += '#' + current.id;
            } else if (current.className) {
                const classes = current.className.split(/\\s+/).filter(c => c);
                if (classes.length > 0) {
                    identifier += '.' + classes.join('.');
                }
            }
            
            path.unshift(identifier);
            current = current.parentElement;
            depth++;
        }
        
        return path.join(' > ');
    }
    
    // Get parent elements information to understand the context
    function getParentInfo(element, levels = 2) {
        let result = [];
        let current = element.parentElement;
        let level = 0;
        
        while (current && level < levels) {
            const parent = {
                tag: current.tagName.toLowerCase(),
                id: current.id || null,
                classes: current.className ? current.className.split(/\\s+/).filter(c => c).join(' ') : null,
                text: current.textContent ? current.textContent.trim().substring(0, 50) : ''
            };
            
            result.push(parent);
            current = current.parentElement;
            level++;
        }
        
        return result;
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
            if (text || interactive || el.tagName.toLowerCase() === 'img') {
                const selector = getBestSelector(el);
                
                const elementInfo = {
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
                    childCount: el.children.length,
                    elementPath: getElementPath(el),
                    parentInfo: getParentInfo(el)
                };
                
                // Only include src for images if it's not a data URL (to save space)
                if (el.tagName.toLowerCase() === 'img' && el.src) {
                    if (!el.src.startsWith('data:')) {
                        elementInfo.attributes.src = el.src;
                    } else {
                        // For data URLs, just note their existence but don't include the full content
                        elementInfo.attributes.src = 'data:image/...';
                    }
                }
                
                results.push(elementInfo);
            }
        }
    }
    
    // Sort results by interactivity and position
    results.sort((a, b) => {
        // Interactive elements first
        if (a.isInteractive && !b.isInteractive) return -1;
        if (!a.isInteractive && b.isInteractive) return 1;
        
        // Then by vertical position (top to bottom)
        return a.position.y - b.position.y;
    });
    
    return results;
    """
    
    try:
        element_info = driver.execute_script(js_script)
        return element_info
    except Exception as e:
        print(f"JavaScript execution error: {e}")
        return []

def filter_essential_elements(elements):
    """Filter and keep only essential information for each element"""
    essential_elements = []
    
    for el in elements:
        # Always include interactive and form elements
        if el.get('isInteractive') or el.get('isFormElement'):
            essential_el = {
                'tag': el['tag'],
                'text': el['text'].strip() if el.get('text') else '',
                'directText': el['directText'].strip() if el.get('directText') else '',
                'selector': el['selector'],
                'selectorType': el['selectorType'],
                'isInteractive': el['isInteractive'],
                'isFormElement': el.get('isFormElement', False)
            }
            
            # Include only essential attributes
            if 'attributes' in el:
                essential_el['attributes'] = {k: v for k, v in el['attributes'].items() 
                                            if k in ['id', 'name', 'type', 'placeholder', 'title', 'data-id', 'data-name']}
            
            # Include cursor style as it's important for interactivity
            if 'keyStyles' in el and 'cursor' in el['keyStyles']:
                essential_el['cursor'] = el['keyStyles']['cursor']
                
            essential_elements.append(essential_el)
        
        # Also include elements with significant text that might be important for page understanding
        elif el.get('text') and len(el.get('text', '').strip()) > 5:
            essential_el = {
                'tag': el['tag'],
                'text': el['text'].strip() if el.get('text') else '',
                'directText': el['directText'].strip() if el.get('directText') else '',
                'selector': el['selector'],
                'selectorType': el['selectorType'],
                'isInteractive': False,
                'isFormElement': False
            }
            essential_elements.append(essential_el)
    
    return essential_elements

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
        for i, el in enumerate([e for e in elements if e.get('isInteractive')]):
            # Create constant name
            name_base = ""
            
            # Try to get name from attributes
            for attr in ['id', 'name', 'aria-label', 'title', 'placeholder', 'data-id', 'data-name']:
                if 'attributes' in el and attr in el['attributes']:
                    name_base = el['attributes'][attr]
                    break
            
            # If no suitable attribute found, use direct text
            if not name_base and el.get('directText'):
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
            pattern = r'\s+'  # 定义在 f-string 外部
            f.write(f"{const_name} = '{css_selector}'  # {el['tag']}: {re.sub(pattern, ' ', el.get('text', ''))[:30].strip()}\n")
            #f.write(f"{const_name} = '{css_selector}'  # {el['tag']}: {el.get('text', '')[:30]}\n")
            
        f.write("\n# Form elements\n")
        form_elements = [e for e in elements if e.get('isFormElement') and not e.get('isInteractive')]
        for i, el in enumerate(form_elements):
            # Similar logic for form elements
            name_base = ""
            for attr in ['id', 'name', 'placeholder']:
                if 'attributes' in el and attr in el['attributes']:
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
            placeholder = el.get('attributes', {}).get('placeholder', '')
            f.write(f"{const_name} = '{css_selector}'  # {el['tag']}: {placeholder}\n")
    
    print(f"Generated page element constants to {filename}")

def generate_page_structure(elements, title="Unknown Page", url="", filename="page_structure.md"):
    """Generate a markdown document describing the page structure for easier understanding"""
    
    # Extract visible text and group elements by their role
    text_elements = [e for e in elements if e.get('text') and len(e.get('text', '').strip()) > 0]
    interactive_elements = [e for e in elements if e.get('isInteractive')]
    form_elements = [e for e in elements if e.get('isFormElement')]
    
    # Sort elements by vertical position to maintain document flow
    text_elements.sort(key=lambda e: e.get('position', {}).get('y', 0))
    interactive_elements.sort(key=lambda e: e.get('position', {}).get('y', 0))
    form_elements.sort(key=lambda e: e.get('position', {}).get('y', 0))
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Page Structure Analysis: {title}\n\n")
        
        if url:
            f.write(f"URL: {url}\n\n")
        
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Page overview section
        f.write("## Page Overview\n\n")
        f.write("This document provides a structural analysis of the web page, describing its elements, ")
        f.write("functionality, and content to help with understanding and automation.\n\n")
        
        # Extract main headings
        headers = [e for e in text_elements if e['tag'] in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']]
        if headers:
            f.write("### Main Headings\n\n")
            for header in headers:
                pattern = r'\s+'  # 定义在 f-string 外部
                f.write(f"- {re.sub(pattern, ' ', header.get('text', ''))[:30].strip()}\n")
            f.write("\n")
        
        # Interactive elements section
        f.write("## Interactive Elements\n\n")
        f.write("These elements can be clicked, typed into, or otherwise interacted with:\n\n")
        
        # Buttons
        buttons = [e for e in interactive_elements 
                  if e['tag'] == 'button' 
                  or ('attributes' in e and e['attributes'].get('role') == 'button')
                  or ('keyStyles' in e and e['keyStyles'].get('cursor') == 'pointer')]
        
        if buttons:
            f.write("### Buttons\n\n")
            for button in buttons:
                text = button.get('text', '').strip() or button.get('directText', '').strip() or "Unlabeled button"
                id_attr = button.get('attributes', {}).get('id', '')
                id_info = f" (id: {id_attr})" if id_attr else ""
                pattern = r'\s+'
                clean_text = re.sub(pattern, ' ', text).strip()
                clean_id_info = re.sub(pattern, ' ', id_info).strip()
                f.write(f"- {clean_text}{clean_id_info}\n")
            f.write("\n")
        
        # Links
        links = [e for e in interactive_elements if e['tag'] == 'a']
        if links:
            f.write("### Links\n\n")
            for link in links:
                text = link.get('text', '').strip() or link.get('directText', '').strip() or "Unlabeled link"
                href = link.get('attributes', {}).get('href', '')
                href_info = f" -> {href}" if href else ""
                pattern = r'\s+'
                clean_text = re.sub(pattern, ' ', text).strip()
                clean_href_info = re.sub(pattern, ' ', href_info).strip()
                f.write(f"- {clean_text}{clean_href_info}\n")
            f.write("\n")
        
        # Form elements
        if form_elements:
            f.write("### Form Elements\n\n")
            
            # Inputs
            inputs = [e for e in form_elements if e['tag'] == 'input']
            if inputs:
                f.write("#### Input Fields\n\n")
                for input_el in inputs:
                    input_type = input_el.get('attributes', {}).get('type', 'text')
                    placeholder = input_el.get('attributes', {}).get('placeholder', '')
                    label = placeholder or input_el.get('attributes', {}).get('name', '') or "Unlabeled field"
                    id_attr = input_el.get('attributes', {}).get('id', '')
                    f.write(f"- {label} (type: {input_type}, id: {id_attr})\n")
                f.write("\n")
            
            # Selects/dropdowns
            selects = [e for e in form_elements if e['tag'] == 'select']
            if selects:
                f.write("#### Dropdown Menus\n\n")
                for select in selects:
                    label = select.get('attributes', {}).get('name', '') or "Unlabeled dropdown"
                    id_attr = select.get('attributes', {}).get('id', '')
                    f.write(f"- {label} (id: {id_attr})\n")
                f.write("\n")
        
        # Main content text 
        f.write("## Page Content Text\n\n")
        f.write("Key text content from the page:\n\n")
        
        # Group text by sections to provide better context
        main_text_elements = [e for e in text_elements 
                             if len(e.get('text', '').strip()) > 10 
                             and not e.get('isInteractive')
                             and e['tag'] not in ['script', 'style']]
        
        if main_text_elements:
            for i, elem in enumerate(main_text_elements):
                if i > 30:  # Limit to avoid too long document
                    f.write("\n*... additional content truncated ...*\n")
                    break
                    
                text = elem.get('text', '').strip()
                tag = elem['tag']
                
                # Format differently based on tag
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    heading_level = int(tag[1])
                    prefix = '#' * heading_level
                    pattern = r'\s+'
                    clean_text = re.sub(pattern, ' ', text).strip()
                    f.write(f"\n{prefix} {clean_text}\n\n")
                elif tag in ['p', 'div'] and len(text) > 0:
                    pattern = r'\s+'
                    f.write(f"- {re.sub(pattern, ' ', text).strip()}\n\n")
                    #f.write(f"{text}\n\n")
                else:
                    pattern = r'\s+'
                    clean_text = re.sub(pattern, ' ', text).strip()
                    f.write(f"- {clean_text}\n")
        else:
            f.write("*No significant text content detected*\n\n")
        
        # Page layout section
        f.write("## Page Structure\n\n")
        f.write("Key structural elements of the page:\n\n")
        
        # Find main containers
        main_containers = get_main_containers(elements)
        for container in main_containers:
            container_type = container.get('tag', 'div')
            container_class = container.get('attributes', {}).get('class', '')
            container_id = container.get('attributes', {}).get('id', '')
            
            identifier = container_id or container_class or f"{container_type} at position {container.get('position', {}).get('y', 0)}"
            
            f.write(f"### {identifier}\n\n")
            
            # List child elements by type
            container_children = get_container_children(elements, container)
            if container_children:
                interactive_children = [c for c in container_children if c.get('isInteractive')]
                if interactive_children:
                    f.write("Interactive elements:\n\n")
                    for child in interactive_children[:10]:  # Limit to 10 elements per section
                        text = child.get('text', '').strip() or child.get('directText', '').strip() or f"{child['tag']} element"
                        pattern = r'\s+'
                        f.write(f"- {re.sub(pattern, ' ', text).strip()}\n")
                    if len(interactive_children) > 10:
                        f.write(f"- *...and {len(interactive_children) - 10} more interactive elements*\n")
                    f.write("\n")
            else:
                f.write("*No significant elements detected in this container*\n\n")
    
    print(f"Generated page structure analysis at {filename}")

def get_main_containers(elements):
    """Find the main container elements on the page"""
    # Look for elements that likely serve as main containers
    potential_containers = []
    
    for el in elements:
        # Check for main content divs and sections
        if el['tag'] in ['div', 'section', 'main', 'article']:
            if el.get('childCount', 0) > 5:  # Container with many children
                if 'attributes' in el:
                    attributes = el['attributes']
                    # Look for ID/class patterns that suggest main containers
                    for attr in ['id', 'class']:
                        if attr in attributes:
                            value = attributes[attr].lower()
                            if any(keyword in value for keyword in ['content', 'main', 'container', 'wrapper', 'body', 'panel']):
                                potential_containers.append(el)
                                break
    
    # If we didn't find obvious containers, use the biggest divs by child count
    if not potential_containers:
        sorted_by_children = sorted([e for e in elements if e['tag'] == 'div' and e.get('childCount', 0) > 3], 
                                    key=lambda x: x.get('childCount', 0), 
                                    reverse=True)
        potential_containers = sorted_by_children[:5]  # Top 5 divs with most children
    
    return potential_containers

def get_container_children(elements, container):
    """Get child elements of a container"""
    container_selector = container['selector']
    # Simple heuristic: elements that have this container in their path
    return [e for e in elements if container_selector in e.get('elementPath', '')]

def print_element_summary(elements):
    """Print element summary information"""
    print(f"\n{'='*80}\nFound {len(elements)} interactive/visible elements\n{'='*80}")
    
    interactive_count = len([e for e in elements if e.get('isInteractive')])
    form_count = len([e for e in elements if e.get('isFormElement')])
    
    print(f"Interactive elements: {interactive_count}")
    print(f"Form elements: {form_count}")
    print(f"Other elements: {len(elements) - interactive_count - form_count}")
    
    print("\nMain interactive elements:")
    for i, el in enumerate([e for e in elements if e.get('isInteractive')][:10]):  # Only show first 10
        selector = el['selector']
        text = el.get('text', '')[:50] + ('...' if len(el.get('text', '')) > 50 else '')
        print(f"  {i+1}. [{el['tag']}] {text}")
        print(f"     Selector: {selector}")
        
        # Show key attributes
        attrs = []
        for key in ['id', 'name', 'aria-label', 'role', 'type', 'data-id', 'data-name']:
            if 'attributes' in el and key in el['attributes']:
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
import os
import json
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
    
    chrome_options=Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    try:
        # Try to use local ChromeDriver first
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        print("Chrome driver initialized locally")
    except Exception as local_error:
        print(f"Failed to initialize local Chrome driver: {str(local_error)}")
        try:
            # Try to use remote WebDriver as fallback
            driver = webdriver.Remote(command_executor='http://localhost:4444', options=chrome_options)
            print("Chrome driver initialized remotely")
        except Exception as remote_error:
            print(f"Failed to initialize remote Chrome driver: {str(remote_error)}")
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
        
        # Display page structure if available
        structure_file = "page_structure.md"
        if os.path.exists(structure_file):
            print(f"\\nPage structure analysis is available in '{structure_file}'")
            
        # Demo of how to use automation class methods
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
            print("3. Show page elements")
            print("4. Exit")
            
            choice = input("Enter choice (1-4): ")
            
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
                # Show page elements from JSON
                elements_file = "page_elements.json"
                if os.path.exists(elements_file):
                    try:
                        with open(elements_file, 'r', encoding='utf-8') as f:
                            elements = json.load(f)
                        
                        print(f"\\nFound {len(elements)} elements in {elements_file}")
                        print("Interactive elements:")
                        
                        for i, el in enumerate([e for e in elements if e.get('isInteractive', False)][:10]):
                            text = el.get('text', '').strip() or el.get('directText', '').strip() or "[No text]"
                            print(f"{i+1}. [{el['tag']}] {text[:50]}")
                            print(f"   Selector: {el['selector']}")
                        
                        print("...and more elements (see full details in page_elements.json)")
                    except Exception as e:
                        print(f"Error reading elements file: {str(e)}")
                else:
                    print(f"Elements file '{elements_file}' not found")
            
            elif choice == '4':
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
            if el.get('tag') in ['input', 'textarea']:
                # Create method name
                method_name_base = ""
                
                # Try to get name from attributes
                for attr in ['id', 'name', 'placeholder']:
                    if attr in el.get('attributes', {}):
                        method_name_base = el['attributes'][attr]
                        break
                
                # If no name, use tag and index
                if not method_name_base:
                    method_name_base = f"{el.get('tag', 'input')}_{i}"
                
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
                selector = el.get('selector', '').replace("'", "\\'")
                
                # Description
                description = el.get('attributes', {}).get('placeholder', '') or el.get('attributes', {}).get('name', '') or el.get('attributes', {}).get('id', '') or f"{el.get('tag', 'input')} field"
                
                # Generate method
                f.write(f"    async def {method_name}(self, text: str) -> Dict[str, Any]:\n")
                f.write(f"        \"\"\"Fill form field: {description}\n\n")
                f.write(f"        Selector: {el.get('selector')}\n")
                f.write(f"        Element type: {el.get('tag')}\n\n")
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

        f.write("    async def is_element_visible(self, selector: str) -> bool:\n")
        f.write("        \"\"\"Check if element is visible\n\n")
        f.write("        Args:\n")
        f.write("            selector: CSS selector\n\n")
        f.write("        Returns:\n")
        f.write("            True if element is visible, False otherwise\n")
        f.write("        \"\"\"\n")
        f.write("        try:\n")
        f.write("            element = await self.session.wait_for_selector(selector, timeout=2)\n")
        f.write("            return element is not None\n")
        f.write("        except Exception:\n")
        f.write("            return False\n\n")
        
        f.write("    async def execute_custom_action(self, selector: str, action_name: str) -> Dict[str, Any]:\n")
        f.write("        \"\"\"Execute a custom action on an element\n\n")
        f.write("        Args:\n")
        f.write("            selector: CSS selector\n")
        f.write("            action_name: Name of the action to perform\n\n")
        f.write("        Returns:\n")
        f.write("            Operation result\n")
        f.write("        \"\"\"\n")
        f.write("        try:\n")
        f.write("            element = await self.session.wait_for_selector(selector)\n")
        f.write("            if not element:\n")
        f.write("                return {\n")
        f.write("                    \"status\": \"error\",\n")
        f.write("                    \"message\": \"Element not found\"\n")
        f.write("                }\n")
        f.write("                \n")
        f.write("            # Custom action logic can be implemented here\n")
        f.write("            logger.info(f\"Executing {action_name} on {selector}\")\n")
        f.write("            \n")
        f.write("            # Example: hover\n")
        f.write("            if action_name == 'hover':\n")
        f.write("                # Implement hover using JavaScript\n")
        f.write("                script = \"\"\"arguments[0].dispatchEvent(new MouseEvent('mouseover', {\n")
        f.write("                    'view': window,\n")
        f.write("                    'bubbles': true,\n")
        f.write("                    'cancelable': true\n")
        f.write("                }));\"\"\"\n")
        f.write("                await self.session.execute_script(script, element)\n")
        f.write("                return {\n")
        f.write("                    \"status\": \"success\",\n")
        f.write("                    \"message\": f\"{action_name} executed successfully\"\n")
        f.write("                }\n")
        f.write("            \n")
        f.write("            return {\n")
        f.write("                \"status\": \"error\",\n")
        f.write("                \"message\": f\"Unknown action: {action_name}\"\n")
        f.write("            }\n")
        f.write("        except Exception as e:\n")
        f.write("            logger.error(f\"Custom action failed: {str(e)}\")\n")
        f.write("            return {\n")
        f.write("                \"status\": \"error\",\n")
        f.write("                \"message\": f\"Custom action failed: {str(e)}\"\n")
        f.write("            }\n")
        
    print(f"Generated page automation class to {filename}")        # Generate form fill methods

def main():
    url = input("Enter URL to analyze (or press Enter to analyze current page): ")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Initialize Chrome driver
    try:
        # Try to use local ChromeDriver first
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        print("Using local Chrome driver")
    except Exception as local_error:
        print(f"Failed to initialize local Chrome driver: {str(local_error)}")
        try:
            # Try to use remote WebDriver as fallback
            driver = webdriver.Remote(command_executor='http://localhost:4444', options=chrome_options)
            print("Using remote Chrome driver")
        except Exception as remote_error:
            print(f"Failed to initialize Chrome driver: {str(remote_error)}")
            return
    
    try:
        if url:
            driver.get(url)
            print(f"Analyzing: {url}")
        else:
            print("Analyzing current page")
            url = driver.current_url
        
        # Wait for user to confirm page is fully loaded
        input("Please confirm the page is fully loaded and logged in (if needed), then press Enter to continue...")
        
        # Create output directory
        output_dir = create_output_dir()
        
        # Get element information
        print("Collecting page element information...")
        elements = get_element_info(driver)
        
        # Get page title
        page_title = driver.title
        
        # Print summary
        print_element_summary(elements)
        
        # Filter elements to essential ones only
        print("\nFiltering elements to keep only essential information...")
        essential_elements = filter_essential_elements(elements)
        print(f"Reduced from {len(elements)} to {len(essential_elements)} essential elements")
        
        # Generate page structure document
        print("\nGenerating page structure analysis document...")
        structure_file = os.path.join(output_dir, "page_structure.md")
        generate_page_structure(elements, title=page_title, url=url, filename=structure_file)
        
        # Save elements to files
        json_file = os.path.join(output_dir, "page_elements.json")
        save_elements_to_file(essential_elements, json_file)
        
        # Generate constants and automation class
        selectors_file = os.path.join(output_dir, "page_selectors.py")
        automation_file = os.path.join(output_dir, "page_automation.py")
        
        print("\nGenerating page element constants and automation class...")
        generate_element_constants(essential_elements, selectors_file)
        generate_page_automation_class(essential_elements, automation_file)
        
        # Copy template files for PageSession and test.py
        print("\nGenerating PageSession class and test script...")
        copy_template_files(output_dir)
        
        print(f"\nAnalysis complete! All files saved to {output_dir} directory")
        print(f"- Page structure analysis: {structure_file}")
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
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()        # Generate utility methods
