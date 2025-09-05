from __future__ import annotations
import os
from sqlalchemy import create_engine, text
def get_engine(url: str | None = None):
    url = url or os.getenv("DATABASE_URL")
    if not url: raise RuntimeError("DATABASE_URL não configurada")
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
def ensure_postgis(engine):
    with engine.begin() as con:
        con.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
