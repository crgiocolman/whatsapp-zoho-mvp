from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass

db_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg2://", 1
)
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
