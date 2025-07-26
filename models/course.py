from dataclasses import dataclass
from typing import List

@dataclass
class Course:
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    duration: int  # in hours
    tags: List[str]
    rating: float
    price: float
