# scenario-service/src/scenarios/hr_recruitment.py
from .base import BaseScenario
from typing import Dict, Any

class HRRecruitmentScenario(BaseScenario):
    """
    HR Recruitment scenario for automatically logging into recruitment websites,
    retrieving resumes, and ranking candidates based on requirements.
    """
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "hr_recruitment",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "Recruitment platform URL"},
                "username": {"type": "string", "required": True, "description": "Login username"},
                "password": {"type": "string", "required": True, "description": "Login password"},
                "job_requirements": {"type": "string", "required": True, "description": "Job requirements for candidate evaluation"},
                "sort_criteria": {"type": "array", "items": {"type": "string"}, "description": "Criteria for sorting candidates"}
            },
            "workflow": {
                "steps": [
                    {
                        "type": "browser_action",
                        "action": "navigate",
                        "parameters": {"url": "{url}"}
                    },
                    {
                        "type": "browser_action",
                        "action": "login",
                        "parameters": {
                            "username_selector": ".login-username-input",
                            "password_selector": ".login-password-input",
                            "submit_selector": ".login-submit-button",
                            "username": "{username}",
                            "password": "{password}"
                        }
                    },
                    {
                        "type": "browser_action",
                        "action": "navigate",
                        "parameters": {"url": "{url}/resume-inbox"}
                    },
                    {
                        "type": "browser_action",
                        "action": "extract_resumes",
                        "parameters": {
                            "resume_list_selector": ".resume-list-item",
                            "resume_detail_selector": ".resume-detail-link",
                            "max_resumes": 10
                        }
                    },
                    {
                        "type": "llm_action",
                        "action": "evaluate_resumes",
                        "parameters": {
                            "resumes": "{extracted_resumes}",
                            "job_requirements": "{job_requirements}",
                            "sort_criteria": "{sort_criteria}"
                        }
                    }
                ]
            }
        }