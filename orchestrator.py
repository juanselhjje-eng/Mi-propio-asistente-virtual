"""Orquestación determinista inspirada en agentes Plan/Build/Review."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from subagents import SubAgent, detect_specialists


@dataclass
class Task:
    id: str
    title: str
    description: str
    agent: str = "build"
    status: str = "pending"
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ProjectPlan:
    goal: str
    workspace: str
    specialists: list[str]
    tasks: list[Task]
    files: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "workspace": self.workspace,
            "specialists": self.specialists,
            "tasks": [task.__dict__ for task in self.tasks],
            "files": self.files,
            "tests": self.tests,
        }


class ProjectOrchestrator:
    """Construye un plan corto sin obligar al modelo a hacer llamadas extra."""

    def __init__(self, workspace: str):
        self.workspace = workspace

    def plan(self, request: str, files: list[str]) -> ProjectPlan:
        specialists: list[SubAgent] = detect_specialists(files, request)
        names = [agent.name for agent in specialists]
        tasks = [
            Task("explore", "Explorar proyecto", "Inspeccionar estructura y archivos relevantes.", "explore"),
            Task("build", "Construir", "Crear o modificar el proyecto con el especialista apropiado.", "build", dependencies=["explore"]),
            Task("test", "Comprobar", "Validar sintaxis, referencias y ejecución segura.", "tester", dependencies=["build"]),
        ]
        return ProjectPlan(
            goal=request,
            workspace=self.workspace,
            specialists=names,
            tasks=tasks,
            tests=["validate_project cuando haya varios archivos", "validate_python para Python", "ejecución segura cuando sea posible"],
        )

    @staticmethod
    def next_tasks(plan: ProjectPlan) -> list[Task]:
        completed = {task.id for task in plan.tasks if task.status == "done"}
        return [task for task in plan.tasks if task.status == "pending" and all(dep in completed for dep in task.dependencies)]
