"""Punto de integración de la arquitectura profesional de Milo."""

from __future__ import annotations

from orchestrator import ProjectOrchestrator
from permissions import PermissionPolicy
from project_state import ProjectState
from validators import ProjectValidator


class MiloRuntime:
    """Agrupa estado, planificación, permisos y validación para la UI/agente."""

    def __init__(self, workspace: str, data_dir: str = ".milo_data"):
        self.workspace = workspace
        self.orchestrator = ProjectOrchestrator(workspace)
        self.state = ProjectState(data_dir)
        self.validator = ProjectValidator()
        self.permissions = PermissionPolicy()

    def prepare(self, request: str, files: list[str]) -> dict:
        plan = self.orchestrator.plan(request, files)
        return plan.to_dict()

    def validate(self, project_directory: str) -> dict:
        return self.validator.validate(project_directory)

    def set_project(self, project_directory: str, goal: str = "") -> dict:
        return self.state.set_active(project_directory, goal)

    def checkpoint(self, project_directory: str, label: str = "checkpoint") -> dict:
        return self.state.snapshot(project_directory, label)
