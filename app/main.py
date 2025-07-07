from fastapi import FastAPI
from app.db.db import Base, engine
from app.routes import todo

app = FastAPI(title="Todo API", description="A simple todo API")

app.include_router(todo.router, prefix="/api/todos", tags=["todos"])