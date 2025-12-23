from ..db import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON, DateTime 
import enum

class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Task(Base):
    __tablename__ = 'task'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    repo: Mapped[str] = mapped_column()
    pr_number: Mapped[int] = mapped_column()
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.PENDING)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime,default=datetime.now())
    completed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)