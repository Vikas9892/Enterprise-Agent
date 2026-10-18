"""Utility script to verify PostgreSQL and Redis connectivity prior to service startup."""

import os
import sys
import time
import psycopg


def wait_for_postgres(timeout_seconds: int = 60) -> bool:
    """Poll database connection until ready or timeout."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_agent",
    )
    # Strip SQLAlchemy dialect prefix for direct psycopg connection
    conn_str = db_url.replace("postgresql+psycopg://", "postgresql://")

    start_time = time.time()
    print(f"Waiting for PostgreSQL database at {conn_str}...")

    while time.time() - start_time < timeout_seconds:
        try:
            with psycopg.connect(conn_str, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    print("PostgreSQL is healthy and accepting connections!")
                    return True
        except Exception as exc:
            print(f"PostgreSQL not ready yet ({exc}). Retrying in 2 seconds...")
            time.sleep(2)

    print("Timed out waiting for PostgreSQL.")
    return False


if __name__ == "__main__":
    success = wait_for_postgres()
    sys.exit(0 if success else 1)
