import json
import time
import os
import re
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup

# Menu Item Class for building the menu tree
class MenuItem:
    def __init__(self, element, text, level=1):
        self.element = element
        self.text = text
        self.level = level
        self.children = []
        self.parent = None
        self.iframe_content = None
        self.iframe_selectors = None
        self.path = []  # Full path from root to this menu item
    
    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        
    def get_full_path(self):
        if not self.path:
            # Calculate full path if not already done
            path = []
            current = self
            while current:
                path.insert(0, current.text)
                current = current.parent
            self.path = path
        return self.path
    
    def to_dict(self):
        return {
            "text": self.text,
            "level": self.level,
            "path": self.get_full_path(),
            "children": [child.to_dict() for child in self.children],
            "has_iframe": self.iframe_content is not None,
        }

class SPANavigator:
    def __init__(self, driver, output_dir="spa_navigator_output"):
        self.driver = driver
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.menu_tree = []
        self.menu_items_by_path = {}  # Dictionary to look up menu items by path
        self.current_iframe = None
    
    def extract_menu_structure(self, menu_selector=None):
        """Extract the menu structure from the left sidebar"""
        print("Extracting menu structure from sidebar...")
        
        if not menu_selector:
            # Common selectors for left sidebar menus
            potential_selectors = [
                ".sidebar", "#sidebar", ".left-menu", "#left-menu",
                ".nav-sidebar", "#nav-sidebar", ".sidebar-menu", "#sidebar-menu",
                "nav.sidebar", ".left-sidebar", "#left-sidebar",
                ".aside-menu", "#aside-menu", ".main-menu", "#main-menu"
            ]
            
            # Try to find a menu container using common selectors
            menu_container = None
            for selector in potential_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        menu_container = elements[0]
                        print(f"Found menu container with selector: {selector}")
                        break
                except:
                    pass
            
            if not menu_container:
                # Fallback: try to find menu using common menu item selectors
                try:
                    # Look for elements with menu-like classes or tags
                    menu_items = self.driver.find_elements(By.CSS_SELECTOR, 
                        "a.nav-link, li.nav-item, .menu-item, .sidebar-item")
                    
                    if menu_items:
                        # Find a common ancestor as the menu container
                        menu_container = self._find_common_ancestor(menu_items)
                        print("Found menu container by common ancestor")
                except:
                    pass
            
            if not menu_container:
                print("Warning: Could not automatically detect menu container")
                # Use body as a fallback
                menu_container = self.driver.find_element(By.TAG_NAME, "body")
        else:
            try:
                menu_container = self.driver.find_element(By.CSS_SELECTOR, menu_selector)
            except:
                print(f"Error: Could not find menu container with selector {menu_selector}")
                menu_container = self.driver.find_element(By.TAG_NAME, "body")
        
        # Now extract menu items
        self._build_menu_tree(menu_container)
        
        # Save the menu structure as JSON
        self._save_menu_structure()
        
        print(f"Extracted {len(self.menu_items_by_path)} menu items")
        return self.menu_tree
    
    def _find_common_ancestor(self, elements, max_depth=5):
        """Find the common ancestor of a set of elements"""
        if not elements:
            return None
        
        # Start with the parent of the first element
        common = self.driver.execute_script("return arguments[0].parentElement;", elements[0])
        
        for element in elements[1:]:
            # Get ancestors of this element
            ancestors = []
            current = element
            for i in range(max_depth):
                current = self.driver.execute_script("return arguments[0].parentElement;", current)
                if not current:
                    break
                ancestors.append(current)
            
            # Find the first common ancestor in our list
            found = False
            for i in range(max_depth):
                test_ancestor = self.driver.execute_script(f"return arguments[0].parentElement;", common)
                if not test_ancestor:
                    break
                    
                # Check if this is in the ancestors list
                for ancestor in ancestors:
                    if self.driver.execute_script("return arguments[0] === arguments[1]", test_ancestor, ancestor):
                        common = test_ancestor
                        found = True
                        break
                
                if found:
                    break
        
        return common
    
    def _build_menu_tree(self, container):
        """Build a hierarchical menu tree from container element"""
        
        # First, try to find all potential menu items, preferring anchor tags
        menu_items = container.find_elements(By.CSS_SELECTOR, "a, li, div")
        
        # Filter to only interactive or menu-like elements
        potential_menu_items = []
        for item in menu_items:
            classes = item.get_attribute("class") or ""
            tag_name = item.tag_name
            
            # Check if this item is an interactive menu item
            is_menu_item = (
                tag_name == "a" or  # Most menu items are anchors
                "menu" in classes.lower() or 
                "nav-item" in classes.lower() or
                "sidebar-item" in classes.lower() or
                (item.get_attribute("role") in ["menuitem", "treeitem", "button"]) or
                (item.get_attribute("aria-expanded") is not None)  # Expandable items
            )
            
            if is_menu_item and item.is_displayed():
                # Get text content
                text = item.text.strip()
                if text:  # Only include items with text
                    potential_menu_items.append(item)
        
        # Sort by Y position to preserve original order
        potential_menu_items.sort(key=lambda x: x.rect['y'])
        
        # Analyze items to determine levels based on indentation/classes/structure
        menu_items_with_levels = self._determine_menu_levels(potential_menu_items)
        
        # Build the hierarchical structure
        self._build_hierarchy(menu_items_with_levels)
    
    def _determine_menu_levels(self, items):
        """Determine the hierarchy level of each menu item"""
        items_with_levels = []
        
        # First pass: check for level indicators in class names or indentation
        for item in items:
            text = item.text.strip()
            classes = item.get_attribute("class") or ""
            level = 1  # Default level
            
            # Check for level in classes (e.g., "menu-level-2", "submenu", etc.)
            if "submenu" in classes.lower() or "child" in classes.lower():
                level = 2
            elif "sub-submenu" in classes.lower() or "grandchild" in classes.lower():
                level = 3
            
            # Try to extract numeric level from class
            level_match = re.search(r'level-(\d+)', classes.lower())
            if level_match:
                level = int(level_match.group(1))
            
            # Check indentation using position
            left_pos = item.rect['x']
            if left_pos > 50:
                # Roughly estimate level based on indentation
                level = max(level, int((left_pos - 20) / 15))
            
            items_with_levels.append(MenuItem(item, text, level))
        
        # Second pass: refine levels based on context and position
        if len(items_with_levels) > 1:
            for i in range(1, len(items_with_levels)):
                curr = items_with_levels[i]
                prev = items_with_levels[i-1]
                
                # Adjust level if seems out of place
                if curr.level > prev.level + 1:
                    curr.level = prev.level + 1
                
                # If this item is right after a parent and has similar x-position
                prev_left = prev.element.rect['x']
                curr_left = curr.element.rect['x']
                if abs(curr_left - prev_left) < 10 and curr.level > prev.level:
                    curr.level = prev.level
        
        return items_with_levels
    
    def _build_hierarchy(self, items_with_levels):
        """Build the menu hierarchy based on the determined levels"""
        if not items_with_levels:
            return
        
        # Start with the root
        self.menu_tree = []
        current_parents = {0: None}  # level -> current parent at that level
        
        for item in items_with_levels:
            # Find the parent of this item
            parent = current_parents.get(item.level - 1)
            
            if parent is None:
                # This is a top-level item
                self.menu_tree.append(item)
            else:
                # Add to parent
                parent.add_child(item)
            
            # Update current parent at this level
            current_parents[item.level] = item
            
            # Create lookup for easy access
            item_path = "/".join(item.get_full_path())
            self.menu_items_by_path[item_path] = item
    
    def _save_menu_structure(self):
        """Save the extracted menu structure to a JSON file"""
        menu_data = [item.to_dict() for item in self.menu_tree]
        
        with open(os.path.join(self.output_dir, "menu_structure.json"), "w", encoding="utf-8") as f:
            json.dump(menu_data, f, ensure_ascii=False, indent=2)
    
    def _retry_stale_element(self, max_attempts=3):
        """
        装饰器：处理 StaleElementReferenceException 的重试逻辑
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except StaleElementReferenceException:
                        if attempt == max_attempts - 1:  # 最后一次尝试
                            raise
                        print(f"遇到 StaleElementReferenceException，尝试重新查找元素 (尝试 {attempt+1}/{max_attempts})")
                        time.sleep(0.5)  # 等待一段时间再重试
                return None  # 不应该到达这里
            return wrapper
        return decorator
    
    def _navigate_to_menu_item(self, menu_item):
        """
        导航到指定的菜单项，处理 stale element 问题
        """
        @self._retry_stale_element(max_attempts=3)
        def click_menu_element():
            # 滚动到元素位置
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", menu_item.element)
            time.sleep(0.5)  # 等待滚动完成
            
            # 点击元素
            menu_item.element.click()
            
            # 等待页面加载
            time.sleep(1)
            return True
            
        return click_menu_element()
    
    def navigate_to_menu_item(self, path):
        """
        导航到菜单路径指定的项
        """
        if isinstance(path, str):
            # 转换字符串路径为列表
            path = path.strip().split("/")
        
        # 查找菜单项
        item_path = "/".join(path)
        menu_item = self.menu_items_by_path.get(item_path)
        
        if not menu_item:
            print(f"错误：找不到菜单项: {item_path}")
            return False
        
        # 首先展开父菜单
        self._expand_parents(menu_item)
        
        # 点击目标菜单项
        try:
            # 重新获取菜单元素引用
            # 这是关键：我们不使用存储的元素引用，而是重新查找元素
            try:
                # 根据存储的选择器重新定位元素
                selector = self._get_element_selector(menu_item.element)
                if selector:
                    element = self.driver.find_element(*selector)
                    menu_item.element = element  # 更新引用
            except (NoSuchElementException, TypeError):
                # 如果无法通过选择器找到，尝试使用文本内容
                xpath = f"//a[contains(text(), '{menu_item.text}')]|//button[contains(text(), '{menu_item.text}')]|//div[contains(text(), '{menu_item.text}') and (@role='menuitem' or @role='treeitem' or contains(@class, 'menu') or contains(@class, 'nav'))]"
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    menu_item.element = element  # 更新引用
                except NoSuchElementException:
                    print(f"无法重新定位菜单元素: {menu_item.text}")
                    return False
            
            # 现在使用更新后的元素点击
            success = self._navigate_to_menu_item(menu_item)
            
            if success:
                # 提取iframe内容
                iframe_content = self._extract_iframe_content()
                if iframe_content:
                    menu_item.iframe_content = iframe_content
                    menu_item.iframe_selectors = self._extract_iframe_selectors()
                    print(f"已提取iframe内容和选择器")
                    
                    # 更新当前iframe
                    self.current_iframe = {
                        "menu_path": item_path,
                        "content": iframe_content
                    }
                    
                    # 保存iframe内容
                    self._save_iframe_content(item_path, iframe_content)
                    self._save_iframe_selectors(item_path, menu_item.iframe_selectors)
                    
                    return True
                else:
                    print("点击菜单项后未检测到iframe")
                    return False
            else:
                print(f"菜单项点击失败: {item_path}")
                return False
                
        except Exception as e:
            print(f"导航到菜单项 {item_path} 出错: {str(e)}")
            return False
    
    def _get_element_selector(self, element):
        """
        尝试为元素创建一个可靠的选择器
        返回一个 (By.XXX, 'selector') 元组
        """
        try:
            # 尝试使用ID
            element_id = element.get_attribute('id')
            if element_id:
                return (By.ID, element_id)
            
            # 尝试使用name
            element_name = element.get_attribute('name')
            if element_name:
                return (By.NAME, element_name)
            
            # 使用XPath通过文本内容
            element_text = element.text.strip()
            if element_text:
                xpath = f"//*[contains(text(), '{element_text}')]"
                return (By.XPATH, xpath)
            
            # 最后尝试CSS类选择器
            element_class = element.get_attribute('class')
            if element_class:
                class_names = element_class.split()
                if class_names:
                    css_selector = element.tag_name
                    for class_name in class_names:
                        css_selector += f".{class_name}"
                    return (By.CSS_SELECTOR, css_selector)
            
            return None
        except:
            return None
    
    def _expand_parents(self, menu_item):
        """
        展开所有父菜单，处理可能的 stale element 问题
        """
        parents = []
        current = menu_item.parent
        
        # 构建需要展开的父级菜单列表
        while current:
            parents.insert(0, current)
            current = current.parent
        
        # 逐个展开父级菜单
        for parent in parents:
            try:
                # 重新获取父菜单元素的引用
                try:
                    selector = self._get_element_selector(parent.element)
                    if selector:
                        element = self.driver.find_element(*selector)
                        parent.element = element  # 更新引用
                except (NoSuchElementException, TypeError):
                    # 如果无法通过选择器找到，尝试文本匹配
                    xpath = f"//a[contains(text(), '{parent.text}')]|//button[contains(text(), '{parent.text}')]|//div[contains(text(), '{parent.text}') and (@role='menuitem' or @role='treeitem' or contains(@class, 'menu') or contains(@class, 'nav'))]"
                    try:
                        element = self.driver.find_element(By.XPATH, xpath)
                        parent.element = element  # 更新引用
                    except NoSuchElementException:
                        print(f"无法重新定位父菜单元素: {parent.text}")
                        continue
                
                # 检查是否已展开
                expanded = False
                try:
                    expanded = parent.element.get_attribute("aria-expanded") == "true"
                except:
                    # 如果获取属性失败，继续尝试点击
                    pass
                
                # 如果未展开，点击展开
                if not expanded:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent.element)
                    time.sleep(0.5)  # 等待滚动完成
                    
                    # 使用装饰器处理点击操作中可能的 stale element 问题
                    @self._retry_stale_element(max_attempts=3)
                    def click_parent():
                        parent.element.click()
                        return True
                    
                    click_parent()
                    time.sleep(0.8)  # 等待展开动画
                    print(f"已展开父级菜单: {parent.text}")
            except Exception as e:
                print(f"展开父级菜单 {parent.text} 时出错: {str(e)}")
    
    
    def _extract_iframe_content(self):
        """Extract content from the main iframe that appears after clicking a menu item"""
        try:
            # First, look for iframes in the page
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            if not iframes:
                print("No iframes found on the page")
                return None
            
            # Filter to currently visible iframes
            visible_iframes = [frame for frame in iframes if frame.is_displayed()]
            
            if not visible_iframes:
                print("No visible iframes found")
                return None
            
            # Choose the most prominent iframe (largest or most centered)
            target_iframe = max(visible_iframes, key=lambda f: f.size['width'] * f.size['height'])
            
            # Switch to the iframe
            self.driver.switch_to.frame(target_iframe)
            
            # Extract content
            iframe_content = {
                "title": self.driver.title,
                "url": self.driver.current_url,
                "text_content": self.driver.find_element(By.TAG_NAME, "body").text,
                "html": self.driver.page_source
            }
            
            # Extract structural components
            iframe_content.update(self._extract_structural_content())
            
            # Switch back to main content
            self.driver.switch_to.default_content()
            
            return iframe_content
            
        except Exception as e:
            print(f"Error extracting iframe content: {str(e)}")
            # Make sure we return to the main document
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return None
    
    def _extract_structural_content(self):
        """Extract structured content from the current frame"""
        try:
            # Using BeautifulSoup for better parsing
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # Extract headings
            headings = []
            for i in range(1, 7):
                for heading in soup.find_all(f'h{i}'):
                    if heading.text.strip():
                        headings.append({
                            "level": i,
                            "text": heading.text.strip()
                        })
            
            # Extract paragraphs
            paragraphs = [p.text.strip() for p in soup.find_all('p') if p.text.strip()]
            
            # Extract tables
            tables = []
            for table in soup.find_all('table'):
                table_data = []
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if cells:
                        row_data = [cell.text.strip() for cell in cells]
                        table_data.append(row_data)
                
                if table_data:
                    tables.append(table_data)
            
            # Extract lists
            lists = []
            for ul in soup.find_all(['ul', 'ol']):
                list_items = []
                for li in ul.find_all('li'):
                    if li.text.strip():
                        list_items.append(li.text.strip())
                
                if list_items:
                    lists.append({
                        "type": ul.name,
                        "items": list_items
                    })
            
            # Extract forms and inputs
            forms = []
            for form in soup.find_all('form'):
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', 'get'),
                    "inputs": []
                }
                
                for input_tag in form.find_all(['input', 'textarea', 'select']):
                    input_data = {
                        "type": input_tag.name if input_tag.name != 'input' else input_tag.get('type', 'text'),
                        "name": input_tag.get('name', ''),
                        "id": input_tag.get('id', ''),
                        "placeholder": input_tag.get('placeholder', '')
                    }
                    form_data["inputs"].append(input_data)
                
                forms.append(form_data)
            
            # Extract buttons
            buttons = []
            for button in soup.find_all(['button', 'a']):
                text = button.text.strip()
                if text:
                    buttons.append({
                        "tag": button.name,
                        "text": text,
                        "id": button.get('id', ''),
                        "class": button.get('class', [])
                    })
            
            # Create a meaningful summary
            main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('div', class_='main-content')
            summary = ""
            
            if main_content:
                summary = main_content.text.strip()[:500]  # First 500 chars
            elif headings:
                # Use headings to build a summary
                summary = " - ".join([h["text"] for h in headings[:3]])
            else:
                # Fallback to first 500 chars of body
                summary = soup.body.text.strip()[:500] if soup.body else ""
            
            return {
                "headings": headings,
                "paragraphs": paragraphs[:10],  # Limit to first 10 paragraphs
                "tables": tables,
                "lists": lists,
                "forms": forms,
                "buttons": buttons,
                "summary": summary
            }
        
        except Exception as e:
            print(f"Error extracting structural content: {str(e)}")
            return {
                "headings": [],
                "paragraphs": [],
                "tables": [],
                "lists": [],
                "forms": [],
                "buttons": [],
                "summary": "Error extracting content"
            }
    
    def _extract_iframe_selectors(self):
        """Extract interactive elements from the current iframe"""
        try:
            # Using JavaScript to extract interactive elements
            js_script = """
            function getInteractiveElements() {
                // Find all interactive elements
                const elements = [];
                
                // Find buttons
                document.querySelectorAll('button, .btn, [role="button"]').forEach(el => {
                    if (isVisible(el) && !elements.some(e => e.element === el)) {
                        elements.push({
                            type: 'button',
                            text: el.textContent.trim(),
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            name: el.getAttribute('name') || null,
                            classes: el.className || null,
                            selector: getBestSelector(el)
                        });
                    }
                });
                
                // Find links (but not buttons styled as links)
                document.querySelectorAll('a:not(.btn):not([role="button"])').forEach(el => {
                    if (isVisible(el) && !elements.some(e => e.element === el)) {
                        elements.push({
                            type: 'link',
                            text: el.textContent.trim(),
                            tag: 'a',
                            href: el.href || null,
                            id: el.id || null,
                            classes: el.className || null,
                            selector: getBestSelector(el)
                        });
                    }
                });
                
                // Find form inputs
                document.querySelectorAll('input, textarea, select').forEach(el => {
                    if (isVisible(el) && !elements.some(e => e.element === el)) {
                        elements.push({
                            type: 'input',
                            inputType: el.type || el.tagName.toLowerCase(),
                            label: getInputLabel(el),
                            placeholder: el.placeholder || null,
                            id: el.id || null,
                            name: el.name || null,
                            classes: el.className || null,
                            selector: getBestSelector(el)
                        });
                    }
                });
                
                return elements;
                
                // Helper functions
                function isVisible(el) {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           parseFloat(style.opacity) > 0 &&
                           el.offsetWidth > 0 && 
                           el.offsetHeight > 0;
                }
                
                function getInputLabel(input) {
                    // Try to find label by for attribute
                    if (input.id) {
                        const label = document.querySelector(`label[for="${input.id}"]`);
                        if (label) return label.textContent.trim();
                    }
                    
                    // Try to find parent label
                    let parent = input.parentElement;
                    while (parent && parent !== document.body) {
                        if (parent.tagName.toLowerCase() === 'label') {
                            return parent.textContent.trim().replace(input.value, '').trim();
                        }
                        parent = parent.parentElement;
                    }
                    
                    // Return placeholder or name as fallback
                    return input.placeholder || input.name || '';
                }
                
                function getBestSelector(element) {
                    // Try ID selector
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    // Try attribute selectors
                    if (element.name) {
                        return `${element.tagName.toLowerCase()}[name="${element.name}"]`;
                    }
                    
                    if (element.placeholder) {
                        return `${element.tagName.toLowerCase()}[placeholder="${element.placeholder}"]`;
                    }
                    
                    // For buttons, try text content
                    if ((element.tagName.toLowerCase() === 'button' || element.type === 'button') && element.textContent.trim()) {
                        return `${element.tagName.toLowerCase()}:contains("${element.textContent.trim()}")`;
                    }
                    
                    // Try class selectors
                    if (element.className) {
                        const classes = element.className.split(' ').filter(c => c && !c.includes(' '));
                        if (classes.length > 0) {
                            // Use more specific classes if available to avoid common utility classes
                            const specificClasses = classes.filter(c => !c.match(/^(btn|button|input|form|w-|h-|text-)/));
                            if (specificClasses.length > 0) {
                                return `${element.tagName.toLowerCase()}.${specificClasses.join('.')}`;
                            }
                            return `${element.tagName.toLowerCase()}.${classes.join('.')}`;
                        }
                    }
                    
                    // Fallback to tag name
                    return element.tagName.toLowerCase();
                }
            }
            
            return getInteractiveElements();
            """
            
            # Execute the script
            elements = self.driver.execute_script(js_script)
            
            # Group elements by type
            selectors = {
                "buttons": [],
                "links": [],
                "inputs": []
            }
            
            for element in elements:
                element_type = element.get("type")
                if element_type == "button":
                    selectors["buttons"].append(element)
                elif element_type == "link":
                    selectors["links"].append(element)
                elif element_type == "input":
                    selectors["inputs"].append(element)
            
            return selectors
            
        except Exception as e:
            print(f"Error extracting iframe selectors: {str(e)}")
            return {"buttons": [], "links": [], "inputs": []}
    
    def _save_iframe_content(self, item_path, content):
        """Save iframe content to a file"""
        # Create a safe filename from the menu path
        safe_path = "_".join([re.sub(r'[\\/*?:"<>|]', "", part) for part in item_path.split("/")])
        
        # Save content as JSON
        content_file = os.path.join(self.output_dir, f"{safe_path}_content.json")
        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        # Also save a readable text summary
        summary_file = os.path.join(self.output_dir, f"{safe_path}_summary.txt")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(f"Menu Path: {item_path}\n\n")
            f.write(f"Title: {content.get('title', 'Unknown')}\n")
            f.write(f"URL: {content.get('url', 'Unknown')}\n\n")
            
            f.write("=== SUMMARY ===\n")
            f.write(content.get("summary", "No summary available") + "\n\n")
            
            f.write("=== HEADINGS ===\n")
            for heading in content.get("headings", []):
                level = heading.get("level", 1)
                text = heading.get("text", "")
                f.write("  " * (level-1) + text + "\n")
            
            f.write("\n=== KEY CONTENT ===\n")
            for para in content.get("paragraphs", [])[:5]:
                f.write(para + "\n\n")
                
            if content.get("tables"):
                f.write("\n=== TABLES ===\n")
                f.write(f"{len(content['tables'])} tables found\n")
                
            if content.get("forms"):
                f.write("\n=== FORMS ===\n")
                f.write(f"{len(content['forms'])} forms found\n")
                for form in content.get("forms", []):
                    f.write(f"Form action: {form.get('action', 'None')}\n")
                    f.write(f"Inputs: {len(form.get('inputs', []))}\n")
        
        print(f"Saved iframe content and summary for {item_path}")
    
    def _save_iframe_selectors(self, item_path, selectors):
        """Save iframe selectors to a file"""
        # Create a safe filename from the menu path
        safe_path = "_".join([re.sub(r'[\\/*?:"<>|]', "", part) for part in item_path.split("/")])
        
        # Save selectors as JSON
        selectors_file = os.path.join(self.output_dir, f"{safe_path}_selectors.json")
        with open(selectors_file, "w", encoding="utf-8") as f:
            json.dump(selectors, f, ensure_ascii=False, indent=2)
        
        # Also save as Python code
        py_file = os.path.join(self.output_dir, f"{safe_path}_selectors.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(f"# Selectors for {item_path}\n")
            f.write("# Generated at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            
            # Write button constants
            f.write("# Buttons\n")
            for i, button in enumerate(selectors.get("buttons", [])):
                name = re.sub(r'[^a-zA-Z0-9_]', '_', button.get('text', f"button_{i}")).upper()
                selector = button.get("selector", "")
                f.write(f"{name} = '{selector}'  # {button.get('text', '')}\n")
            
            f.write("\n# Links\n")
            for i, link in enumerate(selectors.get("links", [])):
                name = re.sub(r'[^a-zA-Z0-9_]', '_', link.get('text', f"link_{i}")).upper()
                selector = link.get("selector", "")
                f.write(f"{name} = '{selector}'  # {link.get('text', '')}\n")
            
            f.write("\n# Inputs\n")
            for i, input_el in enumerate(selectors.get("inputs", [])):
                label = input_el.get('label', '')
                name = re.sub(r'[^a-zA-Z0-9_]', '_', label or f"input_{i}").upper()
                selector = input_el.get("selector", "")
                f.write(f"{name} = '{selector}'  # {input_el.get('inputType', '')} - {label}\n")
        
        print(f"Saved iframe selectors for {item_path}")
    
    def navigate_all_menu_items(self):
        """Navigate to all menu items and extract their contents"""
        print("Navigating to all menu items to extract content...")
        
        def traverse_menu_tree(menu_items, current_path=[]):
            """Recursively traverse menu tree and extract content"""
            for item in menu_items:
                # Build the full path to this item
                item_path = current_path + [item.text]
                
                # Navigate to this menu item
                print(f"Navigating to: {'/'.join(item_path)}")
                self.navigate_to_menu_item(item_path)
                
                # Allow time for iframe to load completely
                time.sleep(1)
                
                # Recursively navigate children
                if item.children:
                    traverse_menu_tree(item.children, item_path)
        
        # Start traversal from the root menu items
        traverse_menu_tree(self.menu_tree)
        
        # Generate summary HTML report
        self._generate_navigation_report()
        
        print("Completed navigation of all menu items")
    
    def _generate_navigation_report(self):
        """Generate an HTML report of all menu items and their contents"""
        report_file = os.path.join(self.output_dir, "menu_navigation_report.html")
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SPA Navigation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        h1, h2, h3 { color: #333; }
        .menu-tree { margin-left: 20px; }
        .menu-item { margin: 5px 0; }
        .menu-item.has-iframe { font-weight: bold; }
        .level-1 { margin-left: 0px; }
        .level-2 { margin-left: 20px; }
        .level-3 { margin-left: 40px; }
        .level-4 { margin-left: 60px; }
        .menu-details { 
            background-color: #f5f5f5; 
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
        }
        .hidden { display: none; }
        .toggle-btn {
            background: #eee;
            border: 1px solid #ddd;
            padding: 3px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
    </style>
    <script>
        function toggleDetails(id) {
            const details = document.getElementById(id);
            if (details.classList.contains('hidden')) {
                details.classList.remove('hidden');
            } else {
                details.classList.add('hidden');
            }
        }
    </script>
</head>
<body>
    <h1>SPA Navigation Report</h1>
    <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    
    <h2>Menu Structure</h2>
    <div class="menu-tree">
""")
            
            # Recursively write menu items
            def write_menu_items(items, f, prefix=""):
                for i, item in enumerate(items):
                    item_id = f"{prefix}{i}"
                    item_path = "/".join(item.get_full_path())
                    has_iframe = "has-iframe" if item.iframe_content else ""
                    
                    f.write(f'<div class="menu-item level-{item.level} {has_iframe}">\n')
                    
                    # If the item has iframe content, make it clickable
                    if item.iframe_content:
                        f.write(f'<span>{item.text}</span> <button class="toggle-btn" onclick="toggleDetails(\'details-{item_id}\')">Details</button>\n')
                        
                        # Write details section (initially hidden)
                        f.write(f'<div id="details-{item_id}" class="menu-details hidden">\n')
                        f.write(f'<h4>Path: {item_path}</h4>\n')
                        
                        # Write summary
                        if "summary" in item.iframe_content:
                            f.write(f'<p><strong>Summary:</strong> {item.iframe_content["summary"][:200]}...</p>\n')
                        
                        # Write headings
                        if "headings" in item.iframe_content and item.iframe_content["headings"]:
                            f.write("<p><strong>Key Headings:</strong></p>\n<ul>\n")
                            for heading in item.iframe_content["headings"][:5]:
                                f.write(f'<li>{heading["text"]}</li>\n')
                            f.write("</ul>\n")
                        
                        # Write interactive elements summary
                        if item.iframe_selectors:
                            buttons = item.iframe_selectors.get("buttons", [])
                            inputs = item.iframe_selectors.get("inputs", [])
                            links = item.iframe_selectors.get("links", [])
                            
                            f.write("<p><strong>Interactive Elements:</strong></p>\n")
                            f.write(f"<p>{len(buttons)} buttons, {len(inputs)} inputs, {len(links)} links</p>\n")
                            
                            if buttons:
                                f.write("<p><strong>Key Buttons:</strong></p>\n<ul>\n")
                                for button in buttons[:3]:
                                    f.write(f'<li>{button.get("text", "Unnamed button")}</li>\n')
                                f.write("</ul>\n")
                        
                        f.write('</div>\n')
                    else:
                        f.write(f'<span>{item.text}</span>\n')
                    
                    # Write children recursively
                    if item.children:
                        write_menu_items(item.children, f, prefix=f"{item_id}-")
                    
                    f.write('</div>\n')
            
            # Write menu items
            write_menu_items(self.menu_tree, f)
            
            # Close HTML
            f.write("""
    </div>
    
    <h2>Function Tools</h2>
    <p>The following function tools have been generated:</p>
    <ul>
        <li><strong>navigate_to_menu</strong> - Navigate to a specific menu item by path</li>
        <li><strong>get_current_iframe_content</strong> - Get the content of the currently open iframe</li>
        <li><strong>click_button_in_iframe</strong> - Click a button in the current iframe</li>
        <li><strong>fill_input_in_iframe</strong> - Fill an input in the current iframe</li>
        <li><strong>click_link_in_iframe</strong> - Click a link in the current iframe</li>
    </ul>
    
    <p>See the generated Python module for implementation details.</p>
</body>
</html>
""")
        
        print(f"Generated navigation report: {report_file}")

