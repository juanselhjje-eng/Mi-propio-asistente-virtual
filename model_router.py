"""Enrutamiento de modelos sin depender de APIs de pago.

Milo funciona primero con Ollama/local. Los proveedores externos son opcionales.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    model: str
    base_url: str
    requires_api_key: bool = False
    role: str = "general"


class ModelRouter:
    """Selecciona el modelo según la tarea sin acoplar Milo a un proveedor."""

    def __init__(self):
        local_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        local_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.profiles = {
            "local": ModelProfile("Ollama local", "ollama", local_model, local_url, False, "general"),
            "coder": ModelProfile(
                "Ollama coder", "ollama", os.getenv("OLLAMA_CODER_MODEL", "qwen3-coder:30b"), local_url, False, "coding"
            ),
        }

    def choose(self, task: str = "general", prefer_local: bool = True) -> ModelProfile:
        task = (task or "general").lower()
        if prefer_local and any(word in task for word in ("código", "codigo", "program", "debug", "error", "refactor", "proyecto")):
            return self.profiles["coder"]
        return self.profiles["local"]

    def available_profiles(self) -> list[dict]:
        return [profile.__dict__.copy() for profile in self.profiles.values()]
