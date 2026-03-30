# backend/app/database.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, text
from app.config import DATABASE_URL, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


# Ensure PRAGMA foreign_keys=ON and journal_mode=WAL on EVERY new connection.
# This is critical because SQLAlchemy's connection pool may create multiple
# connections, and PRAGMAs set on one connection do not propagate to others.
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