# Create function tools module for the agent
def generate_function_tools_module(navigator, output_file="spa_function_tools.py"):
    """Generate a Python module with function tools for the agent"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("""# SPA Function Tools for Agent
# Generated at """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """

import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Global driver instance
_driver = None
_navigator = None
_output_dir = "spa_navigator_output"

# Menu structure cache
_menu_structure = None
_current_iframe = None

def initialize_driver():
    \"\"\"Initialize the Chrome driver if not already done\"\"\"
    global _driver, _navigator
    
    if _driver is not None:
        return _driver
    
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize driver
        _driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=chrome_options)
        
        from .spa_navigator import SPANavigator
        _navigator = SPANavigator(_driver, _output_dir)
        
        return _driver
    except Exception as e:
        raise Exception(f"Failed to initialize driver: {str(e)}")

def load_menu_structure():
    \"\"\"Load the menu structure from JSON file\"\"\"
    global _menu_structure
    
    if _menu_structure is not None:
        return _menu_structure
    
    try:
        menu_file = os.path.join(_output_dir, "menu_structure.json")
        if os.path.exists(menu_file):
            with open(menu_file, "r", encoding="utf-8") as f:
                _menu_structure = json.load(f)
            return _menu_structure
        else:
            raise Exception(f"Menu structure file not found: {menu_file}")
    except Exception as e:
        raise Exception(f"Failed to load menu structure: {str(e)}")

