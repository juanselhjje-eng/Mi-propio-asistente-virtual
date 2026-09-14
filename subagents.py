"""Subagentes especializados para el asistente local.

Cada subagente tiene una responsabilidad concreta. El orquestador selecciona
el especialista según el tipo de proyecto antes de generar codigo.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SubAgent:
    name: str
    role: str
    languages: tuple[str, ...]
    instructions: str


SUBAGENTS: Dict[str, SubAgent] = {
    "planner": SubAgent(
        "planner", "Planificador y arquitecto", (),
        "Divide la peticion en tareas pequenas, define archivos, dependencias, interfaces y pruebas. No escribe codigo hasta tener un plan minimo."
    ),
    "python": SubAgent(
        "python", "Especialista Python", ("py",),
        "Escribe Python idiomatico, simple y ejecutable. Revisa imports, tipos de datos, excepciones y valida sintaxis antes de terminar."
    ),
    "javascript": SubAgent(
        "javascript", "Especialista JavaScript", ("js", "mjs", "cjs"),
        "Comprueba DOM, eventos, imports, async/await y nombres de funciones. Mantiene el JavaScript compatible con el HTML y CSS del proyecto."
    ),
    "typescript": SubAgent(
        "typescript", "Especialista TypeScript", ("ts", "tsx"),
        "Mantiene tipos coherentes, interfaces y imports. Evita usar any sin necesidad y comprueba que las APIs utilizadas existan."
    ),
    "html": SubAgent(
        "html", "Especialista HTML", ("html", "htm"),
        "Construye HTML semantico y accesible. Comprueba ids, rutas de scripts, enlaces y elementos referenciados por JavaScript."
    ),
    "css": SubAgent(
        "css", "Especialista CSS", ("css", "scss"),
        "Organiza estilos sin duplicacion innecesaria y comprueba selectores, clases, ids, responsive y compatibilidad con el HTML."
    ),
    "java": SubAgent(
        "java", "Especialista Java", ("java",),
        "Mantiene clases, paquetes, imports, tipos y firmas coherentes. Evita APIs inexistentes y estructura el proyecto de forma compilable."
    ),
    "c_cpp": SubAgent(
        "c_cpp", "Especialista C/C++", ("c", "h", "cpp", "hpp", "cc"),
        "Cuida headers, tipos, memoria, includes y firmas. Prefiere implementaciones pequenas y comprobables."
    ),
    "csharp": SubAgent(
        "csharp", "Especialista C#", ("cs",),
        "Mantiene namespaces, clases, tipos y referencias coherentes y evita APIs inventadas."
    ),
    "php": SubAgent(
        "php", "Especialista PHP", ("php",),
        "Mantiene sintaxis PHP, rutas, funciones y formularios coherentes. Evita mezclar PHP con logica JavaScript incorrectamente."
    ),
    "sql": SubAgent(
        "sql", "Especialista SQL", ("sql",),
        "Diseña tablas, claves, relaciones y consultas coherentes. Comprueba nombres de columnas y parametros."
    ),
    "rust": SubAgent(
        "rust", "Especialista Rust", ("rs",),
        "Cuida ownership, borrowing, tipos, modulos y dependencias de Cargo."
    ),
    "go": SubAgent(
        "go", "Especialista Go", ("go",),
        "Mantiene paquetes, imports, interfaces y manejo de errores idiomatico."
    ),
    "json": SubAgent(
        "json", "Especialista datos/configuracion", ("json", "yaml", "yml", "toml"),
        "Mantiene estructuras validas y compatibles con el codigo que las consume."
    ),
    "ml": SubAgent(
        "ml", "Especialista redes neuronales", ("py", "json", "npz"),
        "Diseña datasets, arquitectura, entrenamiento, validacion y evaluacion. No inventa metricas: mide resultados reales."
    ),
    "tester": SubAgent(
        "tester", "Probador y depurador", (),
        "Busca errores de sintaxis, imports, rutas, referencias cruzadas y fallos de ejecucion. Propone correcciones basadas en evidencia."
    ),
}


def detect_specialists(files: List[str], request: str = "") -> List[SubAgent]:
    """Selecciona especialistas por archivos y por palabras clave de la peticion."""
    selected = [SUBAGENTS["planner"]]
    suffixes = {path.rsplit(".", 1)[-1].lower() for path in files if "." in path}
    text = request.lower()

    if any(word in text for word in ("neuronal", "red neuronal", "entrenar", "machine learning", "ia")):
        selected.append(SUBAGENTS["ml"])

    for agent in SUBAGENTS.values():
        if agent.name in {"planner", "ml", "tester"}:
            continue
        if suffixes.intersection(agent.languages):
            selected.append(agent)

    if not any(word in text for word in ("solo", "explica", "pregunta")):
        selected.append(SUBAGENTS["tester"])

    # Elimina duplicados conservando orden.
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
