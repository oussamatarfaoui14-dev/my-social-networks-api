"""SQLite persistence. Every write request is one atomic, serialized transaction."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import Request


def connect(path: str):
    db = sqlite3.connect(path, timeout=15, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 15000")
    return db


def initialize(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(Path(__file__).with_name("schema.sql").read_text())


def database(request: Request):
    db = connect(request.app.state.database_path)
    db.execute("BEGIN" if request.method in {"GET", "HEAD", "OPTIONS"} else "BEGIN IMMEDIATE")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def default_path():
    return os.environ.get("DATABASE_PATH", "data/social.db")


def one(db, table, item_id):
    from fastapi import HTTPException

    row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Ressource introuvable")
    return serialize_row(row)


def serialize_row(row):
    flags = {
        "members_can_post",
        "members_can_create_events",
        "shopping_enabled",
        "carpool_enabled",
        "ticketing_enabled",
        "closed",
    }
    return {key: bool(value) if key in flags else value for key, value in dict(row).items()}


def insert(db, table, values):
    keys = list(values)
    cur = db.execute(
        f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        list(values.values()),
    )
    return one(db, table, cur.lastrowid)


def update(db, table, item_id, values):
    if values:
        db.execute(
            f"UPDATE {table} SET {','.join(k + '=?' for k in values)} WHERE id=?", [*values.values(), item_id]
        )
    return one(db, table, item_id)


def page(db, table, where="1", args=(), q="", fields=("name",), limit=20, offset=0):
    if q:
        where += " AND (" + " OR ".join(f"instr(lower({f}), lower(?)) > 0" for f in fields) + ")"
        args = (*args, *([q] * len(fields)))
    total = db.execute(f"SELECT count(*) FROM {table} WHERE {where}", args).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM {table} WHERE {where} ORDER BY id LIMIT ? OFFSET ?", (*args, limit, offset)
    ).fetchall()
    return {"items": [serialize_row(r) for r in rows], "total": total, "limit": limit, "offset": offset}