def get_menu_structure():
    \"\"\"Function tool: Get the full menu structure\"\"\"
    try:
        menu_structure = load_menu_structure()
        return {
            "status": "success",
            "message": "Menu structure retrieved successfully",
            "menu_structure": menu_structure
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve menu structure: {str(e)}"
        }

def navigate_to_menu(menu_path):
    \"\"\"
    Function tool: Navigate to a specific menu item
    
    Args:
        menu_path (str): The path to the menu item, separated by /
        
    Returns:
        dict: Result of the navigation operation
    \"\"\"
    try:
        global _navigator, _current_iframe
        
        # Initialize driver if needed
        initialize_driver()
        
        # Navigate to the menu item
        if not _navigator:
            raise Exception("Navigator not initialized")
            
        success = _navigator.navigate_to_menu_item(menu_path)
        
        if success:
            # Update current iframe
            _current_iframe = _navigator.current_iframe
            
            # Load iframe content
            safe_path = "_".join([re.sub(r'[\\/*?:"<>|]', "", part) for part in menu_path.split("/")])
            content_file = os.path.join(_output_dir, f"{safe_path}_content.json")
            
            if os.path.exists(content_file):
                with open(content_file, "r", encoding="utf-8") as f:
                    iframe_content = json.load(f)
                
                # Create a summary of the iframe content
                summary = {
                    "title": iframe_content.get("title", "Unknown"),
                    "summary": iframe_content.get("summary", "No summary available"),
                    "headings": [h.get("text") for h in iframe_content.get("headings", [])[:5]],
                    "paragraphs": iframe_content.get("paragraphs", [])[:3],
                }
                
                return {
                    "status": "success",
                    "message": f"Successfully navigated to menu item: {menu_path}",
                    "content": summary
                }
            else:
                return {
                    "status": "success",
                    "message": f"Successfully navigated to menu item: {menu_path}",
                    "content": "No iframe content available"
                }
        else:
            return {
                "status": "error",
                "message": f"Failed to navigate to menu item: {menu_path}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error navigating to menu item: {str(e)}"
        }

