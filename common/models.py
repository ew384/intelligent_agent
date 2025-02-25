from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from enum import Enum
import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str
    client_id: str
    query: str
    status: TaskStatus
    context: Optional[Dict] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    result: Optional[Dict] = None

class TaskRequest(BaseModel):
    scenario_type: str
    parameters: Dict[str, Any]

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    
class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"

class LLMConfig(BaseModel):
    provider: LLMProvider
    model_name: str
    api_key: str
    parameters: Dict

class ScenarioType(Enum):
    HR_RECRUITMENT = "hr_recruitment"
    ECOMMERCE = "ecommerce"
    PRICE_COMPARISON = "price_comparison"
    CUSTOM = "custom"

class Scenario(BaseModel):
    id: str
    type: ScenarioType
    name: str
    description: str
    workflow: Dict
    required_tools: List[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime