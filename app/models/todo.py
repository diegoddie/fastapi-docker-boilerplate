from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.db.db import Base
import uuid

class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, index=True)
    description = Column(String)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())