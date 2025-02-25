# tool-service/src/tools/handlers/hr_resume.py
from .base import BaseHandler
from typing import Dict, Any, List
import logging
import json
from playwright.async_api import TimeoutError

logger = logging.getLogger(__name__)

class HRResumeHandler(BaseHandler):
    """Handler for HR recruitment website automation"""
    
    # Selectors for BOSS直聘 (adjust these based on the actual website structure)
    BOSS_SELECTORS = {
        'login': {
            'username': '.login-email-wrap input',  # or '.login-account input'
            'password': '.password-wrap input',
            'submit': '.btn-login',
            'success_indicator': '.user-nav-avatar'  # Element indicating successful login
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
        """Generic query processor (required by base class)"""
        return await self.process_hr_query(parameters)

    async def process_hr_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process HR recruitment website query"""
        try:
            # Step 1: Navigate to website
            url = parameters.get("url", "https://www.zhipin.com/")
            await self.page.goto(url)
            
            # Step 2: Handle login
            if not await self._login(parameters.get("username"), parameters.get("password")):
                return {"status": "error", "message": "Login failed or timed out"}
            
            # Step 3: Navigate to resume inbox (assuming the login is successful)
            try:
                # Wait for navigation to complete after login
                await self.page.wait_for_load_state("networkidle")
                
                # Navigate to resume inbox (adjust URL as needed)
                resume_inbox_url = f"{url}/web/geek/chat"  # Example path, adjust as needed
                await self.page.goto(resume_inbox_url)
                
                # Step 4: Extract resumes
                resumes = await self._extract_resumes(
                    max_resumes=parameters.get("max_resumes", 5)
                )
                
                return {
                    "status": "success",
                    "resumes": resumes
                }
                
            except Exception as e:
                logger.error(f"Resume extraction failed: {str(e)}")
                return {"status": "error", "message": f"Resume extraction failed: {str(e)}"}
                
        except Exception as e:
            logger.error(f"HR query failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _login(self, username: str, password: str) -> bool:
        """
        Handle login process for HR recruitment website
        
        Returns:
            Boolean indicating whether login was successful
        """
        try:
            # Wait for the login form to be visible
            await self.page.wait_for_selector(self.BOSS_SELECTORS['login']['username'], timeout=30000)
            
            # Fill in username/email
            await self.page.fill(self.BOSS_SELECTORS['login']['username'], username)
            
            # Fill in password
            await self.page.fill(self.BOSS_SELECTORS['login']['password'], password)
            
            # Click login button
            await self.page.click(self.BOSS_SELECTORS['login']['submit'])
            
            # Wait for successful login indicator
            await self.page.wait_for_selector(
                self.BOSS_SELECTORS['login']['success_indicator'], 
                timeout=30000
            )
            
            return True
            
        except TimeoutError:
            # If timeout occurs, login might require verification code or failed
            logger.warning("Login timeout - might need manual verification")
            
            # Give time for manual verification if needed
            try:
                await self.page.wait_for_selector(
                    self.BOSS_SELECTORS['login']['success_indicator'], 
                    timeout=300000  # 5 minutes for manual intervention
                )
                return True
            except TimeoutError:
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    async def _extract_resumes(self, max_resumes: int = 5) -> List[Dict[str, Any]]:
        """
        Extract resume data from the inbox
        
        Args:
            max_resumes: Maximum number of resumes to extract
            
        Returns:
            List of extracted resume data
        """
        resumes = []
        
        try:
            # Wait for resume list to be visible
            await self.page.wait_for_selector(
                self.BOSS_SELECTORS['resume_list']['container'],
                timeout=30000
            )
            
            # Get all resume cards
            resume_cards = await self.page.query_selector_all(
                self.BOSS_SELECTORS['resume_list']['container']
            )
            
            # Limit to max_resumes
            resume_cards = resume_cards[:max_resumes]
            
            # Process each resume
            for card in resume_cards:
                try:
                    # Extract basic info from card
                    name_elem = await card.query_selector(self.BOSS_SELECTORS['resume_list']['name'])
                    position_elem = await card.query_selector(self.BOSS_SELECTORS['resume_list']['position'])
                    
                    name = await name_elem.text_content() if name_elem else "Unknown"
                    position = await position_elem.text_content() if position_elem else "Unknown"
                    
                    # Click to view detailed resume
                    detail_link = await card.query_selector(self.BOSS_SELECTORS['resume_list']['detail_link'])
                    await detail_link.click()
                    
                    # Wait for resume detail page to load
                    await self.page.wait_for_selector(
                        self.BOSS_SELECTORS['resume_detail']['container'],
                        timeout=30000
                    )
                    
                    # Extract detailed resume information
                    resume_data = {
                        "name": name,
                        "current_position": position
                    }
                    
                    # Extract other fields if they exist
                    for field in ['age', 'experience', 'education', 'expected_salary', 'skills']:
                        selector = self.BOSS_SELECTORS['resume_detail'][field]
                        element = await self.page.query_selector(selector)
                        if element:
                            resume_data[field] = await element.text_content()
                    
                    # Extract work history
                    work_history_elem = await self.page.query_selector(
                        self.BOSS_SELECTORS['resume_detail']['work_history']
                    )
                    if work_history_elem:
                        work_history_text = await work_history_elem.text_content()
                        resume_data['work_history'] = work_history_text
                    
                    # Extract education history
                    education_elem = await self.page.query_selector(
                        self.BOSS_SELECTORS['resume_detail']['education_history']
                    )
                    if education_elem:
                        education_text = await education_elem.text_content()
                        resume_data['education_history'] = education_text
                    
                    # Add to resumes list
                    resumes.append(resume_data)
                    
                    # Go back to resume list
                    back_button = await self.page.query_selector(
                        self.BOSS_SELECTORS['resume_detail']['back_button']
                    )
                    if back_button:
                        await back_button.click()
                        await self.page.wait_for_selector(
                            self.BOSS_SELECTORS['resume_list']['container'],
                            timeout=30000
                        )
                    
                except Exception as e:
                    logger.error(f"Error processing individual resume: {str(e)}")
                    # Continue with next resume
            
            return resumes
            
        except Exception as e:
            logger.error(f"Resume extraction error: {str(e)}")
            return resumes  # Return any resumes that were successfully extracted