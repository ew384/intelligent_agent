from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json
import os

def get_all_clickable_elements(url):
    # 设置Chrome选项
    chrome_options = Options()
    # 如果需要无头模式，取消下面这行的注释
    # chrome_options.add_argument("--headless")
    
    # 初始化WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    
    # 给页面足够时间加载
    time.sleep(3)  
    
    # 执行JavaScript获取所有可点击元素信息
    clickables = driver.execute_script("""
        // 获取所有可点击元素
        var clickableElements = [];
        
        // 通用可点击元素选择器
        var selectors = [
            'a', 'button', 'input[type="button"]', 'input[type="submit"]',
            '[onclick]', '[role="button"]', '.btn', '.button',
            'select', 'label', 'summary', '[tabindex]',
            '[data-toggle]', '[data-target]', '[data-click]'
        ];
        
        // 合并所有可点击元素
        var elements = document.querySelectorAll(selectors.join(','));
        
        // 处理每个元素并提取信息
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            
            // 检查元素是否可见和可点击
            if (el.offsetParent !== null) {
                var rect = el.getBoundingClientRect();
                
                // 忽略过小的元素(可能是隐藏的)
                if (rect.width < 2 || rect.height < 2) continue;
                
                // 创建元素描述
                var elInfo = {
                    index: i,
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    classes: Array.from(el.classList).join(' '),
                    text: (el.textContent || '').trim().substring(0, 50),
                    href: el.href || '',
                    position: {
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2)
                    },
                    size: {
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    visible: true,
                    xpath: getElementXPath(el)
                };
                
                clickableElements.push(elInfo);
            }
        }
        
        // 创建XPath函数
        function getElementXPath(element) {
            if (element && element.id)
                return '//*[@id="' + element.id + '"]';
                
            var paths = [];
            
            // 使用轴方法而不是递归
            for (; element && element.nodeType == 1; element = element.parentNode) {
                var index = 0;
                for (var sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
                    if (sibling.nodeType == Node.DOCUMENT_TYPE_NODE)
                        continue;
                    if (sibling.nodeName == element.nodeName)
                        ++index;
                }
                
                var tagName = element.nodeName.toLowerCase();
                var pathIndex = (index ? "[" + (index+1) + "]" : "");
                paths.splice(0, 0, tagName + pathIndex);
            }
            
            return paths.length ? "/" + paths.join("/") : null;
        }
        
        return clickableElements;
    """)
    
    # 截图作为参考
    screenshot_path = "page_screenshot.png"
    driver.save_screenshot(screenshot_path)
    
    # 关闭浏览器
    driver.quit()
    
    return clickables, screenshot_path

def sort_elements(elements, sort_by='index'):
    """根据指定的属性对元素进行排序"""
    valid_sort_keys = ['index', 'tag', 'id', 'position_x', 'position_y', 'size_width', 'size_height']
    
    if sort_by not in valid_sort_keys:
        print(f"无效的排序键: {sort_by}. 使用默认值 'index'")
        sort_by = 'index'
    
    # 定义排序函数
    if sort_by == 'position_x':
        elements.sort(key=lambda e: e['position']['x'])
    elif sort_by == 'position_y':
        elements.sort(key=lambda e: e['position']['y'])
    elif sort_by == 'size_width':
        elements.sort(key=lambda e: e['size']['width'])
    elif sort_by == 'size_height':
        elements.sort(key=lambda e: e['size']['height'])
    else:
        elements.sort(key=lambda e: e[sort_by])
    
    return elements

def highlight_elements(url, elements):
    """创建一个带有高亮元素的HTML页面"""
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)
    
    # 为每个元素添加高亮和标记
    for i, elem in enumerate(elements):
        driver.execute_script("""
            // 通过XPath找到元素
            var xpath = arguments[0];
            var index = arguments[1];
            
            // 评估XPath
            var element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            
            if (element) {
                // 保存原始样式
                var originalStyle = element.getAttribute('style') || '';
                
                // 添加高亮样式
                element.setAttribute('style', originalStyle + 
                    '; border: 2px solid red; position: relative;');
                
                // 添加索引标签
                var indexLabel = document.createElement('div');
                indexLabel.textContent = index;
                indexLabel.style = 'position: absolute; top: 0; left: 0; background: red; ' +
                    'color: white; padding: 2px 5px; font-size: 12px; z-index: 10000;';
                element.appendChild(indexLabel);
            }
        """, elem['xpath'], i)
    
    # 保存结果页面的截图
    screenshot_path = "highlighted_elements.png"
    driver.save_screenshot(screenshot_path)
    
    # 关闭浏览器
    driver.quit()
    
    return screenshot_path

def save_elements_to_file(elements, filename="clickable_elements.json"):
    """将元素数据保存到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(elements, f, indent=2, ensure_ascii=False)
    print(f"元素数据已保存到 {filename}")

def create_html_report(elements, screenshot_path):
    """创建可视化HTML报告"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>可点击元素报告</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { display: flex; }
            .elements-list { width: 50%; padding: 10px; overflow: auto; height: 90vh; }
            .preview { width: 50%; position: relative; }
            .preview img { width: 100%; border: 1px solid #ccc; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
        </style>
    </head>
    <body>
        <h1>页面可点击元素分析</h1>
        <div class="container">
            <div class="elements-list">
                <table>
                    <tr>
                        <th>索引</th>
                        <th>标签</th>
                        <th>ID</th>
                        <th>文本</th>
                        <th>位置(X,Y)</th>
                        <th>大小(W×H)</th>
                    </tr>
    """
    
    for elem in elements:
        html_content += f"""
                    <tr>
                        <td>{elem['index']}</td>
                        <td>{elem['tag']}</td>
                        <td>{elem['id']}</td>
                        <td>{elem['text']}</td>
                        <td>{elem['position']['x']},{elem['position']['y']}</td>
                        <td>{elem['size']['width']}×{elem['size']['height']}</td>
                    </tr>
        """
    
    html_content += f"""
                </table>
            </div>
            <div class="preview">
                <img src="{os.path.basename(screenshot_path)}" alt="页面截图" />
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("clickable_elements_report.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("HTML报告已创建: clickable_elements_report.html")

def main():
    url = input("请输入要分析的网页URL: ")
    print(f"正在分析 {url}...")
    
    # 获取所有可点击元素
    elements, screenshot_path = get_all_clickable_elements(url)
    
    print(f"找到 {len(elements)} 个可点击元素")
    
    # 排序选项
    print("\n排序选项:")
    print("1. 索引 (默认)")
    print("2. 标签名")
    print("3. ID")
    print("4. X坐标")
    print("5. Y坐标")
    print("6. 宽度")
    print("7. 高度")
    
    sort_choice = input("请选择排序方式 (1-7): ") or "1"
    
    sort_options = {
        "1": "index",
        "2": "tag",
        "3": "id",
        "4": "position_x",
        "5": "position_y",
        "6": "size_width",
        "7": "size_height"
    }
    
    sort_by = sort_options.get(sort_choice, "index")
    elements = sort_elements(elements, sort_by)
    
    # 保存元素数据
    save_elements_to_file(elements)
    
    # 创建可视化报告
    create_html_report(elements, screenshot_path)
    
    # 是否需要高亮元素
    highlight_choice = input("是否创建带高亮元素的页面截图? (y/n): ").lower()
    if highlight_choice == 'y':
        highlighted_path = highlight_elements(url, elements)
        print(f"已创建高亮截图: {highlighted_path}")
    
    print("\n分析完成!")

if __name__ == "__main__":
    main()
