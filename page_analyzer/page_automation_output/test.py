import asyncio
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
            print(f"\nPage structure analysis is available in '{structure_file}'")
            
        # Demo of how to use automation class methods
        print("\nAvailable automation methods:")
        
        # Get all click_ and fill_ methods from PageAutomation
        automation_methods = [method for method in dir(page) 
                             if callable(getattr(page, method)) and 
                             (method.startswith('click_') or method.startswith('fill_'))]
        
        for method in automation_methods:
            print(f"  - {method}")
        
        # Let user choose method to execute
        while True:
            print("\nSelect operation:")
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
                        
                        print(f"\nFound {len(elements)} elements in {elements_file}")
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
