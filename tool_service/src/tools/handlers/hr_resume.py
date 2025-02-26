# tool-service/src/tools/handlers/hr_resume.py
from .base import BaseHandler
from typing import Dict, Any, List
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

class HRResumeHandler(BaseHandler):
    """HR招聘网站自动化处理器"""
    
    # 选择器
    BOSS_SELECTORS = {
        'login': {
            'username': '.login-email-wrap input',  # 或 '.login-account input'
            'password': '.password-wrap input',
            'submit': '.btn-login',
            'success_indicator': '.user-nav-avatar'  # 指示登录成功的元素
        },
        'resume_list': {
            'container': '.resume-card',
            'detail_link': '.resume-link',
            'name': '.resume-name',
            'position': '.position-name'
        },
        'resume_detail': {
            'container': '.resume-content',
            'name': '.name',
            'age': '.age',
            'experience': '.experience',
            'education': '.education',
            'current_role': '.current-position',
            'expected_salary': '.expected-salary',
            'skills': '.skills',
            'projects': '.projects',
            'work_history': '.work-history',
            'education_history': '.education-history',
            'back_button': '.back-button'
        }
    }

    async def process_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理HR招聘查询"""
        try:
            # 导航到网站
            url = parameters.get("url", "https://www.zhipin.com/")
            await self.session.goto(url)
            
            # 处理登录
            login_result = await self._login(parameters.get("username"), parameters.get("password"))
            if not login_result:
                return {"status": "error", "message": "登录失败或超时"}
            
            # 导航到简历收件箱
            try:
                # 等待登录后导航完成
                await self.session.wait_for_load_state("networkidle")
                
                # 导航到简历收件箱
                resume_inbox_url = f"{url}/web/geek/chat"  # 示例路径，根据实际调整
                await self.session.goto(resume_inbox_url)
                
                # 提取简历
                resumes = await self._extract_resumes(
                    max_resumes=parameters.get("max_resumes", 5)
                )
                
                return {
                    "status": "success",
                    "resumes": resumes
                }
                
            except Exception as e:
                logger.error(f"简历提取失败: {str(e)}")
                return {"status": "error", "message": f"简历提取失败: {str(e)}"}
                
        except Exception as e:
            logger.error(f"HR查询失败: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _login(self, username: str, password: str) -> bool:
        """处理登录流程"""
        try:
            # 等待登录表单可见
            form_selector = self.BOSS_SELECTORS['login']['username']
            await self.session.wait_for_selector(form_selector, timeout=30000)
            
            # 填写用户名/邮箱
            await self.safe_fill(self.BOSS_SELECTORS['login']['username'], username)
            
            # 填写密码
            await self.safe_fill(self.BOSS_SELECTORS['login']['password'], password)
            
            # 点击登录按钮
            await self.safe_click(self.BOSS_SELECTORS['login']['submit'])
            
            # 等待用户交互（可能需要验证码）
            await self.wait_for_user_interaction("请完成验证（如果需要），然后按回车继续...")
            
            # 检查登录是否成功
            is_visible = await self.is_element_visible(self.BOSS_SELECTORS['login']['success_indicator'])
            return is_visible
                
        except Exception as e:
            logger.error(f"登录错误: {str(e)}")
            return False

    async def _extract_resumes(self, max_resumes: int = 5) -> List[Dict[str, Any]]:
        """提取简历数据"""
        resumes = []
        
        try:
            # 等待简历列表可见
            await self.session.wait_for_selector(
                self.BOSS_SELECTORS['resume_list']['container'],
                timeout=30000
            )
            
            # 获取所有简历卡片
            resume_cards = await self.session.query_selector_all(
                self.BOSS_SELECTORS['resume_list']['container']
            )
            
            # 限制为max_resumes
            resume_cards = resume_cards[:max_resumes]
            
            # 处理每份简历
            for card in resume_cards:
                try:
                    # 从卡片中提取基本信息
                    name = await self.extract_text(self.BOSS_SELECTORS['resume_list']['name'], "未知")
                    position = await self.extract_text(self.BOSS_SELECTORS['resume_list']['position'], "未知")
                    
                    # 点击查看详细简历
                    await self.safe_click(self.BOSS_SELECTORS['resume_list']['detail_link'])
                    
                    # 等待简历详情页加载
                    await self.session.wait_for_selector(
                        self.BOSS_SELECTORS['resume_detail']['container'],
                        timeout=30000
                    )
                    
                    # 提取详细简历信息
                    resume_data = {
                        "name": name,
                        "current_position": position
                    }
                    
                    # 提取其他字段
                    for field in ['age', 'experience', 'education', 'expected_salary', 'skills']:
                        selector = self.BOSS_SELECTORS['resume_detail'][field]
                        text = await self.extract_text(selector)
                        if text:
                            resume_data[field] = text
                    
                    # 提取工作经历
                    work_history = await self.extract_text(
                        self.BOSS_SELECTORS['resume_detail']['work_history'],
                        ""
                    )
                    if work_history:
                        resume_data['work_history'] = work_history
                    
                    # 提取教育经历
                    education_history = await self.extract_text(
                        self.BOSS_SELECTORS['resume_detail']['education_history'],
                        ""
                    )
                    if education_history:
                        resume_data['education_history'] = education_history
                    
                    # 添加到简历列表
                    resumes.append(resume_data)
                    
                    # 返回简历列表
                    await self.safe_click(self.BOSS_SELECTORS['resume_detail']['back_button'])
                    await self.session.wait_for_selector(
                        self.BOSS_SELECTORS['resume_list']['container'],
                        timeout=30000
                    )
                    
                except Exception as e:
                    logger.error(f"处理单个简历出错: {str(e)}")
                    # 继续处理下一份简历
            
            return resumes
            
        except Exception as e:
            logger.error(f"简历提取错误: {str(e)}")
            return resumes  # 返回已成功提取的简历