def get_current_iframe_content():
    \"\"\"
    Function tool: Get content of the currently open iframe
    
    Returns:
        dict: Iframe content or error message
    \"\"\"
    try:
        global _current_iframe
        
        if not _current_iframe:
            return {
                "status": "error",
                "message": "No iframe is currently open. Please navigate to a menu item first."
            }
        
        # Return the iframe content
        return {
            "status": "success",
            "message": f"Retrieved iframe content for {_current_iframe['menu_path']}",
            "content": _current_iframe['content']
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving iframe content: {str(e)}"
        }

def click_button_in_iframe(button_identifier):
    \"\"\"
    Function tool: Click a button in the current iframe
    
    Args:
        button_identifier (str): Text or selector of the button to click
        
    Returns:
        dict: Result of the click operation
    \"\"\"
    try:
        global _driver, _current_iframe
        
        if not _driver:
            initialize_driver()
            
        if not _current_iframe:
            return {
                "status": "error",
                "message": "No iframe is currently open. Please navigate to a menu item first."
            }
        
        # Switch to the iframe
        # We need to identify the iframe again since the page might have reloaded
        iframes = _driver.find_elements(By.TAG_NAME, "iframe")
        if not iframes:
            return {
                "status": "error",
                "message": "No iframes found on the page"
            }
        
        # Find the visible iframe
        visible_iframes = [frame for frame in iframes if frame.is_displayed()]
        if not visible_iframes:
            return {
                "status": "error",
                "message": "No visible iframes found"
            }
            
        # Switch to the iframe
        _driver.switch_to.frame(visible_iframes[0])
        
        # Try to find the button by selector, text, or partial text
        button = None
        
        # First try CSS selector
        try:
            button = _driver.find_element(By.CSS_SELECTOR, button_identifier)
        except NoSuchElementException:
            pass
            
        # Then try finding by exact text
        if not button:
            try:
                button = _driver.find_element(By.XPATH, f"//button[text()='{button_identifier}']")
            except NoSuchElementException:
                pass
                
        # Then try finding by partial text
        if not button:
            try:
                button = _driver.find_element(By.XPATH, f"//button[contains(text(), '{button_identifier}')]")
            except NoSuchElementException:
                pass
                
        # Check elements with role="button"
        if not button:
            try:
                button = _driver.find_element(By.XPATH, f"//*[@role='button' and contains(text(), '{button_identifier}')]")
            except NoSuchElementException:
                pass
                
        # As a last resort, try any element containing this text that looks clickable
        if not button:
            try:
                button = _driver.find_element(By.XPATH, f"//*[contains(text(), '{button_identifier}') and (@onclick or @class='btn' or @class contains 'button')]")
            except NoSuchElementException:
                pass
                
        # If button found, click it
        if button:
            button.click()
            time.sleep(1)  # Wait for any action to complete
            
            # Switch back to main document
            _driver.switch_to.default_content()
            
            return {
                "status": "success",
                "message": f"Successfully clicked button: {button_identifier}"
            }
        else:
            # Switch back to main document
            _driver.switch_to.default_content()
            
            return {
                "status": "error",
                "message": f"Button not found: {button_identifier}"
            }
    except Exception as e:
        # Make sure we return to the main document
        try:
            _driver.switch_to.default_content()
        except:
            pass
            
        return {
            "status": "error",
            "message": f"Error clicking button: {str(e)}"
        }

