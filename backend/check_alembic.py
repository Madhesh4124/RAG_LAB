import asyncio
from sqlalchemy import text
from app.database import engine

async def check_alembic_version():
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT version_num FROM alembic_version"))
            version = res.scalar()
            print("ALEMBIC_VERSION:" + str(version))
        except Exception as e:
            print("ALEMBIC_VERSION:NOT_FOUND (" + str(e) + ")")

if __name__ == "__main__":
    asyncio.run(check_alembic_version())
