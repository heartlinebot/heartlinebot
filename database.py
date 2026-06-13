import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "heartline.db")


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                first_name  TEXT,
                username    TEXT,
                city        TEXT DEFAULT '',
                send_mode   TEXT DEFAULT 'auto',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recipients (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                name           TEXT NOT NULL,
                relation       TEXT NOT NULL,
                contact        TEXT NOT NULL,
                tone           TEXT DEFAULT 'warm',
                schedule_days  TEXT DEFAULT 'everyday',
                schedule_time  TEXT DEFAULT '09:00',
                active         INTEGER DEFAULT 1,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS message_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                recipient_id INTEGER,
                message_text TEXT,
                status       TEXT DEFAULT 'sent',
                sent_at      TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    # ── USERS ──────────────────────────────────
    def save_user(self, user_id, first_name, username):
        self.conn.execute("""
            INSERT INTO users (id, first_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                first_name = excluded.first_name,
                username   = excluded.username
        """, (user_id, first_name, username))
        self.conn.commit()

    def get_user(self, user_id):
        row = self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_user_city(self, user_id, city):
        self.conn.execute(
            "UPDATE users SET city = ? WHERE id = ?", (city, user_id)
        )
        self.conn.commit()

    def update_send_mode(self, user_id, mode):
        self.conn.execute(
            "UPDATE users SET send_mode = ? WHERE id = ?", (mode, user_id)
        )
        self.conn.commit()

    # ── RECIPIENTS ─────────────────────────────
    def add_recipient(self, user_id, name, relation, contact, tone,
                      schedule_days, schedule_time):
        cur = self.conn.execute("""
            INSERT INTO recipients
                (user_id, name, relation, contact, tone, schedule_days, schedule_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, relation, contact, tone, schedule_days, schedule_time))
        self.conn.commit()
        return cur.lastrowid

    def get_recipients(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM recipients WHERE user_id = ? AND active = 1", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recipient(self, recipient_id):
        row = self.conn.execute(
            "SELECT * FROM recipients WHERE id = ?", (recipient_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_active_recipients(self):
        rows = self.conn.execute(
            "SELECT * FROM recipients WHERE active = 1"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_recipient(self, recipient_id):
        self.conn.execute(
            "UPDATE recipients SET active = 0 WHERE id = ?", (recipient_id,)
        )
        self.conn.commit()

    # ── LOG ────────────────────────────────────
    def log_message(self, user_id, recipient_id, text, status="sent"):
        self.conn.execute("""
            INSERT INTO message_log (user_id, recipient_id, message_text, status)
            VALUES (?, ?, ?, ?)
        """, (user_id, recipient_id, text, status))
        self.conn.commit()