def fill_input_in_iframe(input_identifier, value):
    \"\"\"
    Function tool: Fill an input field in the current iframe
    
    Args:
        input_identifier (str): Label, placeholder, or selector of the input
        value (str): Value to input
        
    Returns:
        dict: Result of the operation
    \"\"\"
    try:
        global _driver, _current_iframe
        
        if not _driver:
            initialize_driver()
            
        if not _current_iframe:
            return {
                "status": "error",
                "message": "No iframe is currently open. Please navigate to a menu item first."
            }
        
        # Switch to the iframe
        iframes = _driver.find_elements(By.TAG_NAME, "iframe")
        if not iframes:
            return {
                "status": "error",
                "message": "No iframes found on the page"
            }
        
        # Find the visible iframe
        visible_iframes = [frame for frame in iframes if frame.is_displayed()]
        if not visible_iframes:
            return {
                "status": "error",
                "message": "No visible iframes found"
            }
            
        # Switch to the iframe
        _driver.switch_to.frame(visible_iframes[0])
        
        # Try to find the input field
        input_field = None
        
        # First try CSS selector
        try:
            input_field = _driver.find_element(By.CSS_SELECTOR, input_identifier)
        except NoSuchElementException:
            pass
            
        # Try finding by id
        if not input_field:
            try:
                input_field = _driver.find_element(By.ID, input_identifier)
            except NoSuchElementException:
                pass
                
        # Try finding by name
        if not input_field:
            try:
                input_field = _driver.find_element(By.NAME, input_identifier)
            except NoSuchElementException:
                pass
                
        # Try finding by placeholder
        if not input_field:
            try:
                input_field = _driver.find_element(By.XPATH, f"//input[@placeholder='{input_identifier}']")
            except NoSuchElementException:
                pass
                
        # Try finding input by associated label
        if not input_field:
            try:
                label = _driver.find_element(By.XPATH, f"//label[contains(text(), '{input_identifier}')]")
                # Check if label has a 'for' attribute
                for_attr = label.get_attribute("for")
                if for_attr:
                    input_field = _driver.find_element(By.ID, for_attr)
                else:
                    # Maybe the input is inside the label
                    input_field = label.find_element(By.TAG_NAME, "input")
            except NoSuchElementException:
                pass
                
        # If input field found, fill it
        if input_field:
            input_field.clear()  # Clear existing value
            input_field.send_keys(value)
            
            # Switch back to main document
            _driver.switch_to.default_content()
            
            return {
                "status": "success",
                "message": f"Successfully filled input '{input_identifier}' with value '{value}'"
            }
        else:
            # Switch back to main document
            _driver.switch_to.default_content()
            
            return {
                "status": "error",
                "message": f"Input field not found: {input_identifier}"
            }
    except Exception as e:
        # Make sure we return to the main document
        try:
            _driver.switch_to.default_content()
        except:
            pass
            
        return {
            "status": "error",
            "message": f"Error filling input: {str(e)}"
        }

