from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import json
import re
from typing import Dict, List, Optional, Any, Union

# Global driver instance to be used across functions
driver = None

def initialize_driver(debugger_address="localhost:9222"):
    """
    Initialize or get the Chrome driver instance
    """
    global driver
    
    if driver is not None:
        try:
            # Check if driver is still active
            driver.title
            return driver
        except:
            # Driver is no longer active, reinitialize
            pass
    
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Add option to connect to existing browser
    chrome_options.add_experimental_option("debuggerAddress", debugger_address)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print(f"Connected to Chrome browser: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        return driver
    except Exception as e:
        print(f"Failed to initialize Chrome driver: {str(e)}")
        return None

def get_menu_structure():
    """
    Get the complete menu structure from the left sidebar
    
    Returns:
        Dict: A dictionary representing the menu structure with status and content
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Wait for the page to be fully loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Take some time to observe the page structure
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Try different strategies to find menu items
        menu_structure = {}
        
        # Strategy 1: Find menu items by left-side vertical position
        try:
            # Get all elements in the left 30% of the page with text
            width = driver.execute_script("return window.innerWidth")
            elements = driver.find_elements(By.XPATH, "//body//*[text()]")
            left_side_elements = []
            
            for element in elements:
                try:
                    if element.is_displayed():
                        location = element.location
                        if location['x'] < width * 0.3:  # Left 30% of the page
                            left_side_elements.append(element)
                except:
                    continue
            
            if left_side_elements:
                print(f"Found {len(left_side_elements)} potential menu items on the left side")
                
                # Process these as menu items
                current_level1 = None
                
                for element in left_side_elements:
                    try:
                        text = element.text.strip()
                        if not text:
                            continue
                            
                        # Check element characteristics to determine menu level
                        classes = element.get_attribute("class") or ""
                        style = element.get_attribute("style") or ""
                        parent = element.find_element(By.XPATH, "./..").get_attribute("class") or ""
                        
                        # Determine level based on indentation, classes, or parent structure
                        # This is a simplified approach - you may need to adjust based on the actual structure
                        level = 3  # Default to deepest level
                        
                        # Look for level 1 indicators (main categories)
                        if "bold" in style or "header" in classes or "title" in classes:
                            level = 1
                        elif element.tag_name == "li" and element.find_elements(By.TAG_NAME, "ul"):
                            level = 1
                        # Check if this is likely a top-level item
                        elif len(text) <= 10 and text in ["客户操作台", "我的收藏", "客户服务", "基本业务", "营销作业", "分期业务"]:
                            level = 1
                            
                        # Add to menu structure based on determined level
                        if level == 1:
                            current_level1 = text
                            menu_structure[current_level1] = {"submenus": {}}
                        elif level <= 3 and current_level1:
                            menu_structure[current_level1]["submenus"][text] = {}
                            
                        print(f"Processed menu item: {text} (Level: {level})")
                    except Exception as e:
                        print(f"Error processing element: {str(e)}")
            
        except Exception as e:
            print(f"Error in Strategy 1: {str(e)}")
        
        # Strategy 2: Find menu items directly by text content
        if not menu_structure:
            try:
                # Chinese menu item texts commonly found in CITIC Bank applications
                common_menu_items = [
                    "客户操作台", "契约客户", "我的收藏", "客户服务", "基本业务", 
                    "营销作业", "分期业务", "年度营销下单", "账单分期", "分期申请"
                ]
                
                for item_text in common_menu_items:
                    try:
                        elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{item_text}')]")
                        if elements and elements[0].is_displayed():
                            print(f"Found menu item: {item_text}")
                            
                            # If this is a top-level item
                            if item_text in ["客户操作台", "我的收藏", "客户服务", "基本业务", "营销作业", "分期业务"]:
                                menu_structure[item_text] = {"submenus": {}}
                            else:
                                # Try to determine parent based on proximity or hierarchy
                                # For simplicity, we'll assign to a default parent
                                if "分期" in item_text:
                                    parent = "分期业务"
                                elif "营销" in item_text:
                                    parent = "营销作业"
                                else:
                                    parent = "基本业务"
                                    
                                if parent in menu_structure:
                                    menu_structure[parent]["submenus"][item_text] = {}
                    except:
                        continue
            except Exception as e:
                print(f"Error in Strategy 2: {str(e)}")
        
        # If we still have no menu structure, create a basic placeholder
        if not menu_structure:
            menu_structure = {
                "客户操作台": {"submenus": {}},
                "客户服务": {"submenus": {}},
                "基本业务": {"submenus": {}},
                "分期业务": {"submenus": {
                    "分期申请": {},
                    "账单分期": {}
                }}
            }
            print("Using placeholder menu structure")
        
        return {
            "status": "success",
            "content": menu_structure
        }
    except Exception as e:
        error_msg = f"Failed to get menu structure: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def search_menu_items(keyword: str) -> Dict:
    """
    Search for menu items containing the given keyword
    
    Args:
        keyword (str): The keyword to search for
        
    Returns:
        Dict: A dictionary of matching menu items with their paths
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get the menu structure first
        menu_result = get_menu_structure()
        
        if menu_result["status"] == "error":
            # If menu structure fails, try direct search
            matches = []
            
            # Search directly for elements containing the keyword
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if keyword.lower() in text.lower():
                            matches.append({
                                "menu_name": text,
                                "path": text,
                                "full_path": [text]
                            })
            except:
                pass
                
            return {
                "status": "success",
                "content": matches
            }
            
        menu_structure = menu_result["content"]
        
        # Search for keyword in menu items
        matches = []
        
        # Helper function to search recursively
        def search_recursively(structure, current_path=[]):
            for key, value in structure.items():
                path = current_path + [key]
                
                # Check if the keyword is in the menu item name
                if keyword.lower() in key.lower():
                    matches.append({
                        "menu_name": key,
                        "path": " > ".join(path),
                        "full_path": path
                    })
                
                # Search in submenus if any
                if "submenus" in value and value["submenus"]:
                    search_recursively(value["submenus"], path)
        
        # Start the recursive search
        search_recursively(menu_structure)
        
        # If no matches found in menu structure, try direct search
        if not matches:
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if keyword.lower() in text.lower():
                            matches.append({
                                "menu_name": text,
                                "path": text,
                                "full_path": [text]
                            })
            except:
                pass
        
        return {
            "status": "success",
            "content": matches
        }
    except Exception as e:
        error_msg = f"Failed to search menu items: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def navigate_to_menu(menu_path: str) -> Dict:
    """
    Navigate to a specific menu by its path
    
    Args:
        menu_path (str): The path to the menu, separated by " > "
        
    Returns:
        Dict: Status of the navigation and content of the opened page
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Split the path into individual menu items
        parts = menu_path.split(" > ")
        
        # Find and click on each menu item in sequence
        found_all = True
        
        for part in parts:
            # Try different strategies to find the menu item
            element = None
            
            # Strategy 1: Exact text match
            try:
                xpath = f"//*[normalize-space(text())='{part}']"
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        element = el
                        break
            except:
                pass
                
            # Strategy 2: Contains text match
            if not element:
                try:
                    xpath = f"//*[contains(text(), '{part}')]"
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed() and part.lower() in el.text.lower():
                            element = el
                            break
                except:
                    pass
            
            # If found, click the element
            if element:
                try:
                    # Scroll the element into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)  # Small delay for the UI to stabilize
                    
                    # Click the element
                    element.click()
                    time.sleep(1)  # Wait for any animations or page changes
                    print(f"Clicked on menu item: {part}")
                except Exception as e:
                    print(f"Error clicking menu item {part}: {str(e)}")
                    found_all = False
                    break
            else:
                print(f"Menu item not found: {part}")
                found_all = False
                break
        
        # Get the content after navigation
        content = get_current_iframe_content()
        
        if found_all:
            return {
                "status": "success",
                "message": f"Successfully navigated to {menu_path}",
                "content": content["content"] if content["status"] == "success" else None
            }
        else:
            return {
                "status": "error",
                "message": f"Could not complete navigation to {menu_path}",
                "content": content["content"] if content["status"] == "success" else None
            }
    except Exception as e:
        error_msg = f"Failed to navigate to menu: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def get_current_iframe_content() -> Dict:
    """
    Get the content of the current iframe or main content area
    
    Returns:
        Dict: Content of the iframe including title, headings, form fields, buttons, and text
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Check if there's an iframe and switch to it
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        if iframes:
            # Try to switch to each iframe and look for content
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    # Check if we have meaningful content
                    body = driver.find_element(By.TAG_NAME, "body")
                    if body.text.strip():
                        break  # Found content, stay in this iframe
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
        
        # Wait for the content to load
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # Get page title
        try:
            title = driver.title
        except:
            title = "No title available"
        
        # Get headings
        headings = []
        for h_level in range(1, 7):
            for heading in driver.find_elements(By.TAG_NAME, f"h{h_level}"):
                if heading.is_displayed() and heading.text.strip():
                    headings.append(heading.text.strip())
        
        # If no headings found, look for elements that might serve as headings
        if not headings:
            for selector in [".title", ".header", "[class*='title']", "[class*='header']", "strong", "b"]:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        headings.append(element.text.strip())
        
        # Get form fields
        form_fields = []
        
        # Input fields
        for input_element in driver.find_elements(By.TAG_NAME, "input"):
            try:
                if input_element.is_displayed():
                    field_type = input_element.get_attribute("type")
                    field_name = input_element.get_attribute("name") or input_element.get_attribute("id") or ""
                    field_label = input_element.get_attribute("placeholder") or field_name
                    
                    # Look for associated label
                    if field_name:
                        try:
                            label_element = driver.find_element(By.XPATH, f"//label[@for='{field_name}']")
                            if label_element.text.strip():
                                field_label = label_element.text.strip()
                        except:
                            pass
                    
                    if field_type not in ["hidden", "submit", "button"]:
                        form_fields.append({
                            "type": field_type,
                            "name": field_name,
                            "label": field_label,
                            "required": input_element.get_attribute("required") is not None,
                            "disabled": input_element.get_attribute("disabled") is not None
                        })
            except:
                continue
        
        # Select elements
        for select_element in driver.find_elements(By.TAG_NAME, "select"):
            try:
                if select_element.is_displayed():
                    field_name = select_element.get_attribute("name") or select_element.get_attribute("id") or ""
                    options = [option.text for option in select_element.find_elements(By.TAG_NAME, "option")]
                    
                    # Look for associated label
                    field_label = field_name
                    if field_name:
                        try:
                            label_element = driver.find_element(By.XPATH, f"//label[@for='{field_name}']")
                            if label_element.text.strip():
                                field_label = label_element.text.strip()
                        except:
                            pass
                    
                    form_fields.append({
                        "type": "select",
                        "name": field_name,
                        "label": field_label,
                        "options": options,
                        "required": select_element.get_attribute("required") is not None,
                        "disabled": select_element.get_attribute("disabled") is not None
                    })
            except:
                continue
        
        # Textarea elements
        for textarea in driver.find_elements(By.TAG_NAME, "textarea"):
            try:
                if textarea.is_displayed():
                    field_name = textarea.get_attribute("name") or textarea.get_attribute("id") or ""
                    field_label = textarea.get_attribute("placeholder") or field_name
                    
                    # Look for associated label
                    if field_name:
                        try:
                            label_element = driver.find_element(By.XPATH, f"//label[@for='{field_name}']")
                            if label_element.text.strip():
                                field_label = label_element.text.strip()
                        except:
                            pass
                    
                    form_fields.append({
                        "type": "textarea",
                        "name": field_name,
                        "label": field_label,
                        "required": textarea.get_attribute("required") is not None,
                        "disabled": textarea.get_attribute("disabled") is not None
                    })
            except:
                continue
        
        # Get buttons
        buttons = []
        for button in driver.find_elements(By.TAG_NAME, "button"):
            try:
                if button.is_displayed() and button.text.strip():
                    buttons.append(button.text.strip())
            except:
                continue
        
        # Also look for input buttons
        for input_button in driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit']"):
            try:
                if input_button.is_displayed():
                    button_text = input_button.get_attribute("value")
                    if button_text and button_text.strip():
                        buttons.append(button_text.strip())
            except:
                continue
        
        # Also look for elements that might function as buttons
        for button_like in driver.find_elements(By.CSS_SELECTOR, "[class*='btn'], [class*='button'], .submit, .cancel"):
            try:
                if button_like.is_displayed() and button_like.text.strip() and button_like.text.strip() not in buttons:
                    buttons.append(button_like.text.strip())
            except:
                continue
        
        # Get links
        links = []
        for link in driver.find_elements(By.TAG_NAME, "a"):
            try:
                if link.is_displayed() and link.text.strip():
                    links.append(link.text.strip())
            except:
                continue
        
        # Get the main text content
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
        except:
            body_text = ""
        
        # Create a summary of the text (first few sentences)
        text_parts = re.split(r'[.!?]\s+', body_text)
        summary = ' '.join(text_parts[:3]) + ('...' if len(text_parts) > 3 else '')
        
        # Extract tables if any
        tables = []
        for table in driver.find_elements(By.TAG_NAME, "table"):
            try:
                if table.is_displayed():
                    table_data = []
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for row in rows:
                        row_data = []
                        cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                        
                        for cell in cells:
                            row_data.append(cell.text.strip())
                        
                        if row_data:
                            table_data.append(row_data)
                    
                    if table_data:
                        tables.append(table_data)
            except:
                continue
        
        # Switch back to default content if we were in an iframe
        if iframes:
            driver.switch_to.default_content()
        
        # Create content object
        content = {
            "title": title,
            "headings": headings,
            "form_fields": form_fields,
            "buttons": buttons,
            "links": links,
            "summary": summary,
            "full_text": body_text,
            "tables": tables
        }
        
        return {
            "status": "success",
            "content": content
        }
    except Exception as e:
        # Make sure to switch back to default content in case of error
        try:
            driver.switch_to.default_content()
        except:
            pass
            
        error_msg = f"Failed to get iframe content: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def click_button_in_iframe(button_text: str) -> Dict:
    """
    Click a button in the current iframe or main content
    
    Args:
        button_text (str): The text of the button to click
        
    Returns:
        Dict: Status of the button click operation
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Check if there's an iframe and switch to it
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        if iframes:
            # Try to switch to each iframe and look for the button
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    # Try to find the button
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{button_text}')]")
                    if any(e.is_displayed() for e in elements):
                        break  # Found elements, stay in this iframe
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
        
        # Try different strategies to find the button
        button_found = False
        
        # Strategy 1: Exact button text match
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[normalize-space(text())='{button_text}']"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            button.click()
            button_found = True
            print(f"Clicked button using strategy 1: {button_text}")
        except:
            pass
        
        # Strategy 2: Partial button text match
        if not button_found:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(),'{button_text}')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                button.click()
                button_found = True
                print(f"Clicked button using strategy 2: {button_text}")
            except:
                pass
        
        # Strategy 3: Input button with value
        if not button_found:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//input[@type='button' or @type='submit'][@value='{button_text}']"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                button.click()
                button_found = True
                print(f"Clicked button using strategy 3: {button_text}")
            except:
                pass
        
        # Strategy 4: Input button with partial value match
        if not button_found:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//input[@type='button' or @type='submit'][contains(@value,'{button_text}')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                button.click()
                button_found = True
                print(f"Clicked button using strategy 4: {button_text}")
            except:
                pass
        
        # Strategy 5: Any element with the button text that looks like a button
        if not button_found:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//*[contains(@class, 'btn') or contains(@class, 'button')][contains(text(),'{button_text}')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                button.click()
                button_found = True
                print(f"Clicked button using strategy 5: {button_text}")
            except:
                pass
        
        # Strategy 6: Desperate attempt - any clickable element with the text
        if not button_found:
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(),'{button_text}')]")
                for element in elements:
                    try:
                        if element.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            element.click()
                            button_found = True
                            print(f"Clicked element using strategy 6: {button_text}")
                            break
                    except:
                        continue
            except:
                pass
        
        # Switch back to default content
        if iframes:
            driver.switch_to.default_content()
        
        if not button_found:
            return {
                "status": "error",
                "message": f"Could not find or click button with text: {button_text}"
            }
        
        # Wait for any page changes after clicking
        time.sleep(2)
        
        # Get updated content
        content = get_current_iframe_content()
        
        return {
            "status": "success",
            "message": f"Successfully clicked button: {button_text}",
            "content": content["content"] if content["status"] == "success" else None
        }
    except Exception as e:
        # Make sure to switch back to default content in case of error
        try:
            driver.switch_to.default_content()
        except:
            pass
            
        error_msg = f"Failed to click button: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def fill_input_in_iframe(field_name: str, value: str) -> Dict:
    """
    Fill an input field in the current iframe or main content
    
    Args:
        field_name (str): The name, id, or label of the field to fill
        value (str): The value to set in the field
        
    Returns:
        Dict: Status of the field fill operation
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Check if there's an iframe and switch to it
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        if iframes:
            # Try to switch to each iframe and look for the field
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    # Try to find the field
                    by_name = driver.find_elements(By.NAME, field_name)
                    by_id = driver.find_elements(By.ID, field_name)
                    by_placeholder = driver.find_elements(By.XPATH, f"//input[@placeholder='{field_name}']")
                    by_label = driver.find_elements(By.XPATH, f"//label[contains(text(),'{field_name}')]")
                    
                    if any(by_name) or any(by_id) or any(by_placeholder) or any(by_label):
                        break  # Found elements, stay in this iframe
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
        
        # Try different strategies to find the input field
        field_found = False
        
        # Strategy 1: By name attribute
        try:
            input_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, field_name))
            )
            if input_field.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                # Clear the field first
                input_field.clear()
                input_field.send_keys(value)
                field_found = True
                print(f"Filled field using strategy 1: {field_name} = {value}")
        except:
            pass
        
        # Strategy 2: By id attribute
        if not field_found:
            try:
                input_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, field_name))
                )
                if input_field.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                    input_field.clear()
                    input_field.send_keys(value)
                    field_found = True
                    print(f"Filled field using strategy 2: {field_name} = {value}")
            except:
                pass
        
        # Strategy 3: By placeholder attribute
        if not field_found:
            try:
                input_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{field_name}']"))
                )
                if input_field.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                    input_field.clear()
                    input_field.send_keys(value)
                    field_found = True
                    print(f"Filled field using strategy 3: {field_name} = {value}")
            except:
                pass
        
        # Strategy 4: By label text
        if not field_found:
            try:
                # Find label element with matching text
                label = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//label[contains(text(),'{field_name}')]"))
                )
                
                # Get the 'for' attribute to find the corresponding input
                for_attribute = label.get_attribute("for")
                
                if for_attribute:
                    input_field = driver.find_element(By.ID, for_attribute)
                    if input_field.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                        input_field.clear()
                        input_field.send_keys(value)
                        field_found = True
                        print(f"Filled field using strategy 4a: {field_name} = {value}")
                else:
                    # Try to find input within the label
                    input_field = label.find_element(By.TAG_NAME, "input")
                    if input_field.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                        input_field.clear()
                        input_field.send_keys(value)
                        field_found = True
                        print(f"Filled field using strategy 4b: {field_name} = {value}")
            except:
                pass
        
        # Strategy 5: Try to find an input near text that matches the field name
        if not field_found:
            try:
                # Find an element that contains the field name text
                text_element = driver.find_element(By.XPATH, f"//*[contains(text(), '{field_name}')]")
                if text_element:
                    # Look for nearby inputs
                    parent = text_element.find_element(By.XPATH, "./..")
                    inputs = parent.find_elements(By.TAG_NAME, "input") + parent.find_elements(By.TAG_NAME, "select") + parent.find_elements(By.TAG_NAME, "textarea")
                    
                    if inputs:
                        input_field = inputs[0]  # Take the first input found
                        if input_field.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                            input_field.clear()
                            input_field.send_keys(value)
                            field_found = True
                            print(f"Filled field using strategy 5: {field_name} = {value}")
            except:
                pass
        
        # Strategy 6: Try to find select element (dropdown) instead of input
        if not field_found:
            try:
                from selenium.webdriver.support.ui import Select
                
                # Try by name
                select_elem = Select(driver.find_element(By.NAME, field_name))
                if driver.find_element(By.NAME, field_name).is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", driver.find_element(By.NAME, field_name))
                    select_elem.select_by_visible_text(value)
                    field_found = True
                    print(f"Filled dropdown using strategy 6a: {field_name} = {value}")
            except:
                pass
        
        # Strategy 7: Try by ID for select
        if not field_found:
            try:
                from selenium.webdriver.support.ui import Select
                
                select_elem = Select(driver.find_element(By.ID, field_name))
                if driver.find_element(By.ID, field_name).is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", driver.find_element(By.ID, field_name))
                    select_elem.select_by_visible_text(value)
                    field_found = True
                    print(f"Filled dropdown using strategy 6b: {field_name} = {value}")
            except:
                pass
        
        # Switch back to default content
        if iframes:
            driver.switch_to.default_content()
        
        if not field_found:
            return {
                "status": "error",
                "message": f"Could not find or fill input field: {field_name}"
            }
        
        return {
            "status": "success",
            "message": f"Successfully filled field {field_name} with value: {value}"
        }
    except Exception as e:
        # Make sure to switch back to default content in case of error
        try:
            driver.switch_to.default_content()
        except:
            pass
            
        error_msg = f"Failed to fill input field: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def click_link_in_iframe(link_text: str) -> Dict:
    """
    Click a link in the current iframe or main content
    
    Args:
        link_text (str): The text of the link to click
        
    Returns:
        Dict: Status of the link click operation
    """
    try:
        driver = initialize_driver()
        if not driver:
            return {"status": "error", "message": "Failed to initialize driver"}
        
        # Check if there's an iframe and switch to it
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        if iframes:
            # Try to switch to each iframe and look for the link
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    # Try to find the link
                    by_link = driver.find_elements(By.LINK_TEXT, link_text)
                    by_partial = driver.find_elements(By.PARTIAL_LINK_TEXT, link_text)
                    
                    if any(by_link) or any(by_partial):
                        break  # Found elements, stay in this iframe
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
        
        # Try different strategies to find the link
        link_found = False
        
        # Strategy 1: Exact link text match
        try:
            link = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.LINK_TEXT, link_text))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", link)
            link.click()
            link_found = True
            print(f"Clicked link using strategy 1: {link_text}")
        except:
            pass
        
        # Strategy 2: Partial link text match
        if not link_found:
            try:
                link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, link_text))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", link)
                link.click()
                link_found = True
                print(f"Clicked link using strategy 2: {link_text}")
            except:
                pass
        
        # Strategy 3: Any anchor element with the text
        if not link_found:
            try:
                link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(),'{link_text}')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", link)
                link.click()
                link_found = True
                print(f"Clicked link using strategy 3: {link_text}")
            except:
                pass
        
        # Strategy 4: Any element that looks like a link with the text
        if not link_found:
            try:
                link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//*[contains(@class, 'link') and contains(text(),'{link_text}')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", link)
                link.click()
                link_found = True
                print(f"Clicked link using strategy 4: {link_text}")
            except:
                pass
        
        # Strategy 5: Desperate attempt - any element with the text that might be clickable
        if not link_found:
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(),'{link_text}')]")
                for element in elements:
                    try:
                        if element.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            element.click()
                            link_found = True
                            print(f"Clicked element using strategy 5: {link_text}")
                            break
                    except:
                        continue
            except:
                pass
        
        # Switch back to default content
        if iframes:
            driver.switch_to.default_content()
        
        if not link_found:
            return {
                "status": "error",
                "message": f"Could not find or click link with text: {link_text}"
            }
        
        # Wait for any page changes after clicking
        time.sleep(2)
        
        # Get updated content
        content = get_current_iframe_content()
        
        return {
            "status": "success",
            "message": f"Successfully clicked link: {link_text}",
            "content": content["content"] if content["status"] == "success" else None
        }
    except Exception as e:
        # Make sure to switch back to default content in case of error
        try:
            driver.switch_to.default_content()
        except:
            pass
            
        error_msg = f"Failed to click link: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def query_customer_info(customer_id: str) -> Dict:
    """
    Query customer information by ID
    
    Args:
        customer_id (str): The customer ID to query
        
    Returns:
        Dict: Customer information
    """
    try:
        # This is a placeholder function that would be implemented with real API calls
        # For now, we'll return mock data based on the ID
        
        # Mock customer data
        if customer_id == "1234567890":
            customer_data = {
                "id": "1234567890",
                "name": "张三",
                "card_number": "6229180073234598",
                "available_credit": 50000,
                "total_credit_limit": 80000,
                "card_status": "正常",
                "level": "金卡"
            }
        else:
            customer_data = {
                "id": customer_id,
                "name": f"用户{customer_id[-4:]}",
                "card_number": f"6229{customer_id[-4:]}XXXX4598",
                "available_credit": 30000,
                "total_credit_limit": 50000,
                "card_status": "正常",
                "level": "普卡"
            }
        
        return {
            "status": "success",
            "content": customer_data
        }
    except Exception as e:
        error_msg = f"Failed to query customer info: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def query_installment_offers(customer_id: str) -> Dict:
    """
    Query available installment offers for a customer
    
    Args:
        customer_id (str): The customer ID to query
        
    Returns:
        Dict: Available installment offers
    """
    try:
        # This is a placeholder function that would be implemented with real API calls
        # For now, we'll return mock data
        
        # Mock offers data
        offers = [
            {
                "type": "消费分期",
                "periods": [3, 6, 12, 24],
                "rates": {
                    "3": 1.5,
                    "6": 3.0,
                    "12": 6.0,
                    "24": 12.0
                },
                "min_amount": 100,
                "max_amount": 50000,
                "description": "将已出账单分期还款"
            },
            {
                "type": "账单分期",
                "periods": [3, 6, 12],
                "rates": {
                    "3": 1.2,
                    "6": 2.4,
                    "12": 5.0
                },
                "min_amount": 500,
                "max_amount": 30000,
                "description": "将已出账单金额分期偿还"
            },
            {
                "type": "现金分期",
                "periods": [12, 24, 36],
                "rates": {
                    "12": 6.5,
                    "24": 12.5,
                    "36": 18.0
                },
                "min_amount": 1000,
                "max_amount": 20000,
                "description": "将信用卡额度转为现金"
            }
        ]
        
        return {
            "status": "success",
            "content": offers
        }
    except Exception as e:
        error_msg = f"Failed to query installment offers: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def calculate_installment_plan(amount: float, periods: int, rate: float = None) -> Dict:
    """
    Calculate installment plan details
    
    Args:
        amount (float): The amount to be paid in installments
        periods (int): The number of periods
        rate (float, optional): The interest rate. If not provided, standard rates will be used.
        
    Returns:
        Dict: Installment plan details
    """
    try:
        # Use standard rates if not provided
        if rate is None:
            if periods == 3:
                rate = 1.5
            elif periods == 6:
                rate = 3.0
            elif periods == 12:
                rate = 6.0
            elif periods == 24:
                rate = 12.0
            else:
                rate = periods * 0.5  # Simple estimate
        
        # Calculate fee
        fee_amount = amount * (rate / 100)
        
        # Calculate monthly payment (principal only)
        monthly_principal = amount / periods
        
        # Calculate total amount
        total_amount = amount + fee_amount
        
        # Calculate monthly payment with fee distributed
        monthly_payment = total_amount / periods
        
        # Create payment schedule
        payment_schedule = []
        remaining = amount
        
        for i in range(1, periods + 1):
            remaining -= monthly_principal
            payment_schedule.append({
                "period": i,
                "payment": round(monthly_payment, 2),
                "principal": round(monthly_principal, 2),
                "fee": round(fee_amount / periods, 2),
                "remaining": round(remaining, 2) if remaining > 0 else 0
            })
        
        plan_details = {
            "amount": amount,
            "periods": periods,
            "rate": rate,
            "fee_amount": round(fee_amount, 2),
            "total_amount": round(total_amount, 2),
            "monthly_payment": round(monthly_payment, 2),
            "payment_schedule": payment_schedule
        }
        
        return {
            "status": "success",
            "content": plan_details
        }
    except Exception as e:
        error_msg = f"Failed to calculate installment plan: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}
# The rest of the functions (query_customer_info, query_installment_offers, calculate_installment_plan)
# can remain the same as they are mock implementations and don't interact with the actual browser

# Dictionary of all tools for easy import into the agent system
function_tools = {
    "get_menu_structure": get_menu_structure,
    "search_menu_items": search_menu_items,
    "navigate_to_menu": navigate_to_menu,
    "get_current_iframe_content": get_current_iframe_content,
    "click_button_in_iframe": click_button_in_iframe,
    "fill_input_in_iframe": fill_input_in_iframe,
    "click_link_in_iframe": click_link_in_iframe,
    "query_customer_info": query_customer_info,
    "query_installment_offers": query_installment_offers,
    "calculate_installment_plan": calculate_installment_plan
}
