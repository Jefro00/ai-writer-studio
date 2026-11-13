"""SQLite-backed durable drafts and research sessions."""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from datetime import datetime

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "studio.sqlite3"


class Storage:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path or os.environ.get("DATABASE_PATH", DEFAULT_DB))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS research_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT '',
                style TEXT NOT NULL DEFAULT '',
                content_format TEXT NOT NULL DEFAULT 'X Article',
                analysis TEXT NOT NULL DEFAULT '',
                strategy TEXT NOT NULL DEFAULT '',
                article TEXT NOT NULL DEFAULT '',
                sources_json TEXT NOT NULL DEFAULT '[]',
                checks_json TEXT NOT NULL DEFAULT '[]',
                infographics_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'draft',
                published_url TEXT NOT NULL DEFAULT ''
            )""")
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(research_sessions)")}
            if "infographics_json" not in columns:
                conn.execute("ALTER TABLE research_sessions ADD COLUMN infographics_json TEXT NOT NULL DEFAULT '[]'")

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _load(row) -> dict:
        item = dict(row)
        item["sources"] = json.loads(item.pop("sources_json") or "[]")
        item["fact_checks"] = json.loads(item.pop("checks_json") or "[]")
        item["infographics"] = json.loads(item.pop("infographics_json", "[]") or "[]")
        return item

    def save_session(self, data: dict, session_id: int | None = None) -> int:
        now = str(data.get("updated_at") or data.get("created_at") or datetime.now().astimezone().isoformat(timespec="seconds"))
        fields = (data.get("topic", ""), str(data.get("created_at") or now), now, data.get("language", ""), data.get("style", ""),
                  data.get("content_format", "X Article"), data.get("analysis", ""), data.get("strategy", ""), data.get("article", ""),
                  self._dump(data.get("sources", [])), self._dump(data.get("fact_checks", [])),
                  self._dump(data.get("infographics", [])), data.get("status", "draft"), data.get("published_url", ""))
        with self._connect() as conn:
            if session_id:
                conn.execute("""UPDATE research_sessions SET topic=?,created_at=?,updated_at=?,language=?,style=?,content_format=?,analysis=?,strategy=?,article=?,sources_json=?,checks_json=?,infographics_json=?,status=?,published_url=? WHERE id=?""", fields + (session_id,))
                if conn.total_changes == 0:
                    raise KeyError(f"Сессия {session_id} не найдена")
                return session_id
            cur = conn.execute("""INSERT INTO research_sessions (topic,created_at,updated_at,language,style,content_format,analysis,strategy,article,sources_json,checks_json,infographics_json,status,published_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", fields)
            return int(cur.lastrowid)

    def get_session(self, session_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM research_sessions WHERE id=?", (session_id,)).fetchone()
        return self._load(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM research_sessions ORDER BY updated_at DESC,id DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
        return [self._load(row) for row in rows]

    def delete_session(self, session_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM research_sessions WHERE id=?", (session_id,))
