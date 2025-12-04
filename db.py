# db.py
import sqlite3
import os
from datetime import datetime
from flask import g, current_app
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    if "db" not in g:
        os.makedirs(current_app.instance_path, exist_ok=True)
        db_path = os.path.join(current_app.instance_path, "app.db")
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _ensure_column(db, table_name: str, column_name: str, column_def_sql: str):
    """
    Eğer tabloya ait column yoksa: ALTER TABLE ... ADD COLUMN yapar.
    column_def_sql: "INTEGER NOT NULL DEFAULT 0" gibi.
    """
    cur = db.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cur.fetchall()]  # row[1] = name
    if column_name not in cols:
        db.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {column_def_sql}"
        )
        db.commit()


def init_db():
    db = get_db()

    # ---- detections tablosu ----
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            person_count INTEGER NOT NULL
            -- vehicle_count sonradan eklenecek (migration ile)
        );
        """
    )
    db.commit()

    # vehicle_count kolonu yoksa ekle
    _ensure_column(db, "detections", "vehicle_count", "INTEGER NOT NULL DEFAULT 0")

    # ---- users tablosu ----
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        );
        """
    )
    db.commit()

    # Eğer hiç user yoksa default admin & demo kullanıcılarını ekle
    cur = db.execute("SELECT COUNT(*) AS cnt FROM users")
    cnt = cur.fetchone()["cnt"]
    if cnt == 0:
        # admin / Admin123
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("Admin123"), "admin"),
        )
        # demo / Demo123
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("demo", generate_password_hash("Demo123"), "user"),
        )
        db.commit()


# ---------- Detection log fonksiyonları ----------

def log_detection(person_count: int, vehicle_count: int):
    db = get_db()
    ts = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO detections (ts, person_count, vehicle_count) VALUES (?, ?, ?)",
        (ts, person_count, vehicle_count),
    )
    db.commit()


def get_recent_detections(limit: int = 50):
    db = get_db()
    cur = db.execute(
        "SELECT ts, person_count, vehicle_count FROM detections "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return cur.fetchall()


# ---------- User yönetimi fonksiyonları ----------

def get_user_by_username(username: str):
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    return row


def verify_user(username: str, password: str):
    row = get_user_by_username(username)
    if row is None:
        return None
    if check_password_hash(row["password_hash"], password):
        return row
    return None


def get_all_users():
    db = get_db()
    cur = db.execute(
        "SELECT id, username, role FROM users ORDER BY username ASC"
    )
    return cur.fetchall()


def get_user_by_id(user_id: int):
    db = get_db()
    cur = db.execute(
        "SELECT id, username, role FROM users WHERE id = ?",
        (user_id,),
    )
    return cur.fetchone()


def create_user(username: str, password: str, role: str):
    db = get_db()
    pwd_hash = generate_password_hash(password)
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, pwd_hash, role),
    )
    db.commit()


def update_user(user_id: int, username: str, password: str | None, role: str):
    db = get_db()
    if password:
        pwd_hash = generate_password_hash(password)
        db.execute(
            "UPDATE users SET username = ?, password_hash = ?, role = ? "
            "WHERE id = ?",
            (username, pwd_hash, role, user_id),
        )
    else:
        db.execute(
            "UPDATE users SET username = ?, role = ? WHERE id = ?",
            (username, role, user_id),
        )
    db.commit()


def delete_user(user_id: int):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
