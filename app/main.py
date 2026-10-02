import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Config comes from the environment, so the same code runs locally,
# in Docker Compose and on OpenShift. SQLite is the local fallback.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    done = Column(Boolean, default=False)


Base.metadata.create_all(bind=engine)


class TaskCreate(BaseModel):
    title: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    done: bool


app = FastAPI(title="Task Tracker API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(title=payload.title)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()


@app.patch("/tasks/{task_id}/done", response_model=TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.done = True
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()