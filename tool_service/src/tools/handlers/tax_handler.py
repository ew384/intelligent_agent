# tool_service/src/tools/handlers/tax_handler.py
from .base import BaseHandler
from typing import Dict, Any, Optional, List
import logging
import asyncio
import time
from urllib.parse import urljoin, urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from ..utils.dom_parser import DOMParser
from ..utils.tax_helper import TaxHelper
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class TaxHandler(BaseHandler):
    """
    电子税务局操作处理器
    职责:
    1. 提供税务局网站的各种操作功能
    2. 处理与税务相关的查询和操作
    3. 提供访问税务系统的通用接口
    """
    
    BASE_URL = "https://etax.chinatax.gov.cn/?dmnHafHu=4GaB4GlqEiwcKTTdRKqNSIrmPl6C4Fotuqtcf8HlZ3KBQv_qxzOqEcP8SmwFXbxbJSCPer3FLzftI0Zep6WcQqzaluxjqcxz"
    SHENZHEN_TAX_URL = "https://its.shenzhen.chinatax.gov.cn:4433/gkpt/#/taxChecklist"
    
    def __init__(self, session):
        """初始化处理器"""
        super().__init__(session)
        self.dom_parser = DOMParser
        self.helper = TaxHelper(session)
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理税务操作请求"""
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 业务逻辑路由
        action_map = {
            "check_login": self.check_tax_login,
            "navigate_to_main": self.navigate_to_main_page,
            "select_city": self.select_city,
            "navigate_to_tax_checklist": self.navigate_to_tax_checklist,
            "get_tax_records": self.get_tax_records,
            "query_tax_record": self.query_tax_record
        }
        
        # 调用具体的业务逻辑方法
        handler = action_map.get(action)
        if not handler:
            return {"status": "error", "message": f"未知的税务操作: {action}"}
        
        return await handler(parameters)
    
    async def check_tax_login(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查电子税务局是否已登录
        
        Args:
            parameters: 操作参数
                
        Returns:
            登录状态检查结果
        """
        try:
            service_id = parameters.get('service_id', 'tax_service')
            if not isinstance(service_id, str):
                service_id = str(service_id)
            logger.info("检查税务局登录状态")
            
            # 尝试加载之前保存的 cookies
            has_cookies = await self.session.load_cookies(service_id)
            
            # 如果有 cookies，刷新页面应用 cookies
            if has_cookies:
                logger.info("找到已保存的 cookies，刷新页面应用...")
                await self.session.refresh_page()
                
                # 等待页面加载完成
                await asyncio.sleep(3)
            
            # 获取登录状态
            login_status = await self.helper.get_login_status()
            is_logged_in = login_status.get('isLoggedIn', False)
            
            # 如果已登录，保存 cookies
            if is_logged_in:
                logger.info("税务局已登录，保存 cookies...")
                await self.session.save_cookies(service_id)
                
                return {
                    "status": "success",
                    "message": "税务局已登录",
                    "logged_in": True,
                    "user_info": login_status.get('username', '')
                }
            
            # 检查是否显示了二维码，表示需要登录
            # 使用DOM解析器查找二维码元素
            qr_code_elements = await self.dom_parser.find_element_by_selector(
                self.session, 
                ".qrcode, .qrcode-container, [class*='qrcode']"
            )
            
            if qr_code_elements:
                logger.info("检测到税务局登录二维码，等待用户扫码登录")
                
                # 开始检测登录状态变化
                if parameters.get('wait_for_login', False):
                    logger.info("等待用户扫码登录...")
                    
                    # 最大等待时间（默认5分钟）
                    max_wait_time = parameters.get('login_timeout', 300)
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait_time:
                        # 循环检查登录状态
                        login_status = await self.helper.get_login_status()
                        is_logged_in = login_status.get('isLoggedIn', False)
                        
                        if is_logged_in:
                            logger.info("检测到税务局已登录")
                            
                            # 保存 cookies
                            await self.session.save_cookies(service_id)
                            
                            return {
                                "status": "success",
                                "message": "税务局已登录",
                                "logged_in": True,
                                "user_info": login_status.get('username', '')
                            }
                        
                        # 等待一段时间再检查
                        await asyncio.sleep(3)
                    
                    # 超时
                    return {
                        "status": "pending",
                        "message": "等待登录超时，请再次扫码",
                        "logged_in": False
                    }
                
                return {
                    "status": "pending",
                    "message": "请使用税务局APP扫描二维码登录",
                    "logged_in": False
                }
            
            logger.warning("无法确定税务局登录状态")
            return {
                "status": "error",
                "message": "无法确定税务局登录状态",
                "logged_in": False
            }
            
        except Exception as e:
            logger.error(f"检查税务局登录状态失败: {str(e)}")
            return {
                "status": "error",
                "message": f"检查税务局登录状态失败: {str(e)}",
                "logged_in": False
            }
    
    async def navigate_to_main_page(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        导航到电子税务局主页
        
        Args:
            parameters: 操作参数
            
        Returns:
            导航结果
        """
        try:
            logger.info("导航到电子税务局主页")
            
            # 使用辅助工具的导航功能
            success = await self.helper.navigate_with_retry(self.BASE_URL)
            
            if not success:
                return {
                    "status": "error",
                    "message": "导航到电子税务局主页失败"
                }
            
            # 等待主页加载完成
            await self.helper.wait_for_element(".home-container, .main-container", timeout=30)
            
            logger.info("已成功导航到电子税务局主页")
            return {
                "status": "success",
                "message": "已成功导航到电子税务局主页"
            }
            
        except Exception as e:
            logger.error(f"导航到电子税务局主页失败: {str(e)}")
            return {
                "status": "error",
                "message": f"导航到电子税务局主页失败: {str(e)}"
            }
    
    async def select_city(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        选择城市（如深圳市）
        
        Args:
            parameters: 必须包含city字段，表示要选择的城市，例如"深圳市"
            
        Returns:
            选择结果
        """
        try:
            city = parameters.get('city', '深圳市')
            logger.info(f"正在选择城市: {city}")
            # 查找并选择指定城市
            selector_map=await self.helper.get_selector_map()
            """
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"selector_map.json"
            debug_dir = os.path.join(os.getcwd(), "debug_dom")
            os.makedirs(debug_dir, exist_ok=True)
            filepath = os.path.join(debug_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                        json.dump({
                            "timestamp": timestamp,
                            "selector_map": selector_map
                        }, f, ensure_ascii=False, indent=2)"""
            return {}
        except Exception as e:
            logger.error(f"选择城市失败: {str(e)}")
            return {
                "status": "error",
                "message": f"选择城市失败: {str(e)}"
            }
    
    async def navigate_to_tax_checklist(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        导航到纳税记录查询页面
        
        Args:
            parameters: 操作参数
            
        Returns:
            导航结果
        """
        try:
            logger.info("导航到纳税记录查询页面")
            
            # 直接导航到深圳税务局纳税清单页面
            success = await self.helper.navigate_with_retry(self.SHENZHEN_TAX_URL)
            
            if not success:
                return {
                    "status": "error",
                    "message": "导航到纳税清单页面失败"
                }
            
            # 等待页面加载，检查是否需要登录
            login_check_result = await self.check_tax_login({
                "wait_for_login": parameters.get("wait_for_login", True),
                "login_timeout": parameters.get("login_timeout", 300)
            })
            
            if login_check_result.get("status") != "success":
                return login_check_result
            
            # 等待纳税清单页面加载
            page_loaded = await self.helper.wait_for_element(
                selector=".tax-checklist-container, .tax-record-container, .query-container",
                timeout=30
            )
            
            if not page_loaded:
                return {
                    "status": "error",
                    "message": "纳税清单页面加载超时"
                }
            
            logger.info("已成功导航到纳税记录查询页面")
            return {
                "status": "success", 
                "message": "已成功导航到纳税记录查询页面"
            }
            
        except Exception as e:
            logger.error(f"导航到纳税记录查询页面失败: {str(e)}")
            return {
                "status": "error",
                "message": f"导航到纳税记录查询页面失败: {str(e)}"
            }
    
    async def query_tax_record(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        查询纳税记录
        
        Args:
            parameters: 必须包含以下参数:
                start_date: 开始日期（格式：YYYY-MM-DD）
                end_date: 结束日期（格式：YYYY-MM-DD）
            
        Returns:
            查询结果
        """
        try:
            start_date = parameters.get('start_date')
            end_date = parameters.get('end_date')
            
            if not start_date or not end_date:
                return {"status": "error", "message": "缺少日期参数"}
            
            logger.info(f"查询纳税记录，开始日期:{start_date}，结束日期:{end_date}")
            
            # 检查是否在纳税记录页面
            checklist_page = await self.session.query_selector(
                ".tax-checklist-container, .tax-record-container, .query-container"
            )
            
            if not checklist_page:
                # 如果不在纳税记录页面，先导航到该页面
                result = await self.navigate_to_tax_checklist(parameters)
                if result.get("status") != "success":
                    return result
            
            # 设置查询日期范围
            dates_set = await self.helper.set_date_range(start_date, end_date)
            
            if not dates_set:
                logger.warning("设置日期范围失败，尝试其他方法")
                
                # 尝试查找并填充日期输入框
                start_date_set = await self.helper.fill_input(
                    value=start_date,
                    placeholder="开始日期",
                    label="开始日期"
                )
                
                end_date_set = await self.helper.fill_input(
                    value=end_date,
                    placeholder="结束日期",
                    label="结束日期"
                )
                
                if not (start_date_set and end_date_set):
                    logger.warning("填充日期输入框失败")
            
            # 查找并点击查询按钮
            query_clicked = await self.helper.find_and_click_element(
                text="查询",
                wait_time=3
            )
            
            if not query_clicked:
                # 尝试其他常见查询按钮文本
                for btn_text in ["搜索", "确定", "确认", "提交"]:
                    query_clicked = await self.helper.find_and_click_element(
                        text=btn_text,
                        wait_time=3
                    )
                    if query_clicked:
                        break
            
            if not query_clicked:
                # 尝试通过选择器查找常见的查询按钮
                query_clicked = await self.helper.find_and_click_element(
                    selector="button.search-btn, button.query-btn, button.submit-btn, button.el-button--primary",
                    wait_time=3
                )
            
            if not query_clicked:
                return {
                    "status": "error",
                    "message": "无法找到或点击查询按钮"
                }
            
            # this section will navigate the user to the newest page for getting records
            # 等待结果加载
            await asyncio.sleep(3)
            
            # 获取查询结果
            result_data = await self.get_tax_records(parameters)
            
            return result_data
            
        except Exception as e:
            logger.error(f"查询纳税记录失败: {str(e)}")
            return {
                "status": "error",
                "message": f"查询纳税记录失败: {str(e)}"
            }
    
    async def get_tax_records(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取纳税记录数据
        
        Args:
            parameters: 操作参数
            
        Returns:
            纳税记录数据
        """
        try:
            logger.info("正在获取纳税记录数据")
            
            # 等待表格加载完成
            table_loaded = await self.helper.wait_for_element(
                selector="table, .el-table",
                timeout=10
            )
            
            if not table_loaded:
                logger.warning("未找到表格元素，尝试使用DOM解析器查找")
                
                # 使用DOM解析器获取页面元素
                dom_result = await self.dom_parser.extract_dom_elements(self.session)
                if 'error' in dom_result:
                    return {
                        "status": "error",
                        "message": f"解析页面元素失败: {dom_result['error']}"
                    }
                
                # 检查是否有表格元素
                has_table = False
                for element in dom_result.get('interactive_elements', []):
                    if element.tag_name == 'table' or (element.class_name and 'table' in element.class_name.lower()):
                        has_table = True
                        break
                
                if not has_table:
                    return {
                        "status": "error",
                        "message": "页面中未找到表格数据"
                    }
            
            # 使用辅助工具提取税务记录
            records = await self.helper.extract_tax_records()
            
            if "error" in records:
                return {
                    "status": "error",
                    "message": records["error"]
                }
            
            # 如果没有记录，可能需要进一步处理
            if records.get('total', 0) == 0:
                logger.warning("未找到纳税记录，尝试检查页面状态")
                
                # 获取页面状态，检查是否有提示信息
                page_metadata = await self.dom_parser.get_page_metadata(self.session)
                
                # 查找可能的提示信息（如"无数据"、"查询无结果"等）
                empty_message = await self.session.evaluate("""
                () => {
                    // 查找常见的空数据提示
                    const emptyElements = document.querySelectorAll('.empty-text, .no-data, .el-table__empty-text');
                    for (const el of emptyElements) {
                        if (el.textContent.trim()) {
                            return el.textContent.trim();
                        }
                    }
                    
                    // 查找可能包含提示信息的元素
                    const messageElements = document.querySelectorAll('.message, .tip, .alert, .notice');
                    for (const el of messageElements) {
                        if (el.textContent.trim()) {
                            return el.textContent.trim();
                        }
                    }
                    
                    return null;
                }
                """)
                
                if empty_message:
                    return {
                        "status": "success",
                        "message": f"查询完成，{empty_message}",
                        "records": {
                            "headers": [],
                            "data": [],
                            "total": 0
                        }
                    }
            
            logger.info(f"成功获取纳税记录，共{records.get('total', 0)}条记录")
            
            return {
                "status": "success",
                "message": f"成功获取纳税记录，共{records.get('total', 0)}条记录",
                "records": records
            }
            
        except Exception as e:
            logger.error(f"获取纳税记录数据失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取纳税记录数据失败: {str(e)}"
            }
        
    async def query_tax_records_complete(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        一次性完成整个税务查询流程：导航、登录、选择城市、查询纳税记录
        
        Args:
            parameters: 操作参数，包含:
                city: 城市名称（默认为"深圳市"）
                start_date: 开始日期（格式：YYYY-MM-DD）
                end_date: 结束日期（格式：YYYY-MM-DD）
                wait_for_login: 是否等待用户登录（默认为True）
                login_timeout: 登录等待超时时间（默认为300秒）
        
        Returns:
            完整的查询结果
        """
        try:
            # 获取参数
            city = parameters.get('city', '深圳市')
            start_date = parameters.get('start_date')
            end_date = parameters.get('end_date')
            
            # 验证日期参数
            if not start_date or not end_date:
                return {"status": "error", "message": "缺少必要的日期参数"}
            
            logger.info(f"开始执行完整税务查询流程，城市: {city}, 日期范围: {start_date} 至 {end_date}")
            
            # 步骤1: 导航到主页
            main_result = await self.navigate_to_main_page({})
            if main_result.get("status") != "success":
                logger.error(f"导航到主页失败: {main_result.get('message')}")
                return main_result
            
            logger.info("成功导航到主页")
            
            # 步骤2: 选择城市
            city_result = await self.select_city({"city": city})
            if city_result.get("status") not in ["success", "warning"]:
                logger.error(f"选择城市失败: {city_result.get('message')}")
                return city_result
            
            logger.info(f"城市选择结果: {city_result.get('message')}")
            
            # 步骤3: 导航到纳税清单页面（包含登录处理）
            checklist_result = await self.navigate_to_tax_checklist({
                "wait_for_login": parameters.get('wait_for_login', True),
                "login_timeout": parameters.get('login_timeout', 300)
            })
            
            if checklist_result.get("status") != "success":
                logger.error(f"导航到纳税清单页面失败: {checklist_result.get('message')}")
                return checklist_result
            
            logger.info("成功导航到纳税清单页面")
            
            # 步骤4: 查询纳税记录
            query_result = await self.query_tax_record({
                "start_date": start_date,
                "end_date": end_date
            })
            
            if query_result.get("status") != "success":
                logger.error(f"查询纳税记录失败: {query_result.get('message')}")
                return query_result
            
            logger.info(f"成功查询纳税记录，共 {query_result.get('records', {}).get('total', 0)} 条记录")
            
            # 返回完整结果，添加附加信息
            return {
                "status": "success",
                "message": "成功完成税务查询流程",
                "query_info": {
                    "city": city,
                    "start_date": start_date,
                    "end_date": end_date,
                    "query_time": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "records": query_result.get("records", {})
            }
        
        except Exception as e:
            logger.error(f"执行完整税务查询流程时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"执行完整税务查询流程时出错: {str(e)}"
            }