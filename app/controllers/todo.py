from datetime import datetime
from sqlalchemy.orm import Session
from typing import List
from fastapi import HTTPException
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate

def get_todos(db: Session) -> List[Todo]:
    return db.query(Todo).all()

def get_todo_by_id(todo_id: str, db: Session) -> Todo:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

def create_todo(todo: TodoCreate, db: Session) -> Todo:
    new_todo = Todo(title=todo.title, description=todo.description)

    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)

    return new_todo

def update_todo(todo_id: str, todo: TodoUpdate, db: Session) -> Todo:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    updated_data = todo.model_dump(exclude_unset=True)

    if not updated_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    for key, value in updated_data.items():
        setattr(db_todo, key, value)

    db_todo.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_todo)
    return db_todo

def delete_todo(todo_id: str, db: Session) -> dict:
    db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    db.delete(db_todo)
    db.commit()
    return { "message": "Todo deleted successfully" }