from sqlalchemy import create_engine
from .config import settings
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(url=settings.database_url, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

class Base(DeclarativeBase):
    pass

