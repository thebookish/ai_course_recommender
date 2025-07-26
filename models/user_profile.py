from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

@dataclass
class UserProfile:
    user_id: str
    preferences: Dict
    learning_history: List[str]
    feedback_history: List[Dict]
    created_at: datetime
    updated_at: datetime
