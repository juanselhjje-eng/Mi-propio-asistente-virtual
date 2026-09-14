"""Especialistas que el orquestador activa segun la peticion y el proyecto."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SubAgent:
    name: str
    role: str
    languages: tuple[str, ...]
    instructions: str


SUBAGENTS: Dict[str, SubAgent] = {
    "planner": SubAgent("planner", "Planificador y arquitecto", (), "Define objetivo, estructura minima, archivos, dependencias, interfaces y pruebas antes de construir."),
    "python": SubAgent("python", "Especialista Python", ("py",), "Escribe Python ejecutable, revisa imports y excepciones y valida sintaxis."),
    "pygame": SubAgent("pygame", "Especialista Pygame", ("py",), "Construye juegos 2D con pygame, separa recursos y logica y deja una base ejecutable."),
    "javascript": SubAgent("javascript", "Especialista JavaScript", ("js", "mjs", "cjs"), "Mantiene DOM, eventos, modulos y async/await coherentes con HTML y CSS."),
    "typescript": SubAgent("typescript", "Especialista TypeScript", ("ts", "tsx"), "Mantiene tipos, interfaces, imports y APIs coherentes."),
    "html": SubAgent("html", "Especialista HTML", ("html", "htm"), "Construye HTML semantico y comprueba ids y referencias a recursos."),
    "css": SubAgent("css", "Especialista CSS", ("css", "scss"), "Mantiene estilos organizados, responsive y coherentes con el HTML."),
    "java": SubAgent("java", "Especialista Java", ("java",), "Mantiene clases, paquetes, imports y firmas compilables."),
    "c_cpp": SubAgent("c_cpp", "Especialista C/C++", ("c", "h", "cpp", "hpp", "cc"), "Cuida headers, tipos, memoria, includes y firmas."),
    "csharp": SubAgent("csharp", "Especialista C#", ("cs",), "Mantiene namespaces, clases, tipos y referencias coherentes."),
    "php": SubAgent("php", "Especialista PHP", ("php",), "Mantiene sintaxis, rutas, formularios y logica del proyecto."),
    "sql": SubAgent("sql", "Especialista SQL", ("sql",), "Diseña tablas, relaciones, claves y consultas coherentes."),
    "rust": SubAgent("rust", "Especialista Rust", ("rs",), "Cuida ownership, borrowing, tipos, modulos y Cargo."),
    "go": SubAgent("go", "Especialista Go", ("go",), "Mantiene paquetes, imports, interfaces y errores coherentes."),
    "json": SubAgent("json", "Especialista configuracion", ("json", "yaml", "yml", "toml"), "Mantiene datos y configuracion validos y compatibles con el codigo."),
    "tester": SubAgent("tester", "Probador y depurador", (), "Revisa el proyecto completo y corrige errores basandose en evidencia real."),
}

REQUEST_KEYWORDS = {
    "python": ("python", ".py"),
    "pygame": ("pygame", "juego 2d con python"),
    "javascript": ("javascript", "js", "node.js", "nodejs"),
    "typescript": ("typescript", "tsx", "ts "),
    "html": ("html", "pagina web", "web"),
    "css": ("css", "estilos"),
    "java": ("java",),
    "c_cpp": ("c++", "cpp", "c/c++", " c ", ".c"),
    "csharp": ("c#", "csharp", ".cs"),
    "php": ("php",),
    "sql": ("sql", "mysql", "postgres", "postgresql"),
    "rust": ("rust", "cargo"),
    "go": ("golang", "go ", ".go"),
    "json": ("json", "yaml", "yml", "toml"),
}


def _matches(text: str, keyword: str) -> bool:
    if keyword.startswith(".") or keyword.endswith(" ") or keyword.startswith(" "):
        return keyword in text
    return keyword in text


def detect_specialists(files: List[str], request: str = "") -> List[SubAgent]:
    text = f" {request.lower()} "
    suffixes = {path.rsplit(".", 1)[-1].lower() for path in files if "." in path}
    selected = [SUBAGENTS["planner"]]

    for name, keywords in REQUEST_KEYWORDS.items():
        if any(_matches(text, word.lower()) for word in keywords):
            selected.append(SUBAGENTS[name])

    for name, agent in SUBAGENTS.items():
        if name in {"planner", "tester"}:
            continue
        if suffixes.intersection(agent.languages):
            selected.append(agent)

    if any(word in text for word in ("juego", "game", "app", "aplicacion", "pagina", "web", "creame", "crear")):
        selected.append(SUBAGENTS["tester"])
    elif not any(word in text for word in ("explica", "pregunta", "que es")):
        selected.append(SUBAGENTS["tester"])

    unique = []
    seen = set()
    for agent in selected:
        if agent.name not in seen:
            seen.add(agent.name)
            unique.append(agent)
    return unique


def build_team_prompt(agents: List[SubAgent]) -> str:
    lines = ["EQUIPO DE SUBAGENTES ACTIVO:"]
    for agent in agents:
        langs = ", ".join(agent.languages) or "general"
        lines.append(f"- {agent.name}: {agent.role} [{langs}] -> {agent.instructions}")
    return "\n".join(lines)
