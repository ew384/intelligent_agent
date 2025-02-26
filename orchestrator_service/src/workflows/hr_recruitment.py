# orchestrator-service/src/workflows/hr_recruitment.py
from .base import BaseWorkflow
from typing import Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class HRRecruitmentWorkflow(BaseWorkflow):
    """
    Workflow for HR recruitment scenario that handles the sequence of operations 
    for logging into recruitment websites, extracting resumes, and evaluating candidates.
    """
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Step 1: Initialize browser and navigate to the recruitment website
            async with httpx.AsyncClient() as client:
                browser_response = await client.post(
                    "http://localhost:8003/tools/browser/hr-resume",
                    json=parameters
                )
                
                if browser_response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"Browser automation failed with status: {browser_response.status_code}"
                    }
                
                browser_result = browser_response.json()
                
                # Step 2: If resumes were successfully extracted, evaluate them with LLM
                if browser_result.get("status") == "success" and "resumes" in browser_result:
                    # Prepare LLM parameters
                    llm_params = {
                        "prompt": self._generate_evaluation_prompt(
                            browser_result["resumes"],
                            parameters["job_requirements"],
                            parameters.get("sort_criteria", [])
                        ),
                        "provider": "claude"  # Could be configurable
                    }
                    
                    # Call LLM service to evaluate resumes
                    llm_response = await client.post(
                        "http://localhost:8003/tools/llm/chat/claude",
                        json=llm_params
                    )
                    
                    if llm_response.status_code != 200:
                        return {
                            "status": "error",
                            "message": f"LLM evaluation failed with status: {llm_response.status_code}"
                        }
                    
                    llm_result = llm_response.json()
                    
                    # Combine results
                    return {
                        "status": "success",
                        "raw_resumes": browser_result["resumes"],
                        "evaluated_candidates": llm_result.get("responses", [])
                    }
                
                # Return browser results if LLM evaluation wasn't needed or failed
                return browser_result
                
        except Exception as e:
            logger.error(f"HR recruitment workflow failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _generate_evaluation_prompt(self, resumes, job_requirements, sort_criteria):
        """
        Generate a prompt for LLM to evaluate resumes against job requirements
        
        Args:
            resumes: List of extracted resumes
            job_requirements: Job requirements for candidate evaluation
            sort_criteria: Criteria for sorting candidates
        
        Returns:
            Formatted prompt for LLM
        """
        prompt = (
            f"Please evaluate the following resumes against these job requirements:\n\n"
            f"JOB REQUIREMENTS:\n{job_requirements}\n\n"
            f"RESUMES:\n"
        )
        
        # Add each resume to the prompt
        for i, resume in enumerate(resumes, 1):
            prompt += f"--- RESUME {i} ---\n"
            for key, value in resume.items():
                prompt += f"{key}: {value}\n"
            prompt += "\n"
        
        # Add sorting instructions
        if sort_criteria:
            prompt += (
                f"\nPlease rank these candidates based on the following criteria "
                f"(in order of importance):\n"
            )
            for criterion in sort_criteria:
                prompt += f"- {criterion}\n"
        else:
            prompt += "\nPlease rank these candidates from most suitable to least suitable for the position."
        
        prompt += (
            "\nFor each candidate, provide:\n"
            "1. Overall score (0-100)\n"
            "2. Strengths relative to the job requirements\n"
            "3. Weaknesses or missing qualifications\n"
            "4. Brief justification for their ranking\n"
            "\nFinally, provide a summary of the top 3 candidates you recommend for interview."
        )
        
        return prompt