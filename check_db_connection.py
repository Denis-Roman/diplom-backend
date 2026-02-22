import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402


def main() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]

        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
        )
        table_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(1) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='Users'"
        )
        has_users = cursor.fetchone()[0]

        cursor.execute(
            "SELECT TOP (10) TABLE_SCHEMA, TABLE_NAME "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        sample_tables = cursor.fetchall()

    print("DB_NAME=", db_name)
    print("SQL_VERSION=", str(version).splitlines()[0])
    print("TABLES_COUNT=", table_count)
    print("HAS_Users_TABLE=", has_users)
    print("SAMPLE_TABLES=", sample_tables)


if __name__ == "__main__":
    main()
