from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_timeout=5,
                       connect_args={"connect_timeout": 5})


def get_db():
    with Session(engine) as session:
        yield session
