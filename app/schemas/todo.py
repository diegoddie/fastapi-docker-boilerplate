from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class Todo(BaseModel):
    id: UUID
    title: str
    description: str
    completed: bool = False
    created_at: datetime 
    updated_at: datetime

    class Config:
        from_attributes = True

class TodoCreate(BaseModel):
    title: str
    description: str

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