def click_link_in_iframe(link_text):
    \"\"\"
    Function tool: Click a link in the current iframe by its text
    
    Args:
        link_text (str): Text of the link to click
        
    Returns:
        dict: Result of the click operation
    \"\"\"
    try:
        global _driver, _current_iframe
        
        if not _driver:
            initialize_driver()
            
        if not _current_iframe:
            return {
                "status": "error",
                "message": "No iframe is currently open. Please navigate to a menu item first."
            }
        
        # Switch to the iframe
        iframes = _driver.find_elements(By.TAG_NAME, "iframe")
        if not iframes:
            return {
                "status": "error",
                "message": "No iframes found on the page"
            }
        
        # Find the visible iframe
        visible_iframes = [frame for frame in iframes if frame.is_displayed()]
        if not visible_iframes:
            return {
                "status": "error",
                "message": "No visible iframes found"
            }
            
        # Switch to the iframe
        _driver.switch_to.frame(visible_iframes[0])
        
        # Try to find the link
        link = None
        
        # Try finding by exact text
        try:
            link = _driver.find_element(By.LINK_TEXT, link_text)
        except NoSuchElementException:
            pass
            
        # Try finding by partial text
        if not link:
            try:
                link = _driver.find_element(By.PARTIAL_LINK_TEXT, link_text)
            except NoSuchElementException:
                pass
                
        # If link found, click it
        if link:
            link.click()
            time.sleep(1)  # Wait for any action to complete
            
            # Switch back to main document
            _driver.switch_to.default_content()
            
            return {
                "status": "success",
                "message": f"Successfully clicked link: {link_text}"
            }
        else:
            # Switch back to main document
            _driver.switch_to.default_content()
            
            return {
                "status": "error",
                "message": f"Link not found: {link_text}"
            }
    except Exception as e:
        # Make sure we return to the main document
        try:
            _driver.switch_to.default_content()
        except:
            pass
            
        return {
            "status": "error",
            "message": f"Error clicking link: {str(e)}"
        }

