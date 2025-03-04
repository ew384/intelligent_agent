# tool_service/src/tools/handlers/wechat.py
from .base import BaseHandler
from typing import Dict, Any, Optional
import logging
import asyncio
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class WeChatHandler(BaseHandler):
    """
    WeChat操作处理器
    职责:
    1. 提供微信Web版的搜索联系人和发送消息功能
    2. 处理与微信相关的各种操作
    3. 提供通用的微信接口以供其他场景使用
    """
    
    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理微信操作请求"""
        action = parameters.get('action')
        if not action:
            return {"status": "error", "message": "未指定action参数"}
        
        # 业务逻辑路由
        action_map = {
            "search_contact": self.search_contact,
            "send_message": self.send_message,
            "search_and_send": self.search_and_send,
            "check_login": self.check_wechat_login
        }
        
        # 调用具体的业务逻辑方法
        handler = action_map.get(action)
        if not handler:
            return {"status": "error", "message": f"未知的微信操作: {action}"}
        
        return await handler(parameters)

    async def check_wechat_login(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查微信是否已登录，并管理 cookies
        
        Args:
            parameters: 操作参数
                
        Returns:
            检查结果
        """
        try:
            service_id = parameters.get('service_id', 'wechat')
            if not isinstance(service_id, str):
                service_id = str(service_id)
            logger.info("检查微信登录状态")
            
            # 尝试加载之前保存的 cookies
            has_cookies = await self.session.load_cookies(service_id, domain="web.wechat.com")
            
            # 如果有 cookies，刷新页面应用 cookies
            if has_cookies:
                logger.info("找到已保存的 cookies，刷新页面应用...")
                await self.session.refresh_page()
                
                # 等待页面加载完成
                await asyncio.sleep(3)
            
            # 检查是否已登录的选择器
            login_indicators = [
                ".chat_list", 
                ".chat_item", 
                ".contacts",
                ".panel"
            ]
            
            # 检查文本指示
            text_indicators = [
                "通讯录",
                "会话",
                "发现"
            ]
            
            # 检查是否已登录
            is_logged_in = False
            
            # 检查选择器
            for selector in login_indicators:
                element = await self.session.query_selector(selector)
                if element:
                    logger.info(f"检测到微信已登录，指示器: {selector}")
                    is_logged_in = True
                    break
            
            # 检查页面文本
            if not is_logged_in:
                page_text = await self.session.execute_script("return document.body.innerText;")
                for text in text_indicators:
                    if text in page_text:
                        logger.info(f"检测到微信已登录，文本指示: {text}")
                        is_logged_in = True
                        break
            
            # 如果已登录，保存 cookies
            if is_logged_in:
                logger.info("微信已登录，保存 cookies...")
                await self.session.save_cookies(service_id)
                
                return {
                    "status": "success",
                    "message": "微信已登录",
                    "logged_in": True
                }
            
            # 检查是否显示了二维码，表示需要登录
            qr_code = await self.session.query_selector(".qrcode")
            if qr_code:
                logger.info("检测到微信登录二维码，等待用户扫码登录")
                
                # 开始检测登录状态变化
                if parameters.get('wait_for_login', False):
                    logger.info("等待用户扫码登录...")
                    
                    # 最大等待时间（默认5分钟）
                    max_wait_time = parameters.get('login_timeout', 300)
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait_time:
                        # 循环检查登录状态
                        for selector in login_indicators:
                            element = await self.session.query_selector(selector)
                            if element:
                                logger.info(f"检测到微信已登录，指示器: {selector}")
                                
                                # 保存 cookies
                                await self.session.save_cookies(service_id)
                                
                                return {
                                    "status": "success",
                                    "message": "微信已登录",
                                    "logged_in": True
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
                    "message": "请使用微信扫描二维码登录",
                    "logged_in": False
                }
            
            logger.warning("无法确定微信登录状态")
            return {
                "status": "error",
                "message": "无法确定微信登录状态",
                "logged_in": False
            }
            
        except Exception as e:
            logger.error(f"检查微信登录状态失败: {str(e)}")
            return {
                "status": "error",
                "message": f"检查微信登录状态失败: {str(e)}",
                "logged_in": False
            }
    
    async def search_contact(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        搜索联系人
        
        Args:
            parameters: 必须包含contact_name字段
            
        Returns:
            搜索结果
        """
        try:
            contact_name = parameters.get('contact_name')
            if not contact_name:
                return {"status": "error", "message": "缺少contact_name参数"}
            
            logger.info(f"搜索联系人: {contact_name}")
            
            # 点击搜索按钮
            search_button = await self.session.wait_for_selector(".search_bar input")
            if not search_button:
                return {"status": "error", "message": "找不到搜索框"}
            
            await self.session.click(".search_bar input")
            
            # 输入联系人名称
            await self.session.fill(".search_bar input", contact_name)
            
            # 等待搜索结果
            await asyncio.sleep(2)
            
            # 查找联系人
            contact_found = False
            contact_id = None
            
            # 执行JavaScript来查找联系人
            search_results = await self.session.execute_script("""
                const results = [];
                const items = document.querySelectorAll('.contact_item');
                
                for (const item of items) {
                    const nameElement = item.querySelector('.nickname');
                    if (nameElement && nameElement.textContent.includes(arguments[0])) {
                        results.push({
                            id: item.getAttribute('data-username') || item.id,
                            name: nameElement.textContent.trim()
                        });
                    }
                }
                
                return results;
            """, contact_name)
            
            if search_results and len(search_results) > 0:
                contact_found = True
                first_contact = search_results[0]
                contact_id = first_contact.get('id')
                contact_display_name = first_contact.get('name')
                
                logger.info(f"找到联系人: {contact_display_name}, ID: {contact_id}")
                
                # 点击第一个匹配的联系人
                result = await self.session.execute_script("""
                    const items = document.querySelectorAll('.contact_item');
                    for (const item of items) {
                        const nameElement = item.querySelector('.nickname');
                        if (nameElement && nameElement.textContent.includes(arguments[0])) {
                            item.click();
                            return true;
                        }
                    }
                    return false;
                """, contact_name)
                
                if not result:
                    return {
                        "status": "error",
                        "message": f"找到联系人 {contact_display_name}，但无法点击"
                    }
                
                # 等待聊天窗口加载
                await asyncio.sleep(2)
                
                return {
                    "status": "success",
                    "message": f"成功找到并选择联系人 {contact_display_name}",
                    "contact_found": True,
                    "contact_id": contact_id,
                    "contact_name": contact_display_name,
                    "results": search_results
                }
            else:
                logger.warning(f"未找到联系人: {contact_name}")
                return {
                    "status": "error",
                    "message": f"未找到联系人: {contact_name}",
                    "contact_found": False
                }
            
        except Exception as e:
            logger.error(f"搜索联系人失败: {str(e)}")
            return {
                "status": "error",
                "message": f"搜索联系人失败: {str(e)}",
                "contact_found": False
            }
    
    async def send_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送消息
        
        Args:
            parameters: 必须包含message字段，可选contact_id字段
            
        Returns:
            发送结果
        """
        try:
            message = parameters.get('message')
            if not message:
                return {"status": "error", "message": "缺少message参数"}
            
            # 如果提供了contact_id，先确保我们在正确的聊天中
            contact_id = parameters.get('contact_id')
            if contact_id:
                # 确保我们在正确的聊天窗口
                logger.info(f"切换到联系人: {contact_id}")
                # 这里可以添加切换聊天窗口的逻辑
            
            logger.info(f"发送消息: {message}")
            # 使用JavaScript模拟复制粘贴行为
            paste_script = """
            function setMessageByPaste(message) {
                // 获取编辑区域
                const editArea = document.getElementById('editArea');
                if (!editArea) return false;
                
                // 聚焦编辑区域
                editArea.focus();
                
                // 清空现有内容
                editArea.innerHTML = '';
                
                // 使用 execCommand 模拟粘贴操作
                // 这需要先把消息放入剪贴板，但浏览器安全策略限制了这点
                // 所以我们直接设置innerHTML，并触发input事件
                editArea.innerHTML = message.replace(/\\n/g, '<br>');
                
                // 触发input事件让微信知道内容已改变
                const event = new Event('input', { bubbles: true });
                editArea.dispatchEvent(event);
                
                return true;
            }
            return setMessageByPaste(arguments[0]);
            """
            
            # 执行脚本
            success = await self.session.execute_script(paste_script, message)
            
            # 找到消息输入区域并发送消息
           # edit_area = await self.session.wait_for_selector("#editArea")
            if not success:
                return {"status": "error", "message": "找不到消息输入区域"}
            
            # 清除现有文本并输入消息
           # await self.session.fill("#editArea", message)
            
            # 点击发送按钮
            send_button = await self.session.wait_for_selector(".btn_send")
            if not send_button:
                return {"status": "error", "message": "找不到发送按钮"}
            
            await self.session.click(".btn_send")
            
            logger.info("消息已发送")
            return {
                "status": "success",
                "message": "消息已成功发送"
            }
            
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return {
                "status": "error",
                "message": f"发送消息失败: {str(e)}"
            }
    
    async def search_and_send(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        搜索联系人并发送消息
        
        Args:
            parameters: 必须包含contact_name和message字段
            
        Returns:
            操作结果
        """
        try:
            contact_name = parameters.get('contact_name')
            message = parameters.get('message')
            
            if not contact_name:
                return {"status": "error", "message": "缺少contact_name参数"}
            if not message:
                return {"status": "error", "message": "缺少message参数"}
            
            logger.info(f"搜索联系人并发送消息: {contact_name}")
            
            # 首先搜索联系人
            search_result = await self.search_contact({"contact_name": contact_name})
            
            if search_result.get("status") != "success":
                return search_result
            
            # 然后发送消息
            contact_id = search_result.get("contact_id")
            send_result = await self.send_message({
                "message": message,
                "contact_id": contact_id
            })
            
            if send_result.get("status") != "success":
                return send_result
            
            return {
                "status": "success",
                "message": f"成功向联系人 {contact_name} 发送消息",
                "contact_name": search_result.get("contact_name"),
                "contact_id": contact_id
            }
            
        except Exception as e:
            logger.error(f"搜索联系人并发送消息失败: {str(e)}")
            return {
                "status": "error",
                "message": f"搜索联系人并发送消息失败: {str(e)}"
            }
