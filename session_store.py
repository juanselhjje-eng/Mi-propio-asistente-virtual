"""Persistencia ligera de sesiones y mensajes de Milo."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class SessionStore:
    def __init__(self, root: str | Path = ".milo_data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "sessions.json"
        self.data = self._load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def create(self, title: str = "Nueva conversación", workspace: str | None = None) -> dict:
        session_id = uuid.uuid4().hex[:12]
        session = {"id": session_id, "title": title, "created": self._now(), "updated": self._now(), "messages": [], "todo": [], "workspace": workspace, "active_project": None, "plan": None}
        self.data[session_id] = session
        self._save()
        return session

    def get(self, session_id: str) -> dict | None:
        return self.data.get(session_id)

    def list(self) -> list[dict]:
        return sorted(self.data.values(), key=lambda x: x.get("updated", ""), reverse=True)

    def append_message(self, session_id: str, role: str, content: str) -> dict:
        session = self.data[session_id]
        session["messages"].append({"role": role, "content": content, "time": self._now()})
        session["updated"] = self._now()
        self._save()
        return session

    def set_title(self, session_id: str, title: str) -> dict:
        session = self.data[session_id]
        session["title"] = title.strip()[:120] or "Nueva conversación"
        session["updated"] = self._now()
        self._save()
        return session

    def set_todo(self, session_id: str, todo: list[dict]) -> dict:
        session = self.data[session_id]
        session["todo"] = todo
        session["updated"] = self._now()
        self._save()
        return session

    def set_plan(self, session_id: str, plan: dict | None) -> dict:
        session = self.data[session_id]
        session["plan"] = plan
        session["updated"] = self._now()
        self._save()
        return session

    def set_active_project(self, session_id: str, project: str | None) -> dict:
        session = self.data[session_id]
        session["active_project"] = project
        session["updated"] = self._now()
        self._save()
        return session

    def delete(self, session_id: str) -> bool:
        existed = self.data.pop(session_id, None) is not None
        if existed:
            self._save()
        return existed