def search_menu_items(search_term):
    \"\"\"
    Function tool: Search for menu items containing the search term
    
    Args:
        search_term (str): Term to search for in menu item texts
        
    Returns:
        dict: Search results with matching menu paths
    \"\"\"
    try:
        # Load menu structure
        menu_structure = load_menu_structure()
        
        matches = []
        search_term = search_term.lower()
        
        # Recursive function to search menu items
        def search_items(items, current_path=[]):
            for item in items:
                item_text = item.get("text", "").lower()
                path = current_path + [item.get("text", "")]
                
                # Check if this item matches
                if search_term in item_text:
                    matches.append({
                        "path": "/".join(path),
                        "text": item.get("text", ""),
                        "level": item.get("level", 1),
                        "has_iframe": item.get("has_iframe", False)
                    })
                
                # Search children
                if "children" in item and item["children"]:
                    search_items(item["children"], path)
        
        # Start search from the root
        search_items(menu_structure)
        
        return {
            "status": "success",
            "message": f"Found {len(matches)} menu items matching '{search_term}'",
            "matches": matches
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error searching menu items: {str(e)}"
        }

# Map of function tools
function_tools = {
    "get_menu_structure": get_menu_structure,
    "navigate_to_menu": navigate_to_menu,
    "get_current_iframe_content": get_current_iframe_content,
    "click_button_in_iframe": click_button_in_iframe,
    "fill_input_in_iframe": fill_input_in_iframe,
    "click_link_in_iframe": click_link_in_iframe,
    "search_menu_items": search_menu_items
}
""")
    
    print(f"Generated function tools module: {output_file}")

# Main function to run the navigator and generate tools
def main():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Add option to connect to existing browser if needed
    chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")
    
    # Initialize Chrome driver
    try:
        driver = webdriver.Chrome(service=Service('/usr/local/bin/chromedriver'), options=chrome_options)
        print("Connected to Chrome browser")
    except Exception as e:
        print(f"Failed to initialize Chrome driver: {str(e)}")
        return
    
    try:
        # Create output directory
        output_dir = "spa_navigator_output"
        
        # Create navigator
        navigator = SPANavigator(driver, output_dir)
        
        # Extract menu structure
        navigator.extract_menu_structure()
        
        # Prompt to navigate all menu items or just save current state
        choice = input("Navigate all menu items to extract content? (y/n): ")
        if choice.lower() == 'y':
            navigator.navigate_all_menu_items()
        
        # Generate function tools
        generate_function_tools_module(navigator, os.path.join(output_dir, "spa_function_tools.py"))
        
        print(f"\nAll done! Output saved to {output_dir}")
        print("To use with your agent, import the generated spa_function_tools.py module")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close browser (optional, you might want to keep it open)
        choice = input("Close browser? (y/n): ")
        if choice.lower() == 'y':
            driver.quit()
            print("Browser closed")
        else:
            print("Browser kept open")

if __name__ == "__main__":
    main()
