from ..db import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime
from datetime import datetime

class Repo(Base):
    __tablename__ = 'repo'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_name : Mapped[str] = mapped_column(unique=True, index=True)
    installation_id : Mapped[int] = mapped_column()
    owner: Mapped[str] = mapped_column()
    created_at: Mapped[DateTime] = mapped_column(DateTime,default=datetime.now())
