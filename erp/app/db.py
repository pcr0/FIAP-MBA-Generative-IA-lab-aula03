import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Banco SQLite em arquivo local (pasta data/)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mini_erp.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para injetar sessão do banco nas rotas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
