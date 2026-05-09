from app.config import config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine(config.POSTGRES_DB_URL, pool_pre_ping=True, pool_size=10, max_overflow=5)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
