from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.controllers.todo import get_todos, get_todo_by_id, create_todo, update_todo, delete_todo
from app.schemas.todo import TodoCreate, TodoUpdate, Todo

router = APIRouter()

@router.get("/", response_model=List[Todo])
def get_todos_route(db: Session = Depends(get_db)):
    return get_todos(db)

@router.get("/{todo_id}", response_model=Todo | None)
def get_todo_by_id_route(todo_id: str, db: Session = Depends(get_db)):
    return get_todo_by_id(todo_id, db)

@router.post("/", response_model=Todo)
def create_todo_route(todo: TodoCreate, db: Session = Depends(get_db)):
    return create_todo(todo, db)

@router.put("/{todo_id}", response_model=Todo | None)
def update_todo_route(todo_id: str, todo: TodoUpdate, db: Session = Depends(get_db)):
    return update_todo(todo_id, todo, db)

@router.delete("/{todo_id}", response_model=dict | None)
def delete_todo_route(todo_id: str, db: Session = Depends(get_db)):
    return delete_todo(todo_id, db)