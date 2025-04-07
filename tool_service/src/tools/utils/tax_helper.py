# tool_service/src/tools/utils/tax_helper.py
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse
from .dom_parser import DOMParser
from browser_use.dom.service import DomService
from browser_use.utils import time_execution_sync
logger = logging.getLogger(__name__)

class TaxHelper:
    """
    税务操作辅助工具，提供更高级的页面交互和数据处理功能
    """
    
    def __init__(self, session):
        """
        初始化辅助工具
        
        Args:
            session: 浏览器会话对象
        """
        self.session = session
        self.dom_parser = DOMParser
    
    async def navigate_with_retry(self, url, max_retries=3, retry_delay=2):
        """
        带重试机制的页面导航
        
        Args:
            url: 要导航的URL
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            是否导航成功
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"导航到 {url}，尝试次数: {attempt + 1}/{max_retries}")
                await self.session.goto(url)
                
                # 等待页面加载
                await asyncio.sleep(retry_delay)
                
                # 检查页面是否成功加载
                location = await self.session.execute_script("return window.location.href")
                if location:
                    target_domain = urlparse(url).netloc
                    current_domain = urlparse(location).netloc
                    
                    if target_domain and current_domain and target_domain in current_domain:
                        logger.info(f"成功导航到 {location}")
                        return True
                else:
                    logger.warning(f"导航未到达目标URL。当前URL: {location}，目标URL: {url}")
            except Exception as e:
                logger.error(f"导航失败: {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        
        logger.error(f"导航到 {url} 失败，已达最大重试次数")
        return False
    
    async def find_and_click_element(self, text=None, selector=None, exact_match=False, wait_time=2, max_attempts=3):
        """
        查找并点击页面元素
        
        Args:
            text: 要查找的文本
            selector: 要查找的选择器
            exact_match: 是否精确匹配文本
            wait_time: 点击后等待时间
            max_attempts: 最大尝试次数
            
        Returns:
            是否成功点击
        """
        pass
    
    async def get_selector_map(self):
        context = await self.session.get_browser_use_context()
        page = await context.get_current_page()
        dom_service = DomService(page)
        # First get all elements
        print('\nGetting all elements:')
        all_elements_state = await time_execution_sync('get_all_elements')(dom_service.get_clickable_elements)(
            highlight_elements=True, viewport_expansion=100
        )
        selector_map = all_elements_state.selector_map
        total_elements = len(selector_map.keys())
        print(selector_map)
        print(f'Total number of elements: {total_elements}')
        return selector_map
    
    async def fill_input(self, value, selector=None, placeholder=None, label=None, wait_time=1):
        """
        填充输入框
        
        Args:
            value: 要填充的值
            selector: 输入框选择器
            placeholder: 输入框占位符文本
            label: 输入框标签文本
            wait_time: 操作后等待时间
            
        Returns:
            是否成功填充
        """
        try:
            input_selector = selector
            
            # 如果没有提供选择器，尝试通过占位符或标签查找
            if not input_selector and (placeholder or label):
                js_script = f"""
                () => {{
                    let input = null;
                    
                    // 通过占位符查找
                    if ({repr(placeholder)}) {{
                        input = Array.from(document.querySelectorAll('input, textarea')).find(el => 
                            el.placeholder && el.placeholder.includes({repr(placeholder)})
                        );
                    }}
                    
                    // 通过标签查找
                    if (!input && {repr(label)}) {{
                        // 先查找标签元素
                        const labels = Array.from(document.querySelectorAll('label')).filter(el => 
                            el.textContent.includes({repr(label)})
                        );
                        
                        // 查找关联的输入框
                        for (const labelEl of labels) {{
                            // 如果标签有for属性
                            if (labelEl.htmlFor) {{
                                input = document.getElementById(labelEl.htmlFor);
                                if (input) break;
                            }}
                            
                            // 查找标签内或标签后的输入框
                            input = labelEl.querySelector('input, textarea') || 
                                   labelEl.nextElementSibling?.querySelector('input, textarea') ||
                                   labelEl.nextElementSibling;
                                   
                            if (input && (input.tagName === 'INPUT' || input.tagName === 'TEXTAREA')) break;
                        }}
                    }}
                    
                    return input ? {{
                        id: input.id,
                        name: input.name,
                        className: input.className,
                        type: input.type
                    }} : null;
                }}
                """
                
                input_element = await self.session.execute_script(js_script)
                if input_element:
                    # 构建一个更好的选择器
                    if input_element.get('id'):
                        input_selector = f"#{input_element['id']}"
                    elif input_element.get('name'):
                        input_selector = f"input[name='{input_element['name']}'], textarea[name='{input_element['name']}']"
                    elif input_element.get('className'):
                        classes = input_element['className'].split()
                        if classes:
                            input_selector = f".{classes[0]}"
            
            if input_selector:
                # 填充输入框
                fill_script = f"""
                () => {{
                    try {{
                        const input = document.querySelector("{input_selector}");
                        if (!input) return false;
                        
                        // 聚焦元素
                        input.focus();
                        
                        // 清除现有值
                        input.value = '';
                        
                        // 设置新值
                        input.value = {repr(value)};
                        
                        // 触发事件
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        return true;
                    }} catch (e) {{
                        console.error('填充输入框失败:', e);
                        return false;
                    }}
                }}
                """
                
                filled = await self.session.evaluate(fill_script)
                if filled:
                    logger.info(f"成功填充输入框 {input_selector} 为: {value}")
                    await asyncio.sleep(wait_time)
                    return True
                else:
                    logger.warning(f"找到输入框，但填充失败: {input_selector}")
            else:
                logger.warning("未找到匹配的输入框")
            
            return False
        except Exception as e:
            logger.error(f"填充输入框失败: {str(e)}")
            return False
    
    async def wait_for_element(self, selector=None, text=None, timeout=30, check_interval=1):
        """
        等待元素出现
        
        Args:
            selector: 元素选择器
            text: 元素包含的文本
            timeout: 超时时间(秒)
            check_interval: 检查间隔(秒)
            
        Returns:
            是否等待成功
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if selector:
                    element = await self.session.query_selector(selector)
                    if element:
                        logger.info(f"元素已出现: {selector}")
                        return True
                
                if text:
                    elements = await self.dom_parser.find_element_by_text(
                        self.session, text, exact_match=False, highlight=False
                    )
                    if elements and len(elements) > 0:
                        logger.info(f"包含文本 '{text}' 的元素已出现")
                        return True
                
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"等待元素时出错: {str(e)}")
                await asyncio.sleep(check_interval)
        
        logger.warning(f"等待元素超时: {selector or text}")
        return False
    
    async def get_selected_city(self):
        """
        获取当前选中的城市
        
        Returns:
            当前选中的城市名称
        """
        try:
            js_script = """
            () => {
                // 尝试查找城市选择器或城市显示区域
                const cityElements = [
                    document.querySelector('.city-selector .selected'),
                    document.querySelector('.city-name'),
                    document.querySelector('.current-city'),
                    ...Array.from(document.querySelectorAll('.region-item.active, .city-item.active')),
                    ...Array.from(document.querySelectorAll('[class*="city"][class*="selected"], [class*="city"][class*="active"]'))
                ].filter(Boolean);
                
                for (const el of cityElements) {
                    if (el && el.textContent.trim()) {
                        return el.textContent.trim();
                    }
                }
                
                return null;
            }
            """
            
            city = await self.session.execute_script(js_script)
            return city
        except Exception as e:
            logger.error(f"获取当前选中的城市失败: {str(e)}")
            return None
    
    async def get_login_status(self):
        """
        获取登录状态
        
        Returns:
            登录状态信息
        """
        try:
            js_script = """
            () => {
                // 查找可能的登录状态指示器
                const userInfo = document.querySelector('.user-info, .user-name, .welcome-text');
                if (userInfo) {
                    return {
                        isLoggedIn: true,
                        username: userInfo.textContent.trim()
                    };
                }
                
                // 检查登录按钮
                const loginButton = document.querySelector('.login-btn, [class*="login"]');
                if (loginButton) {
                    return {
                        isLoggedIn: false,
                        status: '未登录'
                    };
                }
                
                // 检查二维码
                const qrCode = document.querySelector('.qrcode, .qrcode-container, [class*="qrcode"]');
                if (qrCode) {
                    return {
                        isLoggedIn: false,
                        status: '等待扫码登录'
                    };
                }
                
                return {
                    isLoggedIn: false,
                    status: '未知状态'
                };
            }
            """
            
            status = await self.session.execute_script(js_script)
            return status
        except Exception as e:
            logger.error(f"获取登录状态失败: {str(e)}")
            return {'isLoggedIn': False, 'status': f'错误: {str(e)}'}
    
    async def extract_tax_records(self):
        """
        解析页面上的纳税记录
        
        Returns:
            纳税记录数据
        """
        pass
    
    async def set_date_range(self, start_date, end_date):
        """
        设置日期范围
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            是否成功设置
        """
        try:
            logger.info(f"设置日期范围: {start_date} 至 {end_date}")
            
            # 先获取日期输入框
            js_script = """
            () => {
                const dateInputs = Array.from(document.querySelectorAll('input[type="date"], input.el-input__inner, input.date-picker'));
                
                // 过滤可能的日期输入框
                const likelyDateInputs = dateInputs.filter(input => {
                    const label = input.labels?.[0]?.textContent || '';
                    const placeholder = input.placeholder || '';
                    const name = input.name || '';
                    const id = input.id || '';
                    const classes = input.className || '';
                    
                    return label.includes('日期') || 
                           placeholder.includes('日期') ||
                           name.includes('date') ||
                           id.includes('date') ||
                           classes.includes('date');
                });
                
                if (likelyDateInputs.length >= 2) {
                    return [
                        {
                            id: likelyDateInputs[0].id,
                            name: likelyDateInputs[0].name,
                            class: likelyDateInputs[0].className,
                            placeholder: likelyDateInputs[0].placeholder
                        },
                        {
                            id: likelyDateInputs[1].id,
                            name: likelyDateInputs[1].name,
                            class: likelyDateInputs[1].className,
                            placeholder: likelyDateInputs[1].placeholder
                        }
                    ];
                } else if (dateInputs.length >= 2) {
                    return [
                        {
                            id: dateInputs[0].id,
                            name: dateInputs[0].name,
                            class: dateInputs[0].className,
                            placeholder: dateInputs[0].placeholder
                        },
                        {
                            id: dateInputs[1].id,
                            name: dateInputs[1].name,
                            class: dateInputs[1].className,
                            placeholder: dateInputs[1].placeholder
                        }
                    ];
                }
                
                return null;
            }
            """
            
            date_inputs = await self.session.execute_script(js_script)
            
            if not date_inputs:
                logger.warning("未找到日期输入框")
                return False
            
            # 设置开始日期
            start_input_selector = None
            if date_inputs[0].get('id'):
                start_input_selector = f"#{date_inputs[0]['id']}"
            elif date_inputs[0].get('name'):
                start_input_selector = f"input[name='{date_inputs[0]['name']}']"
            elif date_inputs[0].get('class'):
                classes = date_inputs[0]['class'].split()
                if classes:
                    start_input_selector = f".{classes[0]}"
            
            if start_input_selector:
                start_date_set = await self.fill_input(start_date, selector=start_input_selector)
                if not start_date_set:
                    logger.warning(f"设置开始日期失败: {start_date}")
                    return False
            
            # 设置结束日期
            end_input_selector = None
            if date_inputs[1].get('id'):
                end_input_selector = f"#{date_inputs[1]['id']}"
            elif date_inputs[1].get('name'):
                end_input_selector = f"input[name='{date_inputs[1]['name']}']"
            elif date_inputs[1].get('class'):
                classes = date_inputs[1]['class'].split()
                if classes:
                    end_input_selector = f".{classes[0]}"
            
            if end_input_selector:
                end_date_set = await self.fill_input(end_date, selector=end_input_selector)
                if not end_date_set:
                    logger.warning(f"设置结束日期失败: {end_date}")
                    return False
            
            logger.info("日期范围设置成功")
            return True
        except Exception as e:
            logger.error(f"设置日期范围失败: {str(e)}")
            return False