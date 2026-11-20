"""Copy the demo SQLite file into PostgreSQL without deleting the original."""

import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend" / "storyforge.db"
BACKUP_DIR = ROOT / "backend" / "backups"
TARGET = "postgresql+psycopg://storyforge:storyforge@127.0.0.1:5432/storyforge"
TABLES = [
    "worlds",
    "novels",
    "novel_worlds",
    "chapters",
    "chapter_revisions",
    "ai_suggestions",
]


def as_uuid(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(uuid.UUID(str(value)))


def as_time(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text_value = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text_value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"找不到 SQLite 文件：{SOURCE}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"storyforge-{stamp}.db"
    shutil.copy2(SOURCE, backup)
    print(f"backup={backup}")

    source = sqlite3.connect(SOURCE)
    source.row_factory = sqlite3.Row
    target = create_engine(TARGET)
    with target.begin() as connection:
        existing = connection.execute(text("select count(*) from novels")).scalar_one()
        if existing:
            raise SystemExit("PostgreSQL 里已经有小说，停止导入，避免覆盖。")
        for table in TABLES:
            rows = source.execute(f"select * from {table}").fetchall()
            if not rows:
                print(f"{table}=0")
                continue
            columns = rows[0].keys()
            statement = text(
                f"insert into {table} ({', '.join(columns)}) values ({', '.join(':' + name for name in columns)})"
            )
            payload = []
            for row in rows:
                item = {}
                for name in columns:
                    value = row[name]
                    if name == "id" or name.endswith("_id"):
                        value = as_uuid(value)
                    elif name.endswith("_at"):
                        value = as_time(value)
                    item[name] = value
                payload.append(item)
            connection.execute(statement, payload)
            print(f"{table}={len(payload)}")
    print("imported")


if __name__ == "__main__":
    main()
