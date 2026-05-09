import asyncio
from sqlalchemy import inspect
from app.database import engine

async def check_schema():
    async with engine.connect() as conn:
        def get_columns(connection):
            inspector = inspect(connection)
            return [col['name'] for col in inspector.get_columns("documents")]
        
        columns = await conn.run_sync(get_columns)
        print("COLUMNS:" + ",".join(columns))

if __name__ == "__main__":
    asyncio.run(check_schema())
