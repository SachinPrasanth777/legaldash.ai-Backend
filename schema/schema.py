from pydantic import BaseModel, Field
from typing import List


class CreateClient(BaseModel):
    name: str
    description: str
    documents: dict


class CreateLawsuit(BaseModel):
    client_id: str
    documents: dict
    response: str


class UpdateClient(BaseModel):
    name: str
    description: str
