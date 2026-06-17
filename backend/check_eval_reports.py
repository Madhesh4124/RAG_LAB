import asyncio
from sqlalchemy import inspect, text
from app.database import engine

async def check_tables():
    async with engine.connect() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        tables = await conn.run_sync(get_tables)
        print("TABLES:", tables)
        if "evaluation_reports" in tables:
            def get_cols(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns("evaluation_reports")]
            cols = await conn.run_sync(get_cols)
            print("evaluation_reports columns:", cols)

if __name__ == "__main__":
    asyncio.run(check_tables())
