"""Validaciones ligeras y agnósticas al lenguaje para el pipeline de Milo."""

from __future__ import annotations

import json
import re
from pathlib import Path


class ProjectValidator:
    def __init__(self, ignored: set[str] | None = None):
        self.ignored = ignored or {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}

    def validate(self, directory: str | Path) -> dict:
        root = Path(directory).resolve()
        if not root.is_dir():
            return {"ok": False, "errors": [f"No existe el directorio: {root}"]}
        errors: list[str] = []
        warnings: list[str] = []
        files = [p for p in root.rglob("*") if p.is_file() and not any(part in self.ignored for part in p.parts)]
        suffixes = {p.suffix.lower() for p in files}
        for path in files:
            if path.suffix.lower() == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    errors.append(f"JSON inválido: {path.relative_to(root)} · {exc}")
            if path.suffix.lower() in {".html", ".htm"}:
                text = path.read_text(encoding="utf-8", errors="replace")
                for src in re.findall(r'<(?:script|link)[^>]+(?:src|href)=["\']([^"\']+)', text, re.I):
                    if not src.startswith(("http://", "https://", "//", "data:", "#")):
                        candidate = (path.parent / src).resolve()
                        if not candidate.exists():
                            errors.append(f"Referencia local inexistente: {path.relative_to(root)} -> {src}")
        if not files:
            warnings.append("El proyecto no contiene archivos.")
        return {"ok": not errors, "errors": errors, "warnings": warnings, "file_count": len(files), "suffixes": sorted(suffixes)}
