# tool_service/src/tools/handlers/social_security_handler.py
from .base import BaseHandler
from typing import Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class SocialSecurityHandler(BaseHandler):
    """社保清单操作处理器"""
    
    def __init__(self, browser_context):
        super().__init__(browser_context)
        self.BASE_URL = "https://www.gdzwfw.gov.cn/portal/index?region=440300"
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 业务逻辑路由
        action_map = {
            "navigate_to_social_security": self.navigate_to_social_security,
            "prompt_select_person": self.prompt_user_to_select,
            "navigate_and_select_person":self.navigate_and_select_person,
        }
        
        handler = action_map.get(action)
        if not handler:
            return await super().process_query(parameters)
            
        try:
            return await handler(parameters)
        finally:
            if parameters.get('close_session', False):
                await self.cleanup()
                
    async def navigate_to_social_security(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """导航到社保清单查询页面"""
        try:
            print("🌐 正在导航到广东政务服务网...")
            
            # 使用组合工具完成搜索和导航
            result = await self.search_and_navigate({
                "base_url": self.BASE_URL,
                'search_button_text': '搜索',
                "search_keyword": "社保清单打印",
                "result_keyword": "社保清单"
            })
            print("✅ 搜索社保清单打印完成")
            
            print("🔍 点击'社保查询'链接...")
            await self.find_and_click_element_by_text({"text": "社保查询"})
            print("✅ 成功点击社保查询")

            print("🔍 点击'个人权益记录查询打印'链接...")
            await self.find_and_click_element_by_text({"text": "个人权益记录（参保证明）查询打印(个人参保证明查询打印)"})
            print("✅ 成功点击个人权益记录查询打印")
            
            print("🔍 点击'在线办理'按钮...")
            await self.find_and_click_element_by_text({"text": "在线办理"})
            print("✅ 成功点击在线办理")

            if result["status"] == "success":
                return {
                    "status": "success", 
                    "message": "成功导航到社保清单查询",
                    "new_tab_created": result.get("new_tab_created", False),
                    "url": result.get("url", "未知")
                }
            else:
                return result
                    
        except Exception as e:
            logger.error(f"导航到社保清单查询页面失败: {str(e)}")
            print(f"❌ 导航失败: {str(e)}")
            return {
                "status": "error",
                "message": f"导航到社保清单查询页面失败: {str(e)}"
            }

    async def prompt_user_to_select(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """提示用户选择要操作的人员"""
        try:
            
            # 获取当前页面状态
            state = await self.browser_context.get_state()
            await self.highlight_elements({"viewport_expansion": 500})
            return await self.request_user_action({
                "type": "decision",
                "message": "请选择需要操作的人员",
                "description": "请点击相应人员对应的'选择'按钮继续操作",
                "options": []  # 不提供选项，让用户直接在界面上点击
            })
        except Exception as e:
            return {
                "status": "error",
                "message": f"提示用户选择失败: {str(e)}"
            }

    async def navigate_and_select_person(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        两步骤工具：先导航到社保清单页面，然后提示用户选择人员
        
        Args:
            parameters: 参数字典(可选)
            
        Returns:
            操作结果
        """
        try:
            print("\n" + "="*50)
            print("🔍 开始执行社保清单查询流程...")
            
            # 步骤1: 导航到社保清单页面
            print("📌 步骤1: 导航到社保清单查询页面")
            nav_result = await self.navigate_to_social_security(parameters)
            
            if nav_result["status"] != "success":
                print(f"❌ 导航失败: {nav_result['message']}")
                return nav_result  # 如果导航失败，直接返回结果
            
            print(f"✅ 成功导航到: {nav_result.get('url', '未知URL')}")
            
            # 步骤2: 高亮页面元素以便用户查看
            print("📌 步骤2: 准备选择人员信息")
            state = await self.browser_context.get_state()
            print(f"📄 当前页面标题: {state.title}")
            await self.highlight_elements({"viewport_expansion": 500})
            print("✅ 页面元素已高亮显示")
            
            # 步骤3: 选择用户
            print("📌 步骤3: 点击'选择'按钮")
            select_result = await self.find_and_click_element_by_text({"text": "选择"})
            print(select_result["message"])
            if select_result["status"] == "success":
                print("✅ 已成功点击'选择'按钮")
            else:
                print(f"❌ 点击'选择'按钮失败: {select_result.get('message', '未知错误')}")
            
            # 步骤4: 下载文件
            print("📌 步骤4: 点击'下载'按钮")
            click_result = await self.find_and_click_element_by_text({"text": "下载"})
            print(click_result["message"])
            if click_result["status"] == "success":
                print("✅ 已成功点击'下载'按钮")
                print("🎉 社保清单查询完成并已下载!")
                print("="*50 + "\n")
                return {
                    **click_result,
                    "is_done": True,
                    "task_success": True,
                    "message": "社保清单查询完成并已下载"
                }
            else:
                print(f"❌ 点击'下载'按钮失败: {click_result.get('message', '未知错误')}")
                print("="*50 + "\n")
                return click_result
                
        except Exception as e:
            logger.error(f"导航并选择人员失败: {str(e)}")
            print(f"❌ 执行过程中出错: {str(e)}")
            print("="*50 + "\n")
            return {
                "status": "error",
                "message": f"导航并选择人员失败: {str(e)}"
            }