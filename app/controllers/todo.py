from datetime import datetime
from sqlalchemy.orm import Session
from typing import List
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate

def get_todos(db: Session) -> List[Todo]:
    return db.query(Todo).all()

def get_todo_by_id(todo_id: str, db: Session) -> Todo | None:
    return db.query(Todo).filter(Todo.id == todo_id).first()

def create_todo(todo: TodoCreate, db: Session) -> Todo:
    new_todo = Todo(title=todo.title, description=todo.description)

    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)

    return new_todo

def update_todo(todo_id: str, todo: TodoUpdate, db: Session) -> Todo | None:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not db_todo:
        return None

    if todo.title is not None:
        db_todo.title = todo.title
    if todo.description is not None:
        db_todo.description = todo.description
    if todo.completed is not None:
        db_todo.completed = todo.completed
    
    db_todo.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_todo)
    return db_todo

def delete_todo(todo_id: str, db: Session) -> dict | None:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not db_todo:
        return None
    
    db.delete(db_todo)
    db.commit()
    return { "message": "Todo deleted successfully" }