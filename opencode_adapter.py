"""Puente opcional con OpenCode CLI.

JARVIS no depende de OpenCode para funcionar. Si el ejecutable existe, esta
capa permite consultar su disponibilidad y ejecutar una sesión explícita en
el workspace. La ejecución no se dispara automáticamente desde prompts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class OpenCodeAdapter:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()
        self.executable = shutil.which("opencode")

    @property
    def available(self) -> bool:
        return self.executable is not None

    def version(self) -> str:
        if not self.available:
            return "OpenCode no está instalado"
        result = subprocess.run([self.executable, "--version"], cwd=self.workspace, capture_output=True, text=True, timeout=8)
        return (result.stdout or result.stderr).strip() or "versión desconocida"

    def build_command(self, prompt: str) -> list[str]:
        if not self.available:
            raise RuntimeError("OpenCode no está instalado o no está en PATH")
        if not prompt.strip():
            raise ValueError("El prompt de OpenCode no puede estar vacío")
        return [self.executable, prompt]

    def run(self, prompt: str, timeout: int = 120) -> dict:
        command = self.build_command(prompt)
        timeout = max(5, min(int(timeout), 600))
        try:
            result = subprocess.run(command, cwd=self.workspace, capture_output=True, text=True, timeout=timeout)
            return {
                "ok": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout[-12000:],
                "stderr": result.stderr[-12000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {"ok": False, "error": f"OpenCode superó {timeout}s", "stdout": str(exc.stdout or "")[-4000:], "stderr": str(exc.stderr or "")[-4000:]}
