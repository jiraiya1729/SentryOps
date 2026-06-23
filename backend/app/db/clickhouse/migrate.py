import os
from pathlib import Path

import clickhouse_connect

from app.core.config import settings

def get_client():

    return clickhouse_connect.get_client(
        host = settings.CLICKHOUSE_HOST,
        port = 8123,
        username = settings.CLICKHOUSE_USER,
        password = settings.CLICKHOUSE_PASSWORD,
    )

def run_migrations():
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        print("No migrations directory found")
        return
    
    client = get_client()

    migrations_files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))

    for filename in migrations_files:
        file_path = migrations_dir / filename
        print(f"Applying migration: {filename}")

        sql_content = file_path.read_text()

        def clean_statement(stmt):
            lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
            return "\n".join(lines).strip()

        statements = [
            clean_statement(stmt)
            for stmt in sql_content.split(";")
            if clean_statement(stmt)
        ]

        for statement in statements:
            try:
                client.command(statement)
                # print(f"Successfully applied: {filename}")
            except Exception as e:
                print(f"Error applying migration: {filename}")
                print(e)
                raise
        print(f"Successfully applied migration: {filename}")

    print("All migrations applied successfully")


if __name__ == "__main__":
    run_migrations()
