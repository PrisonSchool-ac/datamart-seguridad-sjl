import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Nombre del servidor tal como aparece en SSMS ("Server name").
SERVIDOR = r"localhost\SQLEXPRESS"
BASE_DE_DATOS = "DataMartSeguridad"

DATABASE_URL = os.getenv("DATABASE_URL") or URL.create(
    "mssql+pyodbc",
    host=SERVIDOR,
    database=BASE_DE_DATOS,
    query={
        "driver": "ODBC Driver 17 for SQL Server",
        "trusted_connection": "yes",
        "TrustServerCertificate": "yes",
    },
)

_kwargs = {"fast_executemany": True} if str(DATABASE_URL).startswith("mssql") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()