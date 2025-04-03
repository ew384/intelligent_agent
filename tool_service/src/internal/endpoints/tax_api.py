# tool_service/src/internal/endpoints/tax_api.py
from fastapi import APIRouter, Request
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
from ...tools.browser.browser_manager import BrowserManager
from ...tools.handlers.tax_handler import TaxHandler

router = APIRouter()
logger = logging.getLogger(__name__)
browser_manager = BrowserManager()

@router.post("/query_complete")
async def query_tax_records_complete(request: Request):
    """
    一次性完成整个税务查询流程：从导航到查询返回结果的自动化查询
    
    Args:
        request: 请求对象，可以包含以下参数:
            city: 城市名称（默认为"深圳市"）
            start_date: 开始日期（格式：YYYY-MM-DD），可选，默认为90天前
            end_date: 结束日期（格式：YYYY-MM-DD），可选，默认为当前日期
            wait_for_login: 是否等待用户登录（默认为True）
            login_timeout: 登录等待超时时间（默认为300秒）
            service_id: 服务ID，用于cookie管理（默认为'tax_service'）
            close_session: 查询完成后是否关闭会话（默认为False）
        
    Returns:
        完整的查询结果
    """
    try:
        # 解析请求参数
        parameters = await request.json()
        
        # 设置默认参数
        city = parameters.get('city', '深圳市')
        service_id = parameters.get('service_id', 'tax_service')
        
        # 如果未提供日期，使用近90天的日期范围
        if not parameters.get('start_date') or not parameters.get('end_date'):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            parameters['start_date'] = start_date.strftime('%Y-%m-%d')
            parameters['end_date'] = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"开始执行一次性完整税务查询流程，城市: {city}")
        
        # 获取专用标签页
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(
            service_id, 
            url=None  # 不预先导航，让处理器负责导航
        )
        
        # 创建处理器
        handler = TaxHandler(session)
        
        # 执行完整查询流程
        result = await handler.query_tax_records_complete(parameters)
        
        # 资源清理（如果需要）
        if parameters.get('close_session', False):
            await session.close()
            if tab_handle in browser_manager.tab_services:
                del browser_manager.tab_services[tab_handle]
        
        return result
    except Exception as e:
        logger.error(f"执行一次性完整税务查询流程时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"查询失败: {str(e)}"}

@router.post("/{action}")
async def handle_tax_action(action: str, request: Request):
    """
    处理电子税务局操作
    
    Args:
        action: 要执行的操作，如check_login、select_city、query_tax_record等
        request: 请求对象
        
    Returns:
        操作执行结果
    """
    try:
        # 1. 请求解析
        parameters = await request.json()
        parameters['action'] = action
        
        logger.info(f"执行税务操作: {action}, 参数: {parameters}")
        
        # 2. 会话管理 - 使用标签页管理
        service_id = parameters.get('service_id', 'tax_service')
        tax_url = "https://etax.chinatax.gov.cn/?dmnHafHu=4GaB4GlqEiwcKTTdRKqNSIrmPl6C4Fotuqtcf8HlZ3KBQv_qxzOqEcP8SmwFXbxbJSCPer3FLzftI0Zep6WcQqzaluxjqcxz"
        
        # 获取专用标签页
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(
            service_id, 
            url=tax_url if parameters.get('skip_navigation', False) is not True else None
        )
        
        # 3. 创建处理器并执行操作
        handler = TaxHandler(session)
        result = await handler.process_query(parameters)
        
        # 4. 资源清理
        if parameters.get('close_session', False):
            await session.close()
            # 从标签页映射中删除
            if tab_handle in browser_manager.tab_services:
                del browser_manager.tab_services[tab_handle]
            
        return result
    except Exception as e:
        logger.error(f"处理税务操作 {action} 时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"操作失败: {str(e)}"}


@router.post("/tax_checklist/query")
async def query_tax_checklist(request: Request):
    """
    查询近3个月的纳税清单
    
    Args:
        request: 请求对象，可以包含city参数指定城市（默认为"深圳市"）
        
    Returns:
        查询结果
    """
    try:
        # 解析请求参数
        parameters = await request.json()
        city = parameters.get('city', '深圳市')
        
        # 计算近3个月的日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        query_params = {
            'service_id': 'tax_service',
            'city': city,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        logger.info(f"开始查询近3个月纳税清单，城市: {city}")
        
        # 获取专用标签页
        browser_service, session, tab_handle = await browser_manager.get_or_create_service_tab(
            query_params['service_id'], 
            url="https://etax.chinatax.gov.cn/" if parameters.get('skip_navigation', False) is not True else None
        )
        
        # 创建处理器
        handler = TaxHandler(session)
        
        # 1. 导航到主页
        main_result = await handler.navigate_to_main_page({})
        if main_result.get("status") != "success":
            return main_result
        
        # 2. 选择城市
        city_result = await handler.select_city({"city": city})
        if city_result.get("status") != "success":
            return city_result
        
        # 3. 导航到纳税清单页面
        checklist_result = await handler.navigate_to_tax_checklist({
            "wait_for_login": True,
            "login_timeout": 300
        })
        if checklist_result.get("status") != "success":
            return checklist_result
        
        # 4. 查询纳税记录
        query_result = await handler.query_tax_record({
            "start_date": query_params['start_date'],
            "end_date": query_params['end_date']
        })
        
        # 5. 资源清理（如果需要）
        if parameters.get('close_session', False):
            await session.close()
            if tab_handle in browser_manager.tab_services:
                del browser_manager.tab_services[tab_handle]
        
        return query_result
    except Exception as e:
        logger.error(f"查询近3个月纳税清单时出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"查询失败: {str(e)}"}
