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
from bs4 import BeautifulSoup
def extract_spa_content(driver, output_dir):
    """
    提取单页应用中的内容，包括处理内部标签页
    按照标签页名称组织内容到单独的子目录
    """
    import os
    import time
    import json
    import re
    from selenium.webdriver.common.by import By
    
    # 创建一个目录来存储所有标签页内容
    tabs_dir = os.path.join(output_dir, "tabs_content")
    if not os.path.exists(tabs_dir):
        os.makedirs(tabs_dir)
    
    # 创建索引文件来总结所有标签页
    tabs_index = []
    
    # 记录初始状态
    print("提取主页面内容...")
    content_file = os.path.join(output_dir, "main_content.txt")
    extract_page_content(driver, content_file)
    
    # 保存当前URL和页面标题
    current_url = driver.current_url
    page_title = driver.title
    
    # 创建一个主信息JSON文件
    main_info = {
        "url": current_url,
        "title": page_title,
        "tabs": []
    }
    
    # 尝试找出所有可能的标签页/导航元素
    print("查找可能的标签页或导航元素...")
    potential_tabs = []
    
    # 标签页元素的常见模式
    tab_patterns = [
        # 标准标签导航
        "//ul[contains(@class, 'nav') or contains(@class, 'tab')]//li",
        "//div[contains(@class, 'tab') or contains(@class, 'tabs')]//a",
        "//div[contains(@class, 'tab') or contains(@class, 'tabs')]//button",
        "//div[contains(@role, 'tablist')]//button",
        "//div[contains(@role, 'tablist')]//div[contains(@role, 'tab')]",
        
        # Material UI 和其他UI框架
        "//div[contains(@class, 'MuiTabs')]//button",
        "//div[contains(@class, 'ant-tabs')]//div[contains(@class, 'ant-tabs-tab')]",
        
        # 常规导航元素
        "//nav//a[not(contains(@href, 'http'))]",  # 非外部链接
        "//div[contains(@class, 'menu') or contains(@class, 'navigation')]//a[not(contains(@href, 'http'))]",
        
        # 基于ARIA角色的元素
        "//*[@role='tab']",
        "//*[@role='menuitem']"
    ]
    
    # 提取可能的标签页元素
    for pattern in tab_patterns:
        try:
            elements = driver.find_elements(By.XPATH, pattern)
            for element in elements:
                # 只考虑可见且有文本内容的元素
                if element.is_displayed() and element.text.strip():
                    # 检查此元素是否已添加（基于文本）
                    text = element.text.strip()
                    if not any(tab["text"] == text for tab in potential_tabs):
                        potential_tabs.append({
                            "element": element,
                            "text": text,
                            "tag": element.tag_name,
                            "is_active": "active" in element.get_attribute("class") if element.get_attribute("class") else False,
                            "href": element.get_attribute("href") if element.tag_name == "a" else None
                        })
        except Exception as e:
            print(f"查找模式 {pattern} 时出错: {str(e)}")
            continue
    
    print(f"找到 {len(potential_tabs)} 个可能的标签页/导航元素")
    
    # 创建一个函数来清理文件名
    def clean_filename(name):
        """将文本转换为有效的文件名"""
        # 移除非法字符
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        # 替换空格
        name = name.replace(" ", "_")
        # 限制长度
        if len(name) > 50:
            name = name[:50]
        return name
    
    # 遍历点击每个潜在的标签页元素
    for i, tab in enumerate(potential_tabs):
        tab_clean_name = clean_filename(tab["text"])
        
        # 为每个标签页创建单独的目录
        tab_dir = os.path.join(tabs_dir, f"{i+1}_{tab_clean_name}")
        if not os.path.exists(tab_dir):
            os.makedirs(tab_dir)
        
        # 标签页信息
        tab_info = {
            "index": i + 1,
            "name": tab["text"],
            "tag": tab["tag"],
            "was_active": tab["is_active"],
            "content_extracted": False,
            "files": []
        }
        
        try:
            print(f"\n[{i+1}/{len(potential_tabs)}] 尝试点击: {tab['text']} ({tab['tag']})")
            
            # 保存点击前的截图
            pre_screenshot = os.path.join(tab_dir, "before_click.png")
            driver.save_screenshot(pre_screenshot)
            tab_info["files"].append({"type": "screenshot", "name": "before_click.png", "description": "点击前状态"})
            
            # 滚动到元素位置
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab["element"])
            time.sleep(1)  # 等待滚动完成
            
            # 记录点击前的DOM状态和URL
            pre_click_html = driver.page_source
            pre_click_url = driver.current_url
            
            # 点击元素
            tab["element"].click()
            
            # 等待内容变化 - 对于复杂应用可能需要更长时间
            time.sleep(3)
            
            # 保存点击后的截图
            post_screenshot = os.path.join(tab_dir, "after_click.png")
            driver.save_screenshot(post_screenshot)
            tab_info["files"].append({"type": "screenshot", "name": "after_click.png", "description": "点击后状态"})
            
            # 检查DOM是否有变化或URL是否改变
            post_click_html = driver.page_source
            post_click_url = driver.current_url
            content_changed = post_click_html != pre_click_html
            url_changed = post_click_url != pre_click_url
            
            if content_changed or url_changed:
                print(f"检测到变化:" + 
                      f" {'DOM已更新' if content_changed else ''}" +
                      f" {'URL已改变' if url_changed else ''}")
                
                # 标记内容已提取
                tab_info["content_extracted"] = True
                
                # 如果URL改变了，记录新URL
                if url_changed:
                    tab_info["new_url"] = post_click_url
                
                # 获取当前标签页标题
                current_tab_title = driver.title
                tab_info["title"] = current_tab_title
                
                # 提取标签页内容
                content_file = os.path.join(tab_dir, "content.txt")
                with open(content_file, "w", encoding="utf-8") as f:
                    f.write(f"标签页: {tab['text']}\n")
                    f.write(f"标题: {current_tab_title}\n")
                    if url_changed:
                        f.write(f"URL: {post_click_url}\n")
                    f.write("\n" + "="*80 + "\n\n")
                    
                    # 获取页面中所有可见文本
                    js_get_text = """
                    function getAllVisibleText() {
                        const result = {
                            headings: [],
                            paragraphs: [],
                            listItems: [],
                            otherText: []
                        };
                        
                        // 获取标题
                        document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => {
                            if (isVisible(el) && el.textContent.trim()) {
                                result.headings.push({
                                    level: parseInt(el.tagName.substring(1)),
                                    text: el.textContent.trim()
                                });
                            }
                        });
                        
                        // 获取段落
                        document.querySelectorAll('p').forEach(el => {
                            if (isVisible(el) && el.textContent.trim()) {
                                result.paragraphs.push(el.textContent.trim());
                            }
                        });
                        
                        // 获取列表项
                        document.querySelectorAll('li').forEach(el => {
                            if (isVisible(el) && el.textContent.trim()) {
                                result.listItems.push(el.textContent.trim());
                            }
                        });
                        
                        // 获取其他可见文本块
                        const textBlocks = [];
                        const walker = document.createTreeWalker(
                            document.body, 
                            NodeFilter.SHOW_TEXT,
                            { acceptNode: function(node) {
                                if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
                                if (!isVisible(node.parentElement)) return NodeFilter.FILTER_REJECT;
                                return NodeFilter.FILTER_ACCEPT;
                            }}
                        );
                        
                        let node;
                        while (node = walker.nextNode()) {
                            const text = node.textContent.trim();
                            if (text && !isInCollection(text, result)) {
                                result.otherText.push(text);
                            }
                        }
                        
                        // 检查元素是否可见
                        function isVisible(el) {
                            if (!el) return false;
                            
                            const style = window.getComputedStyle(el);
                            return style.display !== 'none' && 
                                   style.visibility !== 'hidden' && 
                                   parseFloat(style.opacity) > 0 &&
                                   el.offsetWidth > 0 && 
                                   el.offsetHeight > 0;
                        }
                        
                        // 检查文本是否已经在集合中
                        function isInCollection(text, collection) {
                            return collection.headings.some(h => h.text.includes(text)) ||
                                   collection.paragraphs.some(p => p.includes(text)) ||
                                   collection.listItems.some(li => li.includes(text));
                        }
                        
                        return result;
                    }
                    return getAllVisibleText();
                    """
                    
                    text_content = driver.execute_script(js_get_text)
                    
                    # 写入标题
                    if text_content["headings"]:
                        f.write("标题:\n")
                        for heading in sorted(text_content["headings"], key=lambda h: h["level"]):
                            f.write("  " * (heading["level"]-1) + heading["text"] + "\n")
                        f.write("\n")
                    
                    # 写入段落
                    if text_content["paragraphs"]:
                        f.write("段落:\n")
                        for para in text_content["paragraphs"]:
                            f.write(para + "\n\n")
                    
                    # 写入列表项
                    if text_content["listItems"]:
                        f.write("列表项:\n")
                        for item in text_content["listItems"]:
                            f.write("- " + item + "\n")
                        f.write("\n")
                    
                    # 写入其他文本
                    if text_content["otherText"]:
                        f.write("其他文本:\n")
                        for text in text_content["otherText"]:
                            f.write(text + "\n")
                
                tab_info["files"].append({"type": "text", "name": "content.txt", "description": "文本内容"})
                
                # 提取HTML内容
                html_file = os.path.join(tab_dir, "content.html")
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(post_click_html)
                tab_info["files"].append({"type": "html", "name": "content.html", "description": "HTML内容"})
                
                # 使用BeautifulSoup来提取更详细的结构化内容
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(post_click_html, 'html.parser')
                    
                    # 提取并保存为JSON
                    structured_data = {
                        "title": current_tab_title,
                        "headings": [],
                        "paragraphs": [],
                        "lists": [],
                        "tables": [],
                        "forms": [],
                        "links": [],
                    }
                    
                    # 提取标题
                    for i in range(1, 7):
                        for heading in soup.find_all(f'h{i}'):
                            if heading.text.strip():
                                structured_data["headings"].append({
                                    "level": i,
                                    "text": heading.text.strip()
                                })
                    
                    # 提取段落
                    for p in soup.find_all('p'):
                        if p.text.strip():
                            structured_data["paragraphs"].append(p.text.strip())
                    
                    # 提取列表
                    for ul in soup.find_all(['ul', 'ol']):
                        list_items = []
                        for li in ul.find_all('li'):
                            if li.text.strip():
                                list_items.append(li.text.strip())
                        
                        if list_items:
                            structured_data["lists"].append({
                                "type": ul.name,
                                "items": list_items
                            })
                    
                    # 提取表格
                    for table in soup.find_all('table'):
                        table_data = []
                        rows = table.find_all('tr')
                        
                        for row in rows:
                            cells = row.find_all(['th', 'td'])
                            if cells:
                                row_data = [cell.text.strip() for cell in cells]
                                table_data.append(row_data)
                        
                        if table_data:
                            structured_data["tables"].append(table_data)
                    
                    # 提取表单
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
                        
                        structured_data["forms"].append(form_data)
                    
                    # 提取链接
                    for a in soup.find_all('a', href=True):
                        if a.text.strip():
                            structured_data["links"].append({
                                "text": a.text.strip(),
                                "href": a.get('href', '')
                            })
                    
                    # 保存结构化数据
                    json_file = os.path.join(tab_dir, "structured_data.json")
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(structured_data, f, ensure_ascii=False, indent=2)
                    
                    tab_info["files"].append({"type": "json", "name": "structured_data.json", "description": "结构化数据"})
                    
                except ImportError:
                    print("未安装BeautifulSoup，跳过结构化内容提取")
                except Exception as e:
                    print(f"提取结构化内容时出错: {str(e)}")
                
                # 检查并提取iframe内容
                try:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        print(f"  发现 {len(iframes)} 个iframe")
                        iframe_dir = os.path.join(tab_dir, "iframes")
                        if not os.path.exists(iframe_dir):
                            os.makedirs(iframe_dir)
                        
                        tab_info["iframes"] = []
                        
                        for iframe_index, iframe in enumerate(iframes):
                            iframe_info = {
                                "index": iframe_index + 1,
                                "src": iframe.get_attribute("src") or "无源地址",
                                "id": iframe.get_attribute("id") or f"iframe_{iframe_index+1}",
                                "content_extracted": False
                            }
                            
                            try:
                                # 切换到iframe
                                driver.switch_to.frame(iframe)
                                
                                # 获取内容
                                iframe_content = driver.page_source
                                iframe_text = driver.find_element(By.TAG_NAME, "body").text
                                
                                # 保存内容
                                iframe_html_file = os.path.join(iframe_dir, f"iframe_{iframe_index+1}.html")
                                with open(iframe_html_file, "w", encoding="utf-8") as f:
                                    f.write(iframe_content)
                                
                                iframe_text_file = os.path.join(iframe_dir, f"iframe_{iframe_index+1}.txt")
                                with open(iframe_text_file, "w", encoding="utf-8") as f:
                                    f.write(f"Iframe {iframe_index+1}\n")
                                    f.write(f"源: {iframe_info['src']}\n")
                                    f.write(f"ID: {iframe_info['id']}\n\n")
                                    f.write(iframe_text)
                                
                                # 捕获iframe截图
                                iframe_screenshot = os.path.join(iframe_dir, f"iframe_{iframe_index+1}.png")
                                driver.save_screenshot(iframe_screenshot)
                                
                                iframe_info["content_extracted"] = True
                                iframe_info["files"] = [
                                    {"type": "html", "name": f"iframe_{iframe_index+1}.html", "description": "HTML内容"},
                                    {"type": "text", "name": f"iframe_{iframe_index+1}.txt", "description": "文本内容"},
                                    {"type": "screenshot", "name": f"iframe_{iframe_index+1}.png", "description": "屏幕截图"}
                                ]
                                
                                print(f"  Iframe {iframe_index+1} ({iframe_info['id']}) 内容已提取")
                                
                                # 切回主文档
                                driver.switch_to.default_content()
                                
                            except Exception as e:
                                print(f"  提取iframe {iframe_index+1} 内容时出错: {str(e)}")
                                driver.switch_to.default_content()
                            
                            tab_info["iframes"].append(iframe_info)
                        
                except Exception as e:
                    print(f"处理iframe时出错: {str(e)}")
                
                # 尝试捕获API请求数据
                try:
                    js_get_requests = "return window._requestCaptures || [];"
                    api_requests = driver.execute_script(js_get_requests)
                    
                    if api_requests:
                        print(f"  捕获到 {len(api_requests)} 个API请求")
                        
                        # 保存API请求数据
                        api_dir = os.path.join(tab_dir, "api_data")
                        if not os.path.exists(api_dir):
                            os.makedirs(api_dir)
                        
                        api_json_file = os.path.join(api_dir, "api_responses.json")
                        with open(api_json_file, "w", encoding="utf-8") as f:
                            json.dump(api_requests, f, ensure_ascii=False, indent=2)
                        
                        tab_info["api_requests"] = len(api_requests)
                        tab_info["files"].append({"type": "json", "name": "api_data/api_responses.json", "description": "API响应数据"})
                        
                        # 为每个API响应创建单独的文件
                        for req_index, req in enumerate(api_requests):
                            # 只处理成功的请求
                            if req.get("status", 0) >= 200 and req.get("status", 0) < 300:
                                response_data = req.get("responseData")
                                if response_data:
                                    # 创建文件名
                                    url_parts = req.get("url", "").split("/")
                                    endpoint = url_parts[-1].split("?")[0] or "unknown"
                                    endpoint = clean_filename(endpoint)
                                    
                                    # 保存响应数据
                                    if isinstance(response_data, (dict, list)):
                                        # JSON数据
                                        req_file = os.path.join(api_dir, f"{req_index+1}_{endpoint}.json")
                                        with open(req_file, "w", encoding="utf-8") as f:
                                            json.dump(response_data, f, ensure_ascii=False, indent=2)
                                    else:
                                        # 文本数据
                                        req_file = os.path.join(api_dir, f"{req_index+1}_{endpoint}.txt")
                                        with open(req_file, "w", encoding="utf-8") as f:
                                            f.write(str(response_data))
                
                except Exception as e:
                    print(f"  处理API请求数据时出错: {str(e)}")
                
                print(f"标签页 '{tab['text']}' 的内容已保存到目录 {tab_dir}")
                
            else:
                print("DOM和URL无变化，可能不是真正的标签页或内容已预加载")
                with open(os.path.join(tab_dir, "info.txt"), "w", encoding="utf-8") as f:
                    f.write(f"标签页 '{tab['text']}' 点击后无明显变化\n")
                    f.write("可能不是真正的标签页或内容已预加载")
                
                tab_info["files"].append({"type": "text", "name": "info.txt", "description": "点击结果信息"})
            
        except Exception as e:
            print(f"处理标签页 '{tab['text']}' 时出错: {str(e)}")
            # 记录错误
            with open(os.path.join(tab_dir, "error.txt"), "w", encoding="utf-8") as f:
                f.write(f"处理时出错: {str(e)}")
            
            tab_info["error"] = str(e)
            tab_info["files"].append({"type": "text", "name": "error.txt", "description": "错误信息"})
        
        # 将标签页信息添加到索引中
        tabs_index.append(tab_info)
        main_info["tabs"].append(tab_info)
        
        # 尝试导航回初始URL (如果URL有变化)
        if driver.current_url != current_url:
            try:
                print(f"  导航回初始URL: {current_url}")
                driver.get(current_url)
                time.sleep(2)  # 等待页面加载
            except Exception as e:
                print(f"  导航回初始URL时出错: {str(e)}")
    
    # 保存标签页索引
    index_file = os.path.join(output_dir, "tabs_index.json")
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(main_info, f, ensure_ascii=False, indent=2)
    
    # 创建一个用户友好的HTML索引
    html_index = os.path.join(output_dir, "tabs_index.html")
    with open(html_index, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>标签页内容索引</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        .tab-card {{ 
            border: 1px solid #ddd; 
            border-radius: 5px; 
            margin-bottom: 20px; 
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .tab-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; }}
        .tab-content {{ margin-top: 15px; }}
        .file-list {{ margin-left: 20px; }}
        .file-item {{ margin-bottom: 5px; }}
        .screenshot {{ max-width: 300px; border: 1px solid #ddd; margin-top: 10px; }}
        .success {{ color: green; }}
        .warning {{ color: orange; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
    <h1>标签页内容索引</h1>
    <p><strong>URL:</strong> {current_url}</p>
    <p><strong>页面标题:</strong> {page_title}</p>
    <p><strong>找到 {len(tabs_index)} 个可能的标签页</strong></p>
    
    <h2>标签页列表</h2>
""")
        
        # 添加标签页卡片
        for tab in tabs_index:
            status_class = "success" if tab.get("content_extracted") else "warning"
            status_text = "内容已提取" if tab.get("content_extracted") else "点击后无明显变化"
            if "error" in tab:
                status_class = "error"
                status_text = f"错误: {tab['error']}"
            
            f.write(f"""
    <div class="tab-card">
        <div class="tab-header">
            <h3>#{tab['index']} - {tab['name']}</h3>
            <span class="{status_class}">{status_text}</span>
        </div>
        <div>
            <p><strong>元素类型:</strong> {tab['tag']}</p>
            {f'<p><strong>标题:</strong> {tab.get("title", "未知")}</p>' if tab.get("content_extracted") else ''}
            {f'<p><strong>URL变化为:</strong> {tab.get("new_url", "")}</p>' if tab.get("new_url") else ''}
        </div>
""")
            
            # 添加文件列表
            if tab.get("files"):
                f.write(f"""
        <div class="tab-content">
            <h4>内容文件:</h4>
            <ul class="file-list">
""")
                
                # 文件列表
                for file in tab["files"]:
                    file_path = f"tabs_content/{tab['index']}_{clean_filename(tab['name'])}/{file['name']}"
                    f.write(f'                <li class="file-item"><a href="{file_path}">{file["name"]}</a> - {file["description"]}</li>\n')
                
                f.write("            </ul>\n")
                
                # 显示截图
                f.write(f"""
            <div>
                <h4>截图:</h4>
                <p>点击前:</p>
                <img src="tabs_content/{tab['index']}_{clean_filename(tab['name'])}/before_click.png" class="screenshot" alt="点击前">
                
                <p>点击后:</p>
                <img src="tabs_content/{tab['index']}_{clean_filename(tab['name'])}/after_click.png" class="screenshot" alt="点击后">
            </div>
""")
                
                f.write("        </div>\n")
            
            # iframe信息
            if tab.get("iframes"):
                iframe_count = len(tab["iframes"])
                f.write(f"""
        <div class="tab-content">
            <h4>找到 {iframe_count} 个iframe</h4>
            <ul class="file-list">
""")
                
                for iframe in tab["iframes"]:
                    iframe_status = "内容已提取" if iframe.get("content_extracted") else "无法提取内容"
                    f.write(f'                <li>Iframe #{iframe["index"]}: {iframe["id"]} - {iframe_status}</li>\n')
                
                f.write("            </ul>\n        </div>\n")
            
            # API请求信息
            if tab.get("api_requests"):
                f.write(f"""
        <div class="tab-content">
            <h4>API请求</h4>
            <p>捕获到 {tab["api_requests"]} 个API请求</p>
            <p><a href="tabs_content/{tab['index']}_{clean_filename(tab['name'])}/api_data/api_responses.json">查看API响应数据</a></p>
        </div>
""")
            
            f.write("    </div>\n")
        
        # 结束HTML文件
        f.write("""
</body>
</html>
""")
    
    print(f"\n全部标签页内容已提取完成")
    print(f"- 标签页内容保存在: {tabs_dir}")
    print(f"- 索引JSON文件: {index_file}")
    print(f"- HTML索引: {html_index}")
    
    # 在开始时，创建并注入网络请求监控脚本
    def inject_network_monitor(driver):
        """注入JavaScript来监控网络请求"""
        js_xhr_monitor = """
        // 存储捕获的请求
        window._requestCaptures = [];
        
        // 拦截XMLHttpRequest
        (function(open) {
            XMLHttpRequest.prototype.open = function() {
                this._requestMethod = arguments[0];
                this._requestUrl = arguments[1];
                this._requestTime = new Date().getTime();
                return open.apply(this, arguments);
            };
        })(XMLHttpRequest.prototype.open);
        
        (function(send) {
            XMLHttpRequest.prototype.send = function() {
                const xhr = this;
                this._requestBody = arguments[0] || null;
                
                // 处理响应
                xhr.addEventListener('load', function() {
                    try {
                        let responseData = xhr.responseText;
                        let contentType = xhr.getResponseHeader('Content-Type') || '';
                        
                        // 尝试解析JSON
                        if(contentType.includes('application/json') || 
                           (responseData && responseData.trim().startsWith('{'))) {
                            try {
                                responseData = JSON.parse(responseData);
                            } catch(e) {
                                // 无法解析为JSON，保持原文本
                            }
                        }
                        
                        window._requestCaptures.push({
                            type: 'xhr',
                            method: xhr._requestMethod,
                            url: xhr._requestUrl,
                            time: xhr._requestTime,
                            requestBody: xhr._requestBody,
                            status: xhr.status,
                            responseType: contentType,
                            responseData: responseData
                        });
                    } catch(e) {
                        console.error('XHR响应捕获错误:', e);
                    }
                });
                
                return send.apply(this, arguments);
            };
        })(XMLHttpRequest.prototype.send);
        
        // 拦截Fetch
        (function(fetch) {
            window.fetch = function() {
                const url = arguments[0];
                const options = arguments[1] || {};
                const method = options.method || 'GET';
                const requestBody = options.body || null;
                const requestTime = new Date().getTime();
                
                return fetch.apply(this, arguments).then(response => {
                    // 克隆响应以便我们可以同时读取它并将其返回
                    const responseClone = response.clone();
                    
                    responseClone.text().then(text => {
                        let responseData = text;
                        let contentType = response.headers.get('Content-Type') || '';
                        
                        // 尝试解析JSON
                        if(contentType.includes('application/json') || 
                           (responseData && responseData.trim().startsWith('{'))) {
                            try {
                                responseData = JSON.parse(responseData);
                            } catch(e) {
                                // 无法解析为JSON，保持原文本
                            }
                        }
                        
                        window._requestCaptures.push({
                            type: 'fetch',
                            method: method,
                            url: typeof url === 'string' ? url : url.url,
                            time: requestTime,
                            requestBody: requestBody,
                            status: response.status,
                            responseType: contentType,
                            responseData: responseData
                        });
                    }).catch(e => {
                        console.error('Fetch响应捕获错误:', e);
                    });
                    
                    return response;
                });
            };
        })(window.fetch);
        
        console.log('已安装XHR/Fetch拦截器');
        """
        
        driver.execute_script(js_xhr_monitor)
        print("已注入网络请求监控脚本")
    
    # 在页面初始分析时注入监控脚本
    inject_network_monitor(driver)
    
    # 最后尝试查找和分析iframe
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            print(f"找到 {len(iframes)} 个iframe")
            
            iframe_dir = os.path.join(output_dir, "iframes")
            if not os.path.exists(iframe_dir):
                os.makedirs(iframe_dir)
            
            for i, iframe in enumerate(iframes):
                try:
                    iframe_src = iframe.get_attribute("src") or "无源地址"
                    iframe_id = iframe.get_attribute("id") or f"iframe_{i+1}"
                    
                    print(f"处理iframe: {iframe_id} (源: {iframe_src})")
                    
                    # 创建iframe目录
                    iframe_sub_dir = os.path.join(iframe_dir, f"iframe_{i+1}_{clean_filename(iframe_id)}")
                    if not os.path.exists(iframe_sub_dir):
                        os.makedirs(iframe_sub_dir)
                    
                    # 获取iframe在页面中的位置和大小（用于后续裁剪）
                    iframe_rect = None
                    try:
                        iframe_rect = {
                            'x': iframe.rect['x'],
                            'y': iframe.rect['y'],
                            'width': iframe.rect['width'],
                            'height': iframe.rect['height']
                        }
                    except:
                        pass
                    
                    # 捕获iframe信息
                    info_file = os.path.join(iframe_sub_dir, "info.txt")
                    with open(info_file, "w", encoding="utf-8") as f:
                        f.write(f"iframe: {iframe_id}\n")
                        f.write(f"源URL: {iframe_src}\n")
                        if iframe_rect:
                            f.write(f"位置: x={iframe_rect['x']}, y={iframe_rect['y']}, 宽={iframe_rect['width']}, 高={iframe_rect['height']}\n")
                    
                    # 先捕获iframe的原始视图（未切换到iframe前）
                    try:
                        from PIL import Image
                        import io
                        
                        # 捕获整个窗口的截图
                        original_screenshot = driver.get_screenshot_as_png()
                        img = Image.open(io.BytesIO(original_screenshot))
                        
                        # 如果获取到了iframe位置，裁剪图像
                        if iframe_rect:
                            # 考虑设备像素比
                            pixel_ratio = driver.execute_script('return window.devicePixelRatio') or 1
                            
                            # 获取原始图像尺寸
                            img_width, img_height = img.size
                            
                            # 计算裁剪区域
                            x = int(iframe_rect['x'] * pixel_ratio)
                            y = int(iframe_rect['y'] * pixel_ratio)
                            width = int(iframe_rect['width'] * pixel_ratio)
                            height = int(iframe_rect['height'] * pixel_ratio)
                            
                            # 确保裁剪区域不超出图像边界
                            x = max(0, x)
                            y = max(0, y) 
                            right = min(img_width, x + width)
                            bottom = min(img_height, y + height)
                            
                            # 检查裁剪区域是否有效
                            if x < right and y < bottom:
                                # 裁剪iframe区域
                                iframe_view = img.crop((x, y, right, bottom))
                                iframe_view.save(os.path.join(iframe_sub_dir, "iframe_view.png"))
                                print(f"已保存iframe外部视图")
                            else:
                                # 裁剪区域无效，保存原始截图
                                img.save(os.path.join(iframe_sub_dir, "full_page.png"))
                                print(f"iframe位于可见区域外，已保存完整页面截图")
                    except ImportError:
                        print("未安装PIL，无法裁剪iframe视图。使用pip install pillow安装")
                    except Exception as e:
                        print(f"捕获iframe外部视图时出错: {str(e)}")
                        # 在出错时保存原始截图
                        try:
                            original_screenshot = driver.get_screenshot_as_png()
                            with open(os.path.join(iframe_sub_dir, "original_screenshot.png"), "wb") as f:
                                f.write(original_screenshot)
                            print("已保存原始截图")
                        except:
                            pass
                    
                    # 现在切换到iframe内部
                    try:
                        driver.switch_to.frame(iframe)
                        
                        # 首先尝试使用JavaScript的html2canvas捕获内容
                        try:
                            # 注入html2canvas库
                            driver.execute_script("""
                            if (!window.html2canvas) {
                                var script = document.createElement('script');
                                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                                script.async = false;
                                document.head.appendChild(script);
                            }
                            """)
                            
                            # 等待库加载完成
                            time.sleep(2)
                            
                            # 使用html2canvas截取iframe内容
                            screenshot_data = driver.execute_script("""
                            return new Promise((resolve) => {
                                // 检查html2canvas是否已加载
                                if (typeof html2canvas === 'undefined') {
                                    console.log('html2canvas未加载');
                                    resolve(null);
                                    return;
                                }
                                
                                html2canvas(document.body, {
                                    logging: false,
                                    allowTaint: true,
                                    useCORS: true
                                }).then(function(canvas) {
                                    resolve(canvas.toDataURL('image/png'));
                                }).catch(function(err) {
                                    console.error('Canvas截图失败:', err);
                                    resolve(null);
                                });
                            });
                            """)
                            
                            if screenshot_data and screenshot_data.startswith('data:image/png;base64,'):
                                # 保存base64图像数据为文件
                                import base64
                                screenshot_file = os.path.join(iframe_sub_dir, "iframe_content.png")
                                
                                # 移除data URL前缀
                                screenshot_data = screenshot_data[len('data:image/png;base64,'):]
                                    
                                with open(screenshot_file, "wb") as f:
                                    f.write(base64.b64decode(screenshot_data))
                                print(f"已使用html2canvas捕获iframe内容")
                            else:
                                # 退回到常规截图
                                driver.save_screenshot(os.path.join(iframe_sub_dir, "iframe_screenshot.png"))
                                print(f"html2canvas失败，已使用常规方法捕获iframe的窗口截图")
                        except Exception as e:
                            print(f"使用html2canvas捕获iframe内容时出错: {str(e)}")
                            # 退回到常规截图
                            driver.save_screenshot(os.path.join(iframe_sub_dir, "iframe_screenshot.png"))
                        
                        # 获取HTML内容
                        html_content = driver.page_source
                        html_file = os.path.join(iframe_sub_dir, "content.html")
                        with open(html_file, "w", encoding="utf-8") as f:
                            f.write(html_content)
                        
                        # 获取文本内容
                        text_content = driver.find_element(By.TAG_NAME, "body").text
                        text_file = os.path.join(iframe_sub_dir, "content.txt")
                        with open(text_file, "w", encoding="utf-8") as f:
                            f.write(text_content)
                        
                        print(f"已提取iframe '{iframe_id}' 的内容")
                        
                        # 切回主文档
                        driver.switch_to.default_content()
                        
                    except Exception as e:
                        print(f"提取iframe内容时出错: {str(e)}")
                        # 确保切回主文档
                        driver.switch_to.default_content()
                    
                except Exception as e:
                    print(f"处理iframe时出错: {str(e)}")
            
            print(f"所有iframe内容已保存到 {iframe_dir}")
        
    except Exception as e:
        print(f"检查iframe时出错: {str(e)}")
    
    return True
def extract_structured_content(driver, filename="structured_content.json"):
    """使用BeautifulSoup提取结构化内容"""
    try:
        # 获取页面HTML
        html_content = driver.page_source
        
        # 使用BeautifulSoup解析
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除script和style元素
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # 结构化数据字典
        structured_data = {
            "title": soup.title.text if soup.title else "",
            "headings": [],
            "paragraphs": [],
            "lists": [],
            "tables": [],
            "forms": [],
            "links": [],
            "images": []
        }
        
        # 提取标题
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                if heading.text.strip():
                    structured_data["headings"].append({
                        "level": i,
                        "text": heading.text.strip()
                    })
        
        # 提取段落
        for p in soup.find_all('p'):
            if p.text.strip():
                structured_data["paragraphs"].append(p.text.strip())
        
        # 提取列表
        for ul in soup.find_all(['ul', 'ol']):
            list_items = []
            for li in ul.find_all('li'):
                if li.text.strip():
                    list_items.append(li.text.strip())
            
            if list_items:
                structured_data["lists"].append({
                    "type": ul.name,
                    "items": list_items
                })
        
        # 提取表格
        for table in soup.find_all('table'):
            table_data = []
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if cells:
                    row_data = [cell.text.strip() for cell in cells]
                    table_data.append(row_data)
            
            if table_data:
                structured_data["tables"].append(table_data)
        
        # 提取表单
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
            
            structured_data["forms"].append(form_data)
        
        # 提取链接
        for a in soup.find_all('a', href=True):
            if a.text.strip():
                structured_data["links"].append({
                    "text": a.text.strip(),
                    "href": a.get('href', '')
                })
        
        # 提取图片
        for img in soup.find_all('img'):
            img_data = {
                "alt": img.get('alt', ''),
                "src": img.get('src', '')
            }
            structured_data["images"].append(img_data)
        
        # 提取主要文本内容（用于简单文本分析）
        main_text = soup.get_text(separator=' ', strip=True)
        structured_data["full_text"] = main_text
        
        # 保存为JSON
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
        print(f"结构化内容已保存到 {filename}")
        
        # 保存一个可读性更好的文本版本
        text_filename = filename.rsplit('.', 1)[0] + '.txt'
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(f"页面标题: {structured_data['title']}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("标题结构:\n")
            f.write("=" * 80 + "\n\n")
            
            for heading in structured_data["headings"]:
                f.write("  " * (heading["level"]-1) + heading["text"] + "\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("主要段落内容:\n")
            f.write("=" * 80 + "\n\n")
            
            for para in structured_data["paragraphs"]:
                f.write(para + "\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("列表内容:\n")
            f.write("=" * 80 + "\n\n")
            
            for i, lst in enumerate(structured_data["lists"]):
                f.write(f"列表 {i+1} ({lst['type']}):\n")
                for j, item in enumerate(lst["items"]):
                    f.write(f"  {j+1}. {item}\n")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("链接内容:\n")
            f.write("=" * 80 + "\n\n")
            
            for link in structured_data["links"]:
                f.write(f"{link['text']}: {link['href']}\n")
        
        print(f"文本版内容已保存到 {text_filename}")
        
        return structured_data
        
    except ImportError:
        print("请安装BeautifulSoup库: pip install beautifulsoup4")
        return None
    except Exception as e:
        print(f"提取结构化内容时出错: {str(e)}")
        return None

def analyze_claude_selectors(driver, output_file="claude_selectors.txt"):
    """
    Analyze the Claude page to find accurate selectors for key elements
    
    Args:
        driver: Selenium WebDriver instance
        output_file: Path to output file for results
    
    Returns:
        Dict containing discovered selectors for key page elements
    """
    try:
        print("Analyzing Claude UI for accurate selectors...")
        
        # Execute JavaScript to analyze the page and find selectors
        js_script = """
        function findBestSelectors() {
            // Helper functions
            function getAttributes(element) {
                const result = {};
                const attrs = element.attributes;
                for (let i = 0; i < attrs.length; i++) {
                    result[attrs[i].name] = attrs[i].value;
                }
                return result;
            }
            
            function testSelector(selector) {
                try {
                    const elements = document.querySelectorAll(selector);
                    return {
                        count: elements.length,
                        valid: elements.length > 0,
                        elements: Array.from(elements).slice(0, 3).map(el => ({
                            tag: el.tagName.toLowerCase(),
                            text: el.textContent.trim().substring(0, 50),
                            attributes: getAttributes(el),
                            visible: isVisible(el),
                            location: getElementLocation(el)
                        }))
                    };
                } catch (e) {
                    return { count: 0, valid: false, error: e.toString() };
                }
            }
            
            function isVisible(el) {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       parseFloat(style.opacity) > 0 &&
                       el.offsetWidth > 0 && 
                       el.offsetHeight > 0;
            }
            
            function getElementLocation(el) {
                const rect = el.getBoundingClientRect();
                return {
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                };
            }
            
            // Find New Chat button
            function findNewChatButton() {
                const candidates = [
                    // Test exact selectors
                    '[data-testid="new-chat"]',
                    'button[data-testid="new-chat"]',
                    'a[href="/new"]',
                    // Test text content
                    'button:contains("New chat")',
                    'a:contains("New chat")',
                    'button:contains("Start new chat")',
                    'a:contains("Start new chat")',
                    // Test class and attribute patterns
                    '.new-chat',
                    '[aria-label*="new chat" i]',
                    '[title*="new chat" i]',
                    // Test location
                    'nav a:first-child',
                    'nav button:first-child',
                    'header a:first-child',
                    'header button:first-child',
                    // Visual clues
                    'button svg + span:contains("new" i)',
                    'a svg + span:contains("new" i)'
                ];
                
                // Look for icons/buttons/links in the sidebar
                const sidebar = document.querySelector('nav, aside, .sidebar, [role="navigation"]');
                if (sidebar) {
                    const sidebarButtons = sidebar.querySelectorAll('a, button');
                    // Look for elements with "new" or "chat" related text
                    for (const button of sidebarButtons) {
                        const text = button.textContent.trim().toLowerCase();
                        if (text.includes('new') || text.includes('chat')) {
                            candidates.push(createSelectorForElement(button));
                        }
                    }
                }
                
                // Scan the DOM for elements with "new chat" related text 
                const textWalker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    { acceptNode: node => 
                        node.textContent.trim().toLowerCase().includes('new chat') ||
                        node.textContent.trim().toLowerCase().includes('start new') ?
                        NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT
                    }
                );
                
                while (textWalker.nextNode()) {
                    const node = textWalker.currentNode;
                    const parent = node.parentElement;
                    if (parent && isVisible(parent)) {
                        // Get a clickable parent (button or a)
                        let clickableParent = parent;
                        while (clickableParent && 
                               clickableParent.tagName !== 'BUTTON' && 
                               clickableParent.tagName !== 'A') {
                            clickableParent = clickableParent.parentElement;
                            if (!clickableParent || clickableParent === document.body) break;
                        }
                        
                        if (clickableParent && (clickableParent.tagName === 'BUTTON' || clickableParent.tagName === 'A')) {
                            candidates.push(createSelectorForElement(clickableParent));
                        } else {
                            candidates.push(createSelectorForElement(parent));
                        }
                    }
                }
                
                // Create a specific selector for an element
                function createSelectorForElement(element) {
                    // Try ID
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    // Try data attributes
                    for (const attr of element.attributes) {
                        if (attr.name.startsWith('data-')) {
                            return `[${attr.name}="${attr.value}"]`;
                        }
                    }
                    
                    // Try classes
                    if (element.className) {
                        const classes = element.className.split(/\\s+/).filter(c => c);
                        if (classes.length > 0) {
                            return `.${classes.join('.')}`;
                        }
                    }
                    
                    // Try position
                    const parent = element.parentElement;
                    if (parent) {
                        const index = Array.from(parent.children).indexOf(element) + 1;
                        return `${parent.tagName.toLowerCase()} > ${element.tagName.toLowerCase()}:nth-child(${index})`;
                    }
                    
                    return element.tagName.toLowerCase();
                }
                
                // Test all selectors
                const results = [];
                for (const selector of new Set(candidates)) {
                    const test = testSelector(selector);
                    if (test.valid) {
                        results.push({
                            selector,
                            test
                        });
                    }
                }
                
                // Prioritize results
                return results.sort((a, b) => {
                    // Prefer visible elements
                    const aHasVisible = a.test.elements.some(el => el.visible);
                    const bHasVisible = b.test.elements.some(el => el.visible);
                    if (aHasVisible && !bHasVisible) return -1;
                    if (!aHasVisible && bHasVisible) return 1;
                    
                    // Prefer elements with "new chat" text
                    const aHasNewChatText = a.test.elements.some(el => 
                        el.text.toLowerCase().includes('new chat') || 
                        el.text.toLowerCase().includes('start new'));
                    const bHasNewChatText = b.test.elements.some(el => 
                        el.text.toLowerCase().includes('new chat') || 
                        el.text.toLowerCase().includes('start new'));
                    if (aHasNewChatText && !bHasNewChatText) return -1;
                    if (!aHasNewChatText && bHasNewChatText) return 1;
                    
                    // Prefer more specific selectors
                    return a.selector.length - b.selector.length;
                });
            }
            
            // Find File Upload elements
            function findFileUploadElements() {
                const candidates = [
                    // Direct input selectors
                    'input[type="file"]',
                    // Upload button selectors
                    '[data-testid="image-upload-button"]',
                    '[data-testid="file-upload-button"]',
                    '[data-testid="attachment-button"]',
                    // Attribute patterns
                    '[aria-label*="upload" i]',
                    '[aria-label*="attach" i]',
                    '[title*="upload" i]',
                    '[title*="attach" i]',
                    // Text patterns
                    'button:contains("Upload")',
                    'button:contains("Attach")',
                    'label:contains("Upload")',
                    'label:contains("Attach")',
                    // Icon patterns
                    'button svg[*|href*="upload"]',
                    'button svg[*|href*="attach"]',
                    'button svg[*|href*="paperclip"]',
                    'button svg[*|href*="file"]'
                ];
                
                // Look at the input area
                const inputArea = document.querySelector('textarea, [contenteditable="true"], .ProseMirror');
                if (inputArea) {
                    // Look for nearby buttons that might be upload buttons
                    const parent = inputArea.closest('form') || inputArea.closest('div');
                    if (parent) {
                        const nearbyButtons = parent.querySelectorAll('button, label');
                        for (const button of nearbyButtons) {
                            candidates.push(createSelectorForElement(button));
                        }
                    }
                }
                
                // Create a specific selector for an element
                function createSelectorForElement(element) {
                    // Try ID
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    // Try data attributes
                    for (const attr of element.attributes) {
                        if (attr.name.startsWith('data-')) {
                            return `[${attr.name}="${attr.value}"]`;
                        }
                    }
                    
                    // Try classes
                    if (element.className) {
                        const classes = element.className.split(/\\s+/).filter(c => c);
                        if (classes.length > 0) {
                            return `.${classes.join('.')}`;
                        }
                    }
                    
                    // Try position
                    const parent = element.parentElement;
                    if (parent) {
                        const index = Array.from(parent.children).indexOf(element) + 1;
                        return `${parent.tagName.toLowerCase()} > ${element.tagName.toLowerCase()}:nth-child(${index})`;
                    }
                    
                    return element.tagName.toLowerCase();
                }
                
                // Test all selectors
                const results = [];
                for (const selector of new Set(candidates)) {
                    const test = testSelector(selector);
                    if (test.valid) {
                        results.push({
                            selector,
                            test
                        });
                    }
                }
                
                // Prioritize results
                const uploadButtons = results
                    .filter(r => r.selector !== 'input[type="file"]') // Exclude file inputs for button section
                    .sort((a, b) => {
                        // Prefer visible elements
                        const aHasVisible = a.test.elements.some(el => el.visible);
                        const bHasVisible = b.test.elements.some(el => el.visible);
                        if (aHasVisible && !bHasVisible) return -1;
                        if (!aHasVisible && bHasVisible) return 1;
                        
                        // Prefer elements with upload-related attributes
                        const aHasUploadAttr = a.test.elements.some(el => 
                            Object.entries(el.attributes).some(([k,v]) => 
                                k.includes('upload') || v.includes('upload') ||
                                k.includes('attach') || v.includes('attach') ||
                                k.includes('file') || v.includes('file')));
                        const bHasUploadAttr = b.test.elements.some(el => 
                            Object.entries(el.attributes).some(([k,v]) => 
                                k.includes('upload') || v.includes('upload') ||
                                k.includes('attach') || v.includes('attach') ||
                                k.includes('file') || v.includes('file')));
                        if (aHasUploadAttr && !bHasUploadAttr) return -1;
                        if (!aHasUploadAttr && bHasUploadAttr) return 1;
                        
                        // Prefer more specific selectors
                        return a.selector.length - b.selector.length;
                    });
                
                // Get file inputs separately
                const fileInputs = results
                    .filter(r => r.selector === 'input[type="file"]' || 
                                r.test.elements.some(el => el.tag === 'input' && el.attributes.type === 'file'))
                    .sort((a, b) => {
                        // Prefer visible elements
                        const aHasVisible = a.test.elements.some(el => el.visible);
                        const bHasVisible = b.test.elements.some(el => el.visible);
                        if (aHasVisible && !bHasVisible) return -1;
                        if (!aHasVisible && bHasVisible) return 1;
                        
                        // Prefer elements with more specific attributes
                        return Object.keys(b.test.elements[0]?.attributes || {}).length - 
                               Object.keys(a.test.elements[0]?.attributes || {}).length;
                    });
                
                return {
                    uploadButtons,
                    fileInputs
                };
            }
            
            // Find Message Input field
            function findMessageInput() {
                const candidates = [
                    // Test exact selectors
                    '[data-testid="chat-input-box"]',
                    '.ProseMirror',
                    '[contenteditable="true"]',
                    'textarea',
                    // Test aria attributes
                    '[aria-label*="message" i]',
                    '[aria-label*="chat" i]',
                    '[aria-label*="input" i]',
                    // Test placeholder
                    '[placeholder*="message" i]',
                    '[placeholder*="chat" i]',
                    '[placeholder*="ask" i]',
                    // Test form fields
                    'form textarea',
                    'form [contenteditable="true"]',
                    'form input[type="text"]'
                ];
                
                // Test all selectors
                const results = [];
                for (const selector of candidates) {
                    const test = testSelector(selector);
                    if (test.valid) {
                        results.push({
                            selector,
                            test
                        });
                    }
                }
                
                // Prioritize results
                return results.sort((a, b) => {
                    // Prefer contenteditable div or textarea
                    const aIsProperInput = a.test.elements.some(el => 
                        (el.tag === 'div' && el.attributes.contenteditable === 'true') || 
                        el.tag === 'textarea');
                    const bIsProperInput = b.test.elements.some(el => 
                        (el.tag === 'div' && el.attributes.contenteditable === 'true') || 
                        el.tag === 'textarea');
                    if (aIsProperInput && !bIsProperInput) return -1;
                    if (!aIsProperInput && bIsProperInput) return 1;
                    
                    // Prefer visible elements
                    const aHasVisible = a.test.elements.some(el => el.visible);
                    const bHasVisible = b.test.elements.some(el => el.visible);
                    if (aHasVisible && !bHasVisible) return -1;
                    if (!aHasVisible && bHasVisible) return 1;
                    
                    // Prefer elements at the bottom of the page (typical for chat inputs)
                    const aBottomPosition = Math.max(...a.test.elements.map(el => el.location?.y || 0));
                    const bBottomPosition = Math.max(...b.test.elements.map(el => el.location?.y || 0));
                    return bBottomPosition - aBottomPosition;
                });
            }
            
            // Find Send Button
            function findSendButton() {
                const candidates = [
                    // Test exact selectors
                    '[data-testid="send-message-button"]',
                    'button[aria-label="Send Message"]',
                    'button.bg-accent-main-100',
                    // Test text content
                    'button:contains("Send")',
                    // Test attribute patterns
                    '[aria-label*="send" i]',
                    '[title*="send" i]',
                    // Test SVG icons commonly used for send
                    'button svg[*|href*="send"]',
                    'button svg[*|href*="arrow"]',
                    'button svg[*|href*="paper-plane"]'
                ];
                
                // Find the textarea or input field first, then look for nearby buttons
                const inputField = document.querySelector('textarea, [contenteditable="true"], .ProseMirror');
                if (inputField) {
                    const parent = inputField.closest('form') || inputField.closest('div');
                    if (parent) {
                        const nearbyButtons = parent.querySelectorAll('button');
                        for (const button of nearbyButtons) {
                            candidates.push(createSelectorForElement(button));
                        }
                    }
                }
                
                // Create a specific selector for an element
                function createSelectorForElement(element) {
                    // Try ID
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    // Try data attributes
                    for (const attr of element.attributes) {
                        if (attr.name.startsWith('data-')) {
                            return `[${attr.name}="${attr.value}"]`;
                        }
                    }
                    
                    // Try classes
                    if (element.className) {
                        const classes = element.className.split(/\\s+/).filter(c => c);
                        if (classes.length > 0) {
                            return `.${classes.join('.')}`;
                        }
                    }
                    
                    // Try position - assuming the send button is often the last button
                    const parent = element.parentElement;
                    if (parent) {
                        const buttons = Array.from(parent.querySelectorAll('button'));
                        if (buttons.length > 0 && buttons[buttons.length - 1] === element) {
                            return `${parent.tagName.toLowerCase()} > button:last-child`;
                        }
                        
                        const index = Array.from(parent.children).indexOf(element) + 1;
                        return `${parent.tagName.toLowerCase()} > ${element.tagName.toLowerCase()}:nth-child(${index})`;
                    }
                    
                    return element.tagName.toLowerCase();
                }
                
                // Test all selectors
                const results = [];
                for (const selector of new Set(candidates)) {
                    const test = testSelector(selector);
                    if (test.valid) {
                        results.push({
                            selector,
                            test
                        });
                    }
                }
                
                // Prioritize results
                return results.sort((a, b) => {
                    // Prefer visible elements
                    const aHasVisible = a.test.elements.some(el => el.visible);
                    const bHasVisible = b.test.elements.some(el => el.visible);
                    if (aHasVisible && !bHasVisible) return -1;
                    if (!aHasVisible && bHasVisible) return 1;
                    
                    // Prefer elements with "send" related attributes
                    const aHasSendAttr = a.test.elements.some(el => 
                        Object.entries(el.attributes).some(([k,v]) => 
                            k.includes('send') || v.includes('send')));
                    const bHasSendAttr = b.test.elements.some(el => 
                        Object.entries(el.attributes).some(([k,v]) => 
                            k.includes('send') || v.includes('send')));
                    if (aHasSendAttr && !bHasSendAttr) return -1;
                    if (!aHasSendAttr && bHasSendAttr) return 1;
                    
                    // Prefer elements near the input field
                    return 0;
                });
            }
            
            // Return all discovered selectors
            return {
                newChatSelectors: findNewChatButton(),
                fileUploadSelectors: findFileUploadElements(),
                messageInputSelectors: findMessageInput(),
                sendButtonSelectors: findSendButton(),
            };
        }
        
        return findBestSelectors();
        """
        
        # Execute the JavaScript to analyze selectors
        selector_data = driver.execute_script(js_script)
        
        # Process the results
        best_selectors = {
            'new_chat_button': None,
            'upload_button': None,
            'file_input': None,
            'prompt_textarea': None,
            'send_button': None
        }
        
        # Find best new chat button selector
        if selector_data.get('newChatSelectors'):
            for item in selector_data['newChatSelectors']:
                visible_elements = [el for el in item['test']['elements'] if el['visible']]
                if visible_elements:
                    best_selectors['new_chat_button'] = item['selector']
                    break
            
            # If no visible elements, take the first one
            if not best_selectors['new_chat_button'] and selector_data['newChatSelectors']:
                best_selectors['new_chat_button'] = selector_data['newChatSelectors'][0]['selector']
        
        # Find best upload button selector
        if selector_data.get('fileUploadSelectors') and selector_data['fileUploadSelectors'].get('uploadButtons'):
            for item in selector_data['fileUploadSelectors']['uploadButtons']:
                visible_elements = [el for el in item['test']['elements'] if el['visible']]
                if visible_elements:
                    best_selectors['upload_button'] = item['selector']
                    break
            
            # If no visible elements, take the first one
            if not best_selectors['upload_button'] and selector_data['fileUploadSelectors']['uploadButtons']:
                best_selectors['upload_button'] = selector_data['fileUploadSelectors']['uploadButtons'][0]['selector']
        
        # Find best file input selector
        if selector_data.get('fileUploadSelectors') and selector_data['fileUploadSelectors'].get('fileInputs'):
            for item in selector_data['fileUploadSelectors']['fileInputs']:
                if item['test']['elements']:
                    best_selectors['file_input'] = item['selector']
                    break
        
        # Find best message input selector
        if selector_data.get('messageInputSelectors'):
            for item in selector_data['messageInputSelectors']:
                visible_elements = [el for el in item['test']['elements'] if el['visible']]
                if visible_elements:
                    best_selectors['prompt_textarea'] = item['selector']
                    break
            
            # If no visible elements, take the first one
            if not best_selectors['prompt_textarea'] and selector_data['messageInputSelectors']:
                best_selectors['prompt_textarea'] = selector_data['messageInputSelectors'][0]['selector']
        
        # Find best send button selector
        if selector_data.get('sendButtonSelectors'):
            for item in selector_data['sendButtonSelectors']:
                visible_elements = [el for el in item['test']['elements'] if el['visible']]
                if visible_elements:
                    best_selectors['send_button'] = item['selector']
                    break
            
            # If no visible elements, take the first one
            if not best_selectors['send_button'] and selector_data['sendButtonSelectors']:
                best_selectors['send_button'] = selector_data['sendButtonSelectors'][0]['selector']
        
        # Write results to file using raw strings to avoid escaping issues
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Claude UI Selectors Analysis\n")
            f.write(f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Write best selectors
            f.write("## Best Selectors\n\n")
            f.write("```python\n")
            f.write("CLAUDE_SELECTORS = {\n")
            for key, selector in best_selectors.items():
                if selector:
                    f.write(f"    '{key}': '{selector}',\n")
                else:
                    f.write(f"    '{key}': None,  # Not found\n")
            f.write("}\n")
            f.write("```\n\n")
            
            # Write detailed analysis
            f.write("## Detailed Analysis\n\n")
            
            # New Chat Button
            f.write("### New Chat Button\n\n")
            if selector_data.get('newChatSelectors'):
                for i, item in enumerate(selector_data['newChatSelectors'][:5]):  # Show top 5
                    f.write(f"**Candidate {i+1}**: `{item['selector']}` (Matches: {item['test']['count']})\n\n")
                    
                    # Show element details
                    for j, el in enumerate(item['test']['elements']):
                        f.write(f"Element {j+1}:\n")
                        f.write(f"- Tag: {el['tag']}\n")
                        f.write(f"- Visible: {el['visible']}\n")
                        f.write(f"- Text: {el['text']}\n")
                        
                        # Show key attributes
                        attrs = ", ".join([f"{k}='{v}'" for k, v in el['attributes'].items() 
                                        if k in ['id', 'class', 'data-testid', 'aria-label', 'role']])
                        if attrs:
                            f.write(f"- Attributes: {attrs}\n")
                        f.write("\n")
            else:
                f.write("No new chat button selectors found.\n\n")
            
            # Upload Button
            f.write("### Upload Button\n\n")
            if selector_data.get('fileUploadSelectors') and selector_data['fileUploadSelectors'].get('uploadButtons'):
                for i, item in enumerate(selector_data['fileUploadSelectors']['uploadButtons'][:5]):
                    f.write(f"**Candidate {i+1}**: `{item['selector']}` (Matches: {item['test']['count']})\n\n")
                    
                    # Show element details
                    for j, el in enumerate(item['test']['elements']):
                        f.write(f"Element {j+1}:\n")
                        f.write(f"- Tag: {el['tag']}\n")
                        f.write(f"- Visible: {el['visible']}\n")
                        f.write(f"- Text: {el['text']}\n")
                        
                        # Show key attributes
                        attrs = ", ".join([f"{k}='{v}'" for k, v in el['attributes'].items() 
                                        if k in ['id', 'class', 'data-testid', 'aria-label', 'role']])
                        if attrs:
                            f.write(f"- Attributes: {attrs}\n")
                        f.write("\n")
            else:
                f.write("No upload button selectors found.\n\n")
            
            # File Input
            f.write("### File Input\n\n")
            if selector_data.get('fileUploadSelectors') and selector_data['fileUploadSelectors'].get('fileInputs'):
                for i, item in enumerate(selector_data['fileUploadSelectors']['fileInputs'][:5]):
                    f.write(f"**Candidate {i+1}**: `{item['selector']}` (Matches: {item['test']['count']})\n\n")
                    
                    # Show element details
                    for j, el in enumerate(item['test']['elements']):
                        f.write(f"Element {j+1}:\n")
                        f.write(f"- Tag: {el['tag']}\n")
                        f.write(f"- Visible: {el['visible']}\n")
                        
                        # Show key attributes
                        attrs = ", ".join([f"{k}='{v}'" for k, v in el['attributes'].items() 
                                        if k in ['id', 'class', 'data-testid', 'name', 'type']])
                        if attrs:
                            f.write(f"- Attributes: {attrs}\n")
                        f.write("\n")
            else:
                f.write("No file input selectors found.\n\n")
            
            # Message Input
            f.write("### Message Input\n\n")
            if selector_data.get('messageInputSelectors'):
                for i, item in enumerate(selector_data['messageInputSelectors'][:5]):
                    f.write(f"**Candidate {i+1}**: `{item['selector']}` (Matches: {item['test']['count']})\n\n")
                    
                    # Show element details
                    for j, el in enumerate(item['test']['elements']):
                        f.write(f"Element {j+1}:\n")
                        f.write(f"- Tag: {el['tag']}\n")
                        f.write(f"- Visible: {el['visible']}\n")
                        
                        # Show key attributes
                        attrs = ", ".join([f"{k}='{v}'" for k, v in el['attributes'].items() 
                                        if k in ['id', 'class', 'data-testid', 'contenteditable', 'placeholder']])
                        if attrs:
                            f.write(f"- Attributes: {attrs}\n")
                        f.write("\n")
            else:
                f.write("No message input selectors found.\n\n")
            
            # Send Button
            f.write("### Send Button\n\n")
            if selector_data.get('sendButtonSelectors'):
                for i, item in enumerate(selector_data['sendButtonSelectors'][:5]):
                    f.write(f"**Candidate {i+1}**: `{item['selector']}` (Matches: {item['test']['count']})\n\n")
                    
                    # Show element details
                    for j, el in enumerate(item['test']['elements']):
                        f.write(f"Element {j+1}:\n")
                        f.write(f"- Tag: {el['tag']}\n")
                        f.write(f"- Visible: {el['visible']}\n")
                        f.write(f"- Text: {el['text']}\n")
                        
                         # Show key attributes
                        attrs = ", ".join([f"{k}='{v}'" for k, v in el['attributes'].items() 
                                        if k in ['id', 'class', 'data-testid', 'aria-label', 'type']])
                        if attrs:
                            f.write(f"- Attributes: {attrs}\n")
                        f.write("\n")
            else:
                f.write("No send button selectors found.\n\n")
            
            # Write complete updated selectors using explicit strings to avoid escaping issues
            f.write("## Complete Updated CLAUDE_SELECTORS\n\n")
            f.write("```python\n")
            f.write("# Updated Claude.ai web interface selectors\n")
            f.write("CLAUDE_SELECTORS = {\n")
            f.write("    # Login and authentication\n")
            f.write("    'login_button': 'button:has-text(\"Log in\")',\n")
            
            # For each selector, use string concatenation instead of f-strings with escapes
            logged_in = best_selectors.get('new_chat_button', '[data-testid="new-chat"]')
            f.write("    'logged_in_indicator': '" + logged_in + "',\n")
            
            f.write("\n    # Chat interface\n")
            new_chat = best_selectors.get('new_chat_button', '[data-testid="new-chat"]')
            f.write("    'new_chat_button': '" + new_chat + "',\n")
            
            textarea = best_selectors.get('prompt_textarea', '[data-testid="chat-input-box"]')
            f.write("    'prompt_textarea': '" + textarea + "',\n")
            
            send = best_selectors.get('send_button', '[data-testid="send-message-button"]')
            f.write("    'send_button': '" + send + "',\n")
            
            f.write("    'response_container': '[data-message-author-role=\"assistant\"]',\n")
            f.write("    'thinking_indicator': '[data-testid=\"conversation-turn-loading\"]',\n")
            
            f.write("\n    # File upload\n")
            upload = best_selectors.get('upload_button', '[data-testid="image-upload-button"]')
            f.write("    'upload_button': '" + upload + "',\n")
            
            file_input = best_selectors.get('file_input', 'input[type="file"]')
            f.write("    'file_input': '" + file_input + "',\n")
            
            f.write("    'image_preview': '[data-testid=\"image-preview\"]',\n")
            
            f.write("\n    # Chat management\n")
            f.write("    'chat_list': '[data-testid=\"conversations-list-content\"]',\n")
            f.write("    'chat_item': '[data-testid=\"conversation-item\"]',\n")
            f.write("    'delete_chat_button': '[data-testid=\"delete-chat-button\"]',\n")
            f.write("    'confirm_delete_button': '[data-testid=\"confirm-delete-button\"]',\n")
            
            f.write("\n    # Settings\n")
            f.write("    'settings_button': '[data-testid=\"settings-button\"]',\n")
            f.write("    'account_settings': '[data-testid=\"account-settings\"]',\n")
            f.write("    'model_selector': '[data-testid=\"model-selector\"]'\n")
            f.write("}\n")
            f.write("```\n")
        
        print(f"Selector analysis complete. Results saved to {output_file}")
        print("\nBest selectors found:")
        for key, selector in best_selectors.items():
            if selector:
                print(f"- {key}: {selector}")
            else:
                print(f"- {key}: Not found")
        
        return {
            'best_selectors': best_selectors,
            'all_selectors': selector_data
        }
        
    except Exception as e:
        print(f"Error analyzing page selectors: {str(e)}")
        # Try to write error to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# ERROR: {str(e)}\n")
                f.write("Failed to analyze Claude UI selectors.")
        except:
            pass
        
        return {
            'error': str(e)
        }
def analyze_page_structure(driver, filename="page_structure_analysis.txt"):
    """分析页面结构并保存元素信息到文件"""
    try:
        # 使用JavaScript分析页面结构
        js_script = """
        function analyzePageStructure() {
            // 存储分析结果
            let analysis = {
                tagCounts: {},
                classCounts: {},
                idCounts: {},
                messageElements: [],
                codeBlocks: [],
                sampleTexts: [],
                documentSections: []
            };
            
            // 分析所有元素
            function analyzeElement(element, depth = 0) {
                // 记录标签类型
                const tagName = element.tagName.toLowerCase();
                analysis.tagCounts[tagName] = (analysis.tagCounts[tagName] || 0) + 1;
                
                // 记录类名
                if (element.className && typeof element.className === 'string') {
                    const classes = element.className.split(/\\s+/);
                    classes.forEach(cls => {
                        if (cls) {
                            analysis.classCounts[cls] = (analysis.classCounts[cls] || 0) + 1;
                        }
                    });
                }
                
                // 记录ID
                if (element.id) {
                    analysis.idCounts[element.id] = (analysis.idCounts[element.id] || 0) + 1;
                }
                
                // 检查是否可能是消息元素
                const text = element.textContent.trim();
                if (text.length > 10 && depth < 5) {
                    const rect = element.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 30) {
                        // 检查内容是否看起来像消息
                        const isPossibleMessage = 
                            (element.tagName === 'DIV' || element.tagName === 'P') &&
                            text.length < 1000 &&
                            !element.querySelector('pre') && // 不包含代码块
                            !element.classList.contains('header') &&
                            !element.classList.contains('footer') &&
                            !element.id.includes('header') &&
                            !element.id.includes('footer');
                        
                        if (isPossibleMessage) {
                            analysis.messageElements.push({
                                tag: tagName,
                                id: element.id || '',
                                classes: element.className || '',
                                text: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
                                path: getElementPath(element),
                                rectangle: {
                                    top: rect.top,
                                    left: rect.left,
                                    width: rect.width,
                                    height: rect.height
                                }
                            });
                        }
                        
                        // 采样一些文本内容
                        if (analysis.sampleTexts.length < 20 && text.length > 20) {
                            analysis.sampleTexts.push({
                                tag: tagName,
                                id: element.id || '',
                                classes: element.className || '',
                                text: text.substring(0, 150) + (text.length > 150 ? '...' : ''),
                                path: getElementPath(element)
                            });
                        }
                    }
                }
                
                // 检查是否是代码块
                if (tagName === 'pre' || tagName === 'code' || element.classList.contains('code-block')) {
                    analysis.codeBlocks.push({
                        tag: tagName,
                        id: element.id || '',
                        classes: element.className || '',
                        text: element.textContent.substring(0, 200) + (element.textContent.length > 200 ? '...' : ''),
                        path: getElementPath(element)
                    });
                }
                
                // 检查是否是文档部分
                if (element.classList.contains('document') || 
                    element.id.includes('document') || 
                    tagName === 'article' ||
                    element.classList.contains('sidebar-content')) {
                    analysis.documentSections.push({
                        tag: tagName,
                        id: element.id || '',
                        classes: element.className || '',
                        text: element.textContent.substring(0, 200) + (element.textContent.length > 200 ? '...' : ''),
                        path: getElementPath(element),
                        childElements: Array.from(element.children).map(child => ({
                            tag: child.tagName.toLowerCase(),
                            classes: child.className || '',
                            text: child.textContent.trim().substring(0, 100) + (child.textContent.length > 100 ? '...' : '')
                        }))
                    });
                }
                
                // 递归分析子元素
                for (const child of element.children) {
                    analyzeElement(child, depth + 1);
                }
            }
            
            // 获取元素的CSS选择器路径
            function getElementPath(element) {
                if (!element || element === document.body) return 'body';
                
                let path = '';
                let current = element;
                
                while (current && current !== document.body) {
                    let selector = current.tagName.toLowerCase();
                    
                    if (current.id) {
                        selector += '#' + current.id;
                    } else if (current.className && typeof current.className === 'string') {
                        selector += '.' + current.className.trim().replace(/\\s+/g, '.');
                    }
                    
                    path = selector + (path ? ' > ' + path : '');
                    current = current.parentElement;
                }
                
                return path;
            }
            
            // 特别分析可能的对话结构
            function analyzeConversationStructure() {
                // 尝试不同的选择器来找到消息容器
                const selectors = [
                    '.conversation', '.chat', '.messages', '.message-container',
                    'main', 'article', '.content', '[role="main"]'
                ];
                
                let messageContainer = null;
                
                for (const selector of selectors) {
                    const container = document.querySelector(selector);
                    if (container) {
                        messageContainer = container;
                        break;
                    }
                }
                
                if (!messageContainer) {
                    // 如果没有找到明确的容器，尝试基于结构推断
                    const elements = document.querySelectorAll('div > div > div');
                    for (const el of elements) {
                        const children = el.children;
                        if (children.length > 3) {
                            // 可能是一个消息列表
                            messageContainer = el;
                            break;
                        }
                    }
                }
                
                if (messageContainer) {
                    analysis.messageContainer = {
                        tag: messageContainer.tagName.toLowerCase(),
                        id: messageContainer.id || '',
                        classes: messageContainer.className || '',
                        path: getElementPath(messageContainer),
                        childCount: messageContainer.children.length
                    };
                    
                    // 分析子元素
                    const children = Array.from(messageContainer.children);
                    analysis.conversationElements = children.map(child => ({
                        tag: child.tagName.toLowerCase(),
                        id: child.id || '',
                        classes: child.className || '',
                        text: child.textContent.trim().substring(0, 100) + (child.textContent.length > 100 ? '...' : ''),
                        path: getElementPath(child),
                        rect: {
                            top: child.getBoundingClientRect().top,
                            height: child.getBoundingClientRect().height
                        }
                    }));
                }
            }
            
            // 查找代码示例和其解释
            function findCodeAndExplanations() {
                const codeElements = document.querySelectorAll('pre, code, .code-block');
                
                analysis.codeWithExplanations = [];
                
                codeElements.forEach(codeEl => {
                    // 查找前后的解释文本
                    let explanation = '';
                    let prevSibling = codeEl.previousElementSibling;
                    let nextSibling = codeEl.nextElementSibling;
                    
                    // 检查前一个兄弟元素
                    if (prevSibling && !prevSibling.tagName.match(/^(pre|code)$/i)) {
                        explanation += "前置解释: " + prevSibling.textContent.trim() + "\\n";
                    }
                    
                    // 检查后一个兄弟元素
                    if (nextSibling && !nextSibling.tagName.match(/^(pre|code)$/i)) {
                        explanation += "后置解释: " + nextSibling.textContent.trim();
                    }
                    
                    // 检查列表元素（可能是使用说明）
                    let listElement = codeEl.nextElementSibling;
                    while (listElement) {
                        if (listElement.tagName === 'OL' || listElement.tagName === 'UL') {
                            explanation += "\\n列表说明:\\n" + listElement.textContent.trim();
                            break;
                        }
                        listElement = listElement.nextElementSibling;
                    }
                    
                    analysis.codeWithExplanations.push({
                        code: {
                            tag: codeEl.tagName.toLowerCase(),
                            id: codeEl.id || '',
                            classes: codeEl.className || '',
                            text: codeEl.textContent.substring(0, 150) + (codeEl.textContent.length > 150 ? '...' : ''),
                            path: getElementPath(codeEl)
                        },
                        explanation: explanation
                    });
                });
            }
            
            // 分析按钮和互动元素
            function analyzeInteractiveElements() {
                const buttons = document.querySelectorAll('button, [role="button"], .button');
                
                analysis.interactiveElements = Array.from(buttons).map(button => ({
                    tag: button.tagName.toLowerCase(),
                    id: button.id || '',
                    classes: button.className || '',
                    text: button.textContent.trim(),
                    path: getElementPath(button)
                }));
            }
            
            // 开始分析
            analyzeElement(document.body);
            analyzeConversationStructure();
            findCodeAndExplanations();
            analyzeInteractiveElements();
            
            return analysis;
        }
        
        return analyzePageStructure();
        """
        
        analysis_data = driver.execute_script(js_script)
        
        # 保存分析结果到文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Claude页面结构分析\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("常见标签统计:\n")
            f.write("=" * 80 + "\n\n")
            
            for tag, count in sorted(analysis_data['tagCounts'].items(), key=lambda x: x[1], reverse=True):
                f.write(f"{tag}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("常见类名统计:\n")
            f.write("=" * 80 + "\n\n")
            
            for cls, count in sorted(analysis_data['classCounts'].items(), key=lambda x: x[1], reverse=True)[:50]:
                f.write(f"{cls}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("ID统计:\n")
            f.write("=" * 80 + "\n\n")
            
            for id_name, count in sorted(analysis_data['idCounts'].items(), key=lambda x: x[1], reverse=True)[:50]:
                f.write(f"{id_name}: {count}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("可能的消息元素:\n")
            f.write("=" * 80 + "\n\n")
            
            for msg_element in analysis_data['messageElements']:
                f.write(f"标签: {msg_element['tag']}\n")
                f.write(f"ID: {msg_element['id']}\n")
                f.write(f"类名: {msg_element['classes']}\n")
                f.write(f"路径: {msg_element['path']}\n")
                f.write(f"位置: 上={msg_element['rectangle']['top']}, 左={msg_element['rectangle']['left']}, 宽={msg_element['rectangle']['width']}, 高={msg_element['rectangle']['height']}\n")
                f.write(f"文本: {msg_element['text']}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("代码块:\n")
            f.write("=" * 80 + "\n\n")
            
            for code_block in analysis_data['codeBlocks']:
                f.write(f"标签: {code_block['tag']}\n")
                f.write(f"ID: {code_block['id']}\n")
                f.write(f"类名: {code_block['classes']}\n")
                f.write(f"路径: {code_block['path']}\n")
                f.write(f"代码示例: {code_block['text']}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("代码与解释:\n")
            f.write("=" * 80 + "\n\n")
            
            for item in analysis_data['codeWithExplanations']:
                f.write(f"代码路径: {item['code']['path']}\n")
                f.write(f"代码示例: {item['code']['text']}\n")
                if item['explanation']:
                    f.write(f"相关解释: {item['explanation']}\n")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("文档部分:\n")
            f.write("=" * 80 + "\n\n")
            
            for doc in analysis_data['documentSections']:
                f.write(f"标签: {doc['tag']}\n")
                f.write(f"ID: {doc['id']}\n")
                f.write(f"类名: {doc['classes']}\n")
                f.write(f"路径: {doc['path']}\n")
                f.write(f"文本示例: {doc['text']}\n")
                f.write("子元素:\n")
                for child in doc['childElements']:
                    f.write(f"  - {child['tag']} ({child['classes']}): {child['text']}\n")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("交互元素:\n")
            f.write("=" * 80 + "\n\n")
            
            for button in analysis_data['interactiveElements']:
                f.write(f"标签: {button['tag']}\n")
                f.write(f"ID: {button['id']}\n")
                f.write(f"类名: {button['classes']}\n")
                f.write(f"路径: {button['path']}\n")
                f.write(f"文本: {button['text']}\n\n")
            
            # 写入对话结构分析
            if 'messageContainer' in analysis_data:
                f.write("\n" + "=" * 80 + "\n")
                f.write("对话容器:\n")
                f.write("=" * 80 + "\n\n")
                
                container = analysis_data['messageContainer']
                f.write(f"标签: {container['tag']}\n")
                f.write(f"ID: {container['id']}\n")
                f.write(f"类名: {container['classes']}\n")
                f.write(f"路径: {container['path']}\n")
                f.write(f"子元素数量: {container['childCount']}\n\n")
                
                f.write("对话元素:\n")
                for i, elem in enumerate(analysis_data.get('conversationElements', [])):
                    f.write(f"元素 {i+1}:\n")
                    f.write(f"  标签: {elem['tag']}\n")
                    f.write(f"  ID: {elem['id']}\n")
                    f.write(f"  类名: {elem['classes']}\n")
                    f.write(f"  路径: {elem['path']}\n")
                    f.write(f"  位置: 上={elem['rect']['top']}, 高={elem['rect']['height']}\n")
                    f.write(f"  文本: {elem['text']}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("文本样本:\n")
            f.write("=" * 80 + "\n\n")
            
            for i, sample in enumerate(analysis_data['sampleTexts']):
                f.write(f"样本 {i+1}:\n")
                f.write(f"标签: {sample['tag']}\n")
                f.write(f"ID: {sample['id']}\n")
                f.write(f"类名: {sample['classes']}\n")
                f.write(f"路径: {sample['path']}\n")
                f.write(f"文本: {sample['text']}\n\n")
        
        print(f"页面结构分析已保存到 {filename}")
        return analysis_data
    
    except Exception as e:
        print(f"分析页面结构时出错: {str(e)}")
        return None

def extract_page_content(driver, filename="page_content.txt"):
    """提取页面的完整文本内容并保存到文件，保留格式并区分生成内容与UI元素"""
    try:
        # 获取页面标题
        title = driver.title
        
        # 使用JavaScript提取内容并保留格式
        js_script = """
        function getFormattedContent() {
            // 存储内容
            let content = {
                conversationTurns: [],
                uiElements: []
            };
            
            // 更可靠的方式查找对话区域
            const mainContentArea = document.querySelector('div.flex-1.flex.flex-col.gap-3');
            if (!mainContentArea) {
                return { error: "无法找到主要内容区域" };
            }
            
            // 获取所有直接子元素，它们应该是对话轮次
            const conversationElements = Array.from(mainContentArea.children);
            
            // 初始化变量来跟踪当前的对话轮次
            let currentTurn = null;
            
            for (const element of conversationElements) {
                // 检查元素是否包含用户查询（通常有特定的背景色）
                const isUserQuery = element.querySelector('.bg-bg-300');
                
                if (isUserQuery) {
                    // 如果有之前的轮次，将其添加到结果中
                    if (currentTurn) {
                        content.conversationTurns.push(currentTurn);
                    }
                    
                    // 提取用户查询文本，排除可能的编辑按钮
                    let queryText = isUserQuery.textContent.trim();
                    queryText = queryText.replace(/Edit$/, '').trim();
                    
                    // 移除用户名前缀（例如："E")
                    queryText = queryText.replace(/^[A-Z]\\s*/, '');
                    
                    // 创建新的对话轮次
                    currentTurn = {
                        query: queryText,
                        responses: [],
                        codeBlocks: [],
                        documents: [],
                        codeExplanations: []
                    };
                } else {
                    // 如果没有当前轮次，跳过
                    if (!currentTurn) continue;
                    
                    // 检查是否是 Claude 的回复（通常有特定的样式特征）
                    const hasResponseContent = element.querySelector('.font-claude-message') || 
                                              element.querySelector('[class*="tracking"]');
                    
                    if (hasResponseContent) {
                        // 处理回复内容
                        
                        // 1. 查找代码块
                        const codeBlocks = element.querySelectorAll('pre');
                        for (const codeBlock of codeBlocks) {
                            // 获取代码语言
                            let language = '';
                            const codeElement = codeBlock.querySelector('code');
                            if (codeElement && codeElement.className) {
                                const match = codeElement.className.match(/language-([a-zA-Z0-9]+)/);
                                if (match) {
                                    language = match[1];
                                }
                            }
                            
                            // 获取代码文本
                            let codeText = codeBlock.textContent || "";
                            
                            // 移除"Copy"和语言标识
                            codeText = codeText.replace(/^(python|javascript|html|css|json)\\s*Copy\\s*/i, '');
                            
                            // 将代码块添加到当前轮次
                            if (codeText.trim()) {
                                currentTurn.codeBlocks.push({
                                    language: language || 'python', // 默认为python
                                    code: codeText
                                });
                            }
                        }
                        
                        // 2. 查找文档引用
                        const docButtons = element.querySelectorAll('button[class*="font-styrene"][class*="border-0"]');
                        for (const docButton of docButtons) {
                            // 提取文档标题
                            const docTitle = docButton.textContent.replace(/Click to open document.*$/, '').trim();
                            
                            // 尝试找到文档内容
                            let docContent = [];
                            
                            // 检查页面上是否有侧边栏，其中可能包含文档内容
                            const sidebarContent = document.querySelector('div[class*="fixed"][class*="right-0"][class*="flex"][class*="w-full"]');
                            if (sidebarContent) {
                                // 从侧边栏中提取段落
                                const docTextElements = sidebarContent.querySelectorAll('p');
                                for (const textEl of docTextElements) {
                                    docContent.push(textEl.textContent.trim());
                                }
                            }
                            
                            // 添加文档到当前轮次
                            if (docTitle) {
                                currentTurn.documents.push({
                                    title: docTitle,
                                    content: docContent
                                });
                            }
                        }
                        
                        // 3. 提取代码说明和使用说明 - 改进的捕获方式
                        let codeExplanations = [];
                        
                        // 整个响应元素作为容器，查找所有可能的说明文本
                        const allExplanationTexts = [];
                        
                        // 查找所有列表（有序和无序）
                        const listItems = element.querySelectorAll('ol li, ul li');
                        for (const item of listItems) {
                            // 检查不在代码块内
                            if (!item.closest('pre')) {
                                allExplanationTexts.push(item.textContent.trim());
                            }
                        }
                        
                        // 如果找到列表项，添加为代码说明
                        if (listItems.length > 0) {
                            const orderedLists = element.querySelectorAll('ol');
                            for (const list of orderedLists) {
                                // 检查不在代码块内
                                if (!list.closest('pre')) {
                                    codeExplanations.push(list.textContent.trim());
                                }
                            }
                            
                            const unorderedLists = element.querySelectorAll('ul');
                            for (const list of unorderedLists) {
                                // 检查不在代码块内
                                if (!list.closest('pre')) {
                                    codeExplanations.push(list.textContent.trim());
                                }
                            }
                        }
                        
                        // 查找可能包含使用说明的段落和div
                        const explanationParagraphs = element.querySelectorAll('p, div');
                        for (const para of explanationParagraphs) {
                            const text = para.textContent.trim();
                            
                            // 特定关键词的段落，如果不在代码块中
                            if ((text.includes('To use this code') || 
                                text.includes('Install') || 
                                text.includes('Set your API') || 
                                text.includes('Run the script') ||
                                text.includes('adjust parameters') ||
                                text.includes('This demo shows')) && 
                                !para.closest('pre') && 
                                !para.querySelector('pre') &&
                                !text.includes('Claude can make mistakes')) {
                                
                                // 排除已经添加的（避免重复）
                                if (!codeExplanations.includes(text)) {
                                    codeExplanations.push(text);
                                }
                            }
                        }
                        
                        // 添加到当前轮次
                        currentTurn.codeExplanations = codeExplanations;
                        
                        // 4. 更全面地捕获说明文本
                        // 创建一个临时的容器来保存所有内容，过滤掉代码区域
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = element.innerHTML;
                        
                        // 移除所有代码块，以便我们可以获取剩余文本
                        const codeToRemove = tempDiv.querySelectorAll('pre');
                        for (const code of codeToRemove) {
                            if (code.parentNode) {
                                code.parentNode.removeChild(code);
                            }
                        }
                        
                        // 查找特定的段落文本模式
                        const remainingText = tempDiv.textContent;
                        const usageMatch = remainingText.match(/To use this code:([\\s\\S]*?)(?=\\n\\n|$)/);
                        if (usageMatch && usageMatch[1]) {
                            const usageText = usageMatch[1].trim();
                            if (usageText && !codeExplanations.includes(usageText)) {
                                codeExplanations.push("To use this code:" + usageText);
                            }
                        }
                        
                        // 查找其他关键说明段落
                        const demoMatch = remainingText.match(/This demo shows([\\s\\S]*?)(?=\\n\\n|$)/);
                        if (demoMatch && demoMatch[0]) {
                            const demoText = demoMatch[0].trim();
                            if (demoText && !codeExplanations.includes(demoText)) {
                                codeExplanations.push(demoText);
                            }
                        }
                        
                        // 5. 提取回复文本（排除代码块、按钮和已捕获的说明）
                        let responseText = '';
                        
                        // 查找所有段落元素
                        const allParagraphs = element.querySelectorAll('p');
                        for (const para of allParagraphs) {
                            // 排除代码块内的段落、文档引用按钮内的文本和明显的说明文本
                            const paraText = para.textContent.trim();
                            if (!para.closest('pre') && 
                                !para.closest('button') && 
                                !paraText.includes('To use this code') &&
                                !paraText.includes('This demo shows') &&
                                !paraText.includes('Claude can make mistakes')) {
                                
                                responseText += paraText + '\\n\\n';
                            }
                        }
                        
                        // 如果没有找到段落元素或文本为空，尝试从主元素提取
                        if (!responseText.trim()) {
                            // 复制内容
                            const tempTextDiv = document.createElement('div');
                            tempTextDiv.innerHTML = element.innerHTML;
                            
                            // 移除代码块、按钮和其他UI元素
                            const elementsToRemove = [
                                ...tempTextDiv.querySelectorAll('pre'),
                                ...tempTextDiv.querySelectorAll('button'),
                                ...tempTextDiv.querySelectorAll('ol'),
                                ...tempTextDiv.querySelectorAll('ul')
                            ];
                            
                            for (const el of elementsToRemove) {
                                if (el.parentNode) {
                                    el.parentNode.removeChild(el);
                                }
                            }
                            
                            // 移除UI元素文本
                            responseText = tempTextDiv.textContent.trim()
                                .replace(/Retry/g, '')
                                .replace(/Copy/g, '')
                                .replace(/Edit/g, '')
                                .replace(/Claude can make mistakes. Please double-check responses./g, '')
                                .trim();
                        }
                        
                        // 移除多余的空行
                        responseText = responseText.replace(/\\n{3,}/g, '\\n\\n');
                        
                        // 添加到当前轮次的回复
                        if (responseText.trim()) {
                            currentTurn.responses.push(responseText);
                        }
                    }
                }
            }
            
            // 添加最后一个轮次（如果有）
            if (currentTurn) {
                content.conversationTurns.push(currentTurn);
            }
            
            // 收集页面头部信息作为UI元素
            const headerElement = document.querySelector('header');
            if (headerElement) {
                content.uiElements.push({
                    type: 'header',
                    text: headerElement.textContent.trim()
                });
            }
            
            // 收集页面底部的免责声明
            const disclaimerElement = document.querySelector('div[class*="Claude can make mistakes"]');
            if (disclaimerElement) {
                content.uiElements.push({
                    type: 'disclaimer',
                    text: disclaimerElement.textContent.trim()
                });
            }
            
            return content;
        }
        
        return getFormattedContent();
        """
        
        content_data = driver.execute_script(js_script)
        
        # 检查是否有错误
        if isinstance(content_data, dict) and 'error' in content_data:
            print(f"JavaScript执行错误: {content_data['error']}")
            return None
        
        # 保存结构化内容到文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"页面标题: {title}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("对话内容:\n")
            f.write("=" * 80 + "\n\n")
            
            # 写入对话轮次
            for i, turn in enumerate(content_data['conversationTurns']):
                f.write(f"轮次 {i+1}:\n")
                f.write(f"用户查询: {turn['query']}\n\n")
                
                f.write("Claude回复:\n")
                for response in turn['responses']:
                    f.write(f"{response}\n\n")
                
                # 写入文档内容
                for j, doc in enumerate(turn['documents']):
                    f.write(f"文档 {j+1}: {doc['title']}\n")
                    for content in doc['content']:
                        f.write(f"{content}\n")
                    f.write("\n")
                
                # 写入代码块
                for j, code_block in enumerate(turn['codeBlocks']):
                    f.write(f"代码块 {j+1}")
                    if code_block['language']:
                        f.write(f" ({code_block['language']}):\n")
                    else:
                        f.write(":\n")
                    
                    # 保留原始格式写入代码
                    f.write(f"{code_block['code']}\n\n")
                
                # 写入代码说明
                if turn['codeExplanations'] and len(turn['codeExplanations']) > 0:
                    f.write("代码说明:\n")
                    for explanation in turn['codeExplanations']:
                        f.write(f"{explanation}\n\n")
                
                f.write("-" * 80 + "\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("UI元素（页面固有内容）:\n")
            f.write("=" * 80 + "\n\n")
            
            # 写入UI元素
            for i, element in enumerate(content_data['uiElements']):
                f.write(f"UI元素 {i+1} ({element['type']}):\n{element['text']}\n\n")
        
        # 保存结构化内容为JSON
        json_filename = filename.rsplit('.', 1)[0] + '.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            import json
            json.dump(content_data, f, ensure_ascii=False, indent=2)
        
        print(f"页面内容已保存到 {filename}")
        print(f"结构化内容已保存到 {json_filename}")
        
        return content_data
    
    except Exception as e:
        print(f"提取页面内容时出错: {str(e)}")
        return None

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
        # Always include interactive elements (isInteractive = True)
        if el.get('isInteractive'):
            essential_el = {
                'tag': el['tag'],
                'text': el['text'].strip() if el.get('text') else '',
                'directText': el['directText'].strip() if el.get('directText') else '',
                'selector': el['selector'],
                'selectorType': el['selectorType'],
                'isInteractive': True,
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
            
        # Form elements (keeping this condition in case there are form elements with isInteractive=False)
        elif el.get('isFormElement'):
            essential_el = {
                'tag': el['tag'],
                'text': el['text'].strip() if el.get('text') else '',
                'directText': el['directText'].strip() if el.get('directText') else '',
                'selector': el['selector'],
                'selectorType': el['selectorType'],
                'isInteractive': False,
                'isFormElement': True
            }
            
            # Include only essential attributes
            if 'attributes' in el:
                essential_el['attributes'] = {k: v for k, v in el['attributes'].items() 
                                             if k in ['id', 'name', 'type', 'placeholder', 'title', 'data-id', 'data-name']}
            
            # Include cursor style as it's important for interactivity
            if 'keyStyles' in el and 'cursor' in el['keyStyles']:
                essential_el['cursor'] = el['keyStyles']['cursor']
                
            essential_elements.append(essential_el)
            
        # Also include elements with significant text (keeping this condition if you still want text elements)
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
    #url = input("Enter URL to analyze (or press Enter to analyze current page): ")
    url=False
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "localhost:54805")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Initialize Chrome driver
    try:
        # Try to use local ChromeDriver first
        driver = webdriver.Chrome(service=Service('/usr/local/bin/chromedriver'), options=chrome_options)
        #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
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
        print("\n提取单页应用内容，包括内部标签页...")
        #extract_spa_content(driver, output_dir)
        # 提取页面内容
        print("\n提取页面文本内容...")
        content_file = os.path.join(output_dir, "page_content.txt")
        extract_page_content(driver, content_file)
        structure_content_file = os.path.join(output_dir, "page_structure_analysis.txt")
        analyze_page_structure(driver, structure_content_file)
        selectors_content_file = os.path.join(output_dir, "claude_selectors.txt")
        analyze_claude_selectors(driver, selectors_content_file)
        # 提取结构化内容
        print("\n提取页面结构化内容...")
        structured_file = os.path.join(output_dir, "structured_content.json")
        extract_structured_content(driver, structured_file)
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
        #driver.quit()

if __name__ == "__main__":
    main()        # Generate utility methods
