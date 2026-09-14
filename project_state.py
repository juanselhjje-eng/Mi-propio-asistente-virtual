"""Estado persistente del proyecto activo y operaciones seguras de recuperación."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class ProjectState:
    def __init__(self, data_dir: str | Path = ".milo_data"):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "project_state.json"
        self.data = self._load()

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

    def set_active(self, project_path: str | Path, goal: str = "") -> dict:
        self.data["active_project"] = str(Path(project_path).resolve())
        self.data["goal"] = goal
        self.data["updated"] = datetime.now(timezone.utc).isoformat()
        self._save()
        return self.data.copy()

    def get_active(self) -> str | None:
        value = self.data.get("active_project")
        return value if value else None

    def snapshot(self, project_path: str | Path, label: str = "checkpoint") -> dict:
        source = Path(project_path).resolve()
        if not source.is_dir():
            return {"ok": False, "error": f"No existe el proyecto: {source}"}
        snapshots = self.root / "snapshots"
        snapshots.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label).strip("_") or "checkpoint"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = snapshots / f"{stamp}_{safe}"
        shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", ".venv", "venv", "node_modules", "__pycache__"))
        return {"ok": True, "path": str(target), "verified": target.is_dir()}
