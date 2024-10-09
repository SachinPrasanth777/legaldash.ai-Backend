from pydantic import BaseModel
from typing import List

class CreateClient(BaseModel):
    name: str
    userId: str
    documents: List[str]