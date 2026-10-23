import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        return self.connection.execute(query.replace("?", "%s"), params)

@contextmanager
def db():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(database_url, connect_timeout=10, row_factory=dict_row) as connection:
            yield PostgresConnection(connection)
        return

    path = os.getenv("DATABASE_PATH", "data/study.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    if os.getenv("DATABASE_URL"):
        with db() as c:
            schema = (
                "CREATE TABLE IF NOT EXISTS users(id BIGSERIAL PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS documents(id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id),name TEXT,text TEXT)",
                "CREATE TABLE IF NOT EXISTS sessions(id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id),kind TEXT,topic TEXT,payload TEXT,created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)",
                "CREATE TABLE IF NOT EXISTS answers(id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id),quiz_id BIGINT REFERENCES sessions(id),question_index INTEGER,topic TEXT,correct INTEGER,created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,quiz_id,question_index))",
                "CREATE TABLE IF NOT EXISTS cards(id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id),topic TEXT,front TEXT,back TEXT,interval_days INTEGER DEFAULT 0,repetitions INTEGER DEFAULT 0,due TEXT,UNIQUE(user_id,front))",
                "CREATE TABLE IF NOT EXISTS reminders(id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id),day TEXT,message TEXT,UNIQUE(user_id,day))",
            )
            for statement in schema:
                c.execute(statement)
        return

    with db() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), name TEXT, text TEXT);
        CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), kind TEXT, topic TEXT, payload TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), quiz_id INTEGER REFERENCES sessions(id), question_index INTEGER, topic TEXT, correct INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, quiz_id, question_index));
        CREATE TABLE IF NOT EXISTS cards(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), topic TEXT, front TEXT, back TEXT, interval_days INTEGER DEFAULT 0, repetitions INTEGER DEFAULT 0, due TEXT, UNIQUE(user_id, front));
        CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), day TEXT, message TEXT, UNIQUE(user_id, day));
        """)
