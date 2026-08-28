"""SQLite storage for pages, widgets, themes and settings.

This is the single source of truth for the whole panel layout. Nothing here
requires the user to ever look at (let alone edit) the raw data - all access
happens through the editor UI. The schema is intentionally simple (JSON blobs
for widget/theme config) so that new widget types or properties never require
a migration.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "homepanel.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '',
    order_index INTEGER NOT NULL DEFAULT 0,
    bg_image_path TEXT NOT NULL DEFAULT '',
    bg_fit TEXT NOT NULL DEFAULT 'cover'
);

CREATE TABLE IF NOT EXISTS widgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    x REAL NOT NULL DEFAULT 0,
    y REAL NOT NULL DEFAULT 0,
    w REAL NOT NULL DEFAULT 200,
    h REAL NOT NULL DEFAULT 120,
    z INTEGER NOT NULL DEFAULT 0,
    config TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    config TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 0,
    built_in INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@dataclass
class Page:
    id: int
    name: str
    icon: str = ""
    order_index: int = 0
    bg_image_path: str = ""
    bg_fit: str = "cover"


@dataclass
class Widget:
    id: int
    page_id: int
    type: str
    x: float
    y: float
    w: float
    h: float
    z: int
    config: dict = field(default_factory=dict)


@dataclass
class Theme:
    id: int
    name: str
    config: dict
    is_active: bool
    built_in: bool = False


class Database:
    """Thin, dependency-free wrapper around the sqlite3 module."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._migrate_pages()
        self._ensure_defaults()

    # ------------------------------------------------------------------ #
    # bootstrap
    # ------------------------------------------------------------------ #
    def _migrate_pages(self) -> None:
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(pages)").fetchall()}
        if "bg_image_path" not in cols:
            self._conn.execute("ALTER TABLE pages ADD COLUMN bg_image_path TEXT NOT NULL DEFAULT ''")
        if "bg_fit" not in cols:
            self._conn.execute("ALTER TABLE pages ADD COLUMN bg_fit TEXT NOT NULL DEFAULT 'cover'")
        self._conn.commit()

    def _ensure_defaults(self) -> None:
        if not self.list_pages():
            self.create_page("Home", icon="home")
        if not self.list_themes():
            from app.ui.themes import BUILT_IN_THEMES

            for i, theme in enumerate(BUILT_IN_THEMES):
                self.save_theme(theme["name"], theme, set_active=(i == 0), built_in=True)

    # ------------------------------------------------------------------ #
    # pages
    # ------------------------------------------------------------------ #
    def list_pages(self) -> list[Page]:
        rows = self._conn.execute("SELECT * FROM pages ORDER BY order_index ASC, id ASC").fetchall()
        return [
            Page(
                id=r["id"], name=r["name"], icon=r["icon"], order_index=r["order_index"],
                bg_image_path=r["bg_image_path"], bg_fit=r["bg_fit"],
            )
            for r in rows
        ]

    def get_page(self, page_id: int) -> Optional[Page]:
        row = self._conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        if not row:
            return None
        return Page(
            id=row["id"], name=row["name"], icon=row["icon"], order_index=row["order_index"],
            bg_image_path=row["bg_image_path"], bg_fit=row["bg_fit"],
        )

    def create_page(self, name: str, icon: str = "", order_index: Optional[int] = None,
                     bg_image_path: str = "", bg_fit: str = "cover") -> Page:
        if order_index is None:
            order_index = len(self.list_pages())
        cur = self._conn.execute(
            "INSERT INTO pages (name, icon, order_index, bg_image_path, bg_fit) VALUES (?, ?, ?, ?, ?)",
            (name, icon, order_index, bg_image_path, bg_fit),
        )
        self._conn.commit()
        return Page(id=cur.lastrowid, name=name, icon=icon, order_index=order_index,
                    bg_image_path=bg_image_path, bg_fit=bg_fit)

    def update_page(self, page_id: int, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._conn.execute(f"UPDATE pages SET {cols} WHERE id = ?", (*fields.values(), page_id))
        self._conn.commit()

    def delete_page(self, page_id: int) -> None:
        self._conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        self._conn.commit()

    def reorder_pages(self, page_ids_in_order: list[int]) -> None:
        for idx, pid in enumerate(page_ids_in_order):
            self._conn.execute("UPDATE pages SET order_index = ? WHERE id = ?", (idx, pid))
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # widgets
    # ------------------------------------------------------------------ #
    def list_widgets(self, page_id: int) -> list[Widget]:
        rows = self._conn.execute(
            "SELECT * FROM widgets WHERE page_id = ? ORDER BY z ASC, id ASC", (page_id,)
        ).fetchall()
        return [self._row_to_widget(r) for r in rows]

    def get_widget(self, widget_id: int) -> Optional[Widget]:
        row = self._conn.execute("SELECT * FROM widgets WHERE id = ?", (widget_id,)).fetchone()
        return self._row_to_widget(row) if row else None

    def create_widget(
        self, page_id: int, wtype: str, x: float, y: float, w: float, h: float, config: Optional[dict] = None, z: Optional[int] = None
    ) -> Widget:
        if z is None:
            z = len(self.list_widgets(page_id))
        cfg = json.dumps(config or {})
        cur = self._conn.execute(
            "INSERT INTO widgets (page_id, type, x, y, w, h, z, config) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (page_id, wtype, x, y, w, h, z, cfg),
        )
        self._conn.commit()
        return Widget(id=cur.lastrowid, page_id=page_id, type=wtype, x=x, y=y, w=w, h=h, z=z, config=config or {})

    def update_widget(self, widget_id: int, **fields: Any) -> None:
        if not fields:
            return
        if "config" in fields and isinstance(fields["config"], dict):
            fields["config"] = json.dumps(fields["config"])
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._conn.execute(f"UPDATE widgets SET {cols} WHERE id = ?", (*fields.values(), widget_id))
        self._conn.commit()

    def delete_widget(self, widget_id: int) -> None:
        self._conn.execute("DELETE FROM widgets WHERE id = ?", (widget_id,))
        self._conn.commit()

    def duplicate_widget(self, widget_id: int, offset: float = 20) -> Optional[Widget]:
        w = self.get_widget(widget_id)
        if not w:
            return None
        return self.create_widget(w.page_id, w.type, w.x + offset, w.y + offset, w.w, w.h, dict(w.config))

    def _row_to_widget(self, row: sqlite3.Row) -> Widget:
        return Widget(
            id=row["id"], page_id=row["page_id"], type=row["type"],
            x=row["x"], y=row["y"], w=row["w"], h=row["h"], z=row["z"],
            config=json.loads(row["config"] or "{}"),
        )

    # ------------------------------------------------------------------ #
    # themes
    # ------------------------------------------------------------------ #
    def list_themes(self) -> list[Theme]:
        rows = self._conn.execute("SELECT * FROM themes ORDER BY built_in DESC, id ASC").fetchall()
        return [self._row_to_theme(r) for r in rows]

    def get_active_theme(self) -> Optional[Theme]:
        row = self._conn.execute("SELECT * FROM themes WHERE is_active = 1 LIMIT 1").fetchone()
        return self._row_to_theme(row) if row else None

    def save_theme(self, name: str, config: dict, set_active: bool = False, built_in: bool = False) -> Theme:
        existing = self._conn.execute("SELECT id FROM themes WHERE name = ?", (name,)).fetchone()
        cfg = json.dumps(config)
        if existing:
            self._conn.execute("UPDATE themes SET config = ? WHERE id = ?", (cfg, existing["id"]))
            theme_id = existing["id"]
        else:
            cur = self._conn.execute(
                "INSERT INTO themes (name, config, is_active, built_in) VALUES (?, ?, 0, ?)",
                (name, cfg, int(built_in)),
            )
            theme_id = cur.lastrowid
        if set_active:
            self.set_active_theme(theme_id)
        self._conn.commit()
        return Theme(id=theme_id, name=name, config=config, is_active=set_active, built_in=built_in)

    def set_active_theme(self, theme_id: int) -> None:
        self._conn.execute("UPDATE themes SET is_active = 0")
        self._conn.execute("UPDATE themes SET is_active = 1 WHERE id = ?", (theme_id,))
        self._conn.commit()

    def delete_theme(self, theme_id: int) -> None:
        self._conn.execute("DELETE FROM themes WHERE id = ? AND built_in = 0", (theme_id,))
        self._conn.commit()

    def _row_to_theme(self, row: sqlite3.Row) -> Theme:
        return Theme(
            id=row["id"], name=row["name"], config=json.loads(row["config"] or "{}"),
            is_active=bool(row["is_active"]), built_in=bool(row["built_in"]),
        )

    # ------------------------------------------------------------------ #
    # settings (key/value, e.g. HA url, token, language, edit pin)
    # ------------------------------------------------------------------ #
    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            return row["value"]

    def set_setting(self, key: str, value: Any) -> None:
        v = json.dumps(value)
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, v),
        )
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # backup / export / import
    # ------------------------------------------------------------------ #
    def backup_to_file(self, dest_path: Path) -> Path:
        """Full binary snapshot of the sqlite file (includes everything)."""
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn.commit()
        backup_conn = sqlite3.connect(str(dest_path))
        with backup_conn:
            self._conn.backup(backup_conn)
        backup_conn.close()
        return dest_path

    def restore_from_file(self, src_path: Path) -> None:
        src_path = Path(src_path)
        self._conn.close()
        shutil.copyfile(src_path, self.path)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def export_config(self, include_secrets: bool = False) -> dict:
        """Human-portable JSON export of layout/themes (and optionally secrets)."""
        settings = {}
        for row in self._conn.execute("SELECT key, value FROM settings"):
            if not include_secrets and row["key"] in ("ha_token",):
                continue
            settings[row["key"]] = json.loads(row["value"]) if row["value"] else None
        return {
            "exported_at": time.time(),
            "pages": [p.__dict__ for p in self.list_pages()],
            "widgets": [w.__dict__ for w in [self._row_to_widget(r) for r in self._conn.execute("SELECT * FROM widgets")]],
            "themes": [t.__dict__ for t in self.list_themes()],
            "settings": settings,
        }

    def import_config(self, data: dict, replace: bool = True) -> None:
        if replace:
            self._conn.execute("DELETE FROM widgets")
            self._conn.execute("DELETE FROM pages")
        id_map: dict[int, int] = {}
        for p in data.get("pages", []):
            new_page = self.create_page(
                p["name"], icon=p.get("icon", ""), order_index=p.get("order_index", 0),
                bg_image_path=p.get("bg_image_path", ""), bg_fit=p.get("bg_fit", "cover"),
            )
            id_map[p["id"]] = new_page.id
        for w in data.get("widgets", []):
            page_id = id_map.get(w["page_id"], w["page_id"])
            self.create_widget(page_id, w["type"], w["x"], w["y"], w["w"], w["h"], w.get("config", {}), z=w.get("z"))
        for t in data.get("themes", []):
            self.save_theme(t["name"], t["config"], set_active=t.get("is_active", False))
        for k, v in data.get("settings", {}).items():
            self.set_setting(k, v)

    def close(self) -> None:
        self._conn.close()
