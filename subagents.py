"""Especialistas mínimos activados por la petición actual de Milo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SubAgent:
    name: str
    role: str
    languages: tuple[str, ...]
    instructions: str


SUBAGENTS = {
    "python": SubAgent("python", "Python", ("py",), "Escribe Python ejecutable, imports coherentes y manejo de errores."),
    "pygame": SubAgent("pygame", "Pygame", ("py",), "Construye únicamente cuando el usuario pide Pygame; separa lógica, recursos e interfaz."),
    "javascript": SubAgent("javascript", "JavaScript", ("js", "mjs", "cjs"), "Mantiene módulos, DOM, eventos y asincronía coherentes."),
    "typescript": SubAgent("typescript", "TypeScript", ("ts", "tsx"), "Mantiene tipos, imports y APIs coherentes."),
    "html": SubAgent("html", "HTML", ("html", "htm"), "Construye HTML semántico y referencias locales válidas."),
    "css": SubAgent("css", "CSS", ("css", "scss"), "Mantiene estilos responsive y coherentes con la interfaz."),
    "java": SubAgent("java", "Java", ("java",), "Mantiene clases, paquetes e imports compilables."),
    "c_cpp": SubAgent("c_cpp", "C/C++", ("c", "h", "cpp", "hpp", "cc"), "Cuida headers, tipos, memoria e includes."),
    "csharp": SubAgent("csharp", "C#", ("cs",), "Mantiene namespaces, clases, tipos y referencias."),
    "php": SubAgent("php", "PHP", ("php",), "Mantiene sintaxis, rutas y lógica del proyecto."),
    "sql": SubAgent("sql", "SQL", ("sql",), "Diseña tablas, relaciones, claves y consultas coherentes."),
    "rust": SubAgent("rust", "Rust", ("rs",), "Cuida ownership, tipos, módulos y Cargo."),
    "go": SubAgent("go", "Go", ("go",), "Mantiene paquetes, imports, interfaces y errores."),
    "json": SubAgent("json", "Configuración", ("json", "yaml", "yml", "toml"), "Mantiene configuración y datos válidos."),
    "tester": SubAgent("tester", "Validación", (), "Busca errores reales, valida cambios y evita declarar éxito sin evidencia."),
}

REQUEST_KEYWORDS = {
    "python": ("python", ".py"), "pygame": ("pygame", "juego 2d con python"),
    "javascript": ("javascript", "node.js", "nodejs", " js "), "typescript": ("typescript", "tsx", " ts "),
    "html": ("html", "pagina web", "página web"), "css": ("css", "estilos"), "java": ("java",),
    "c_cpp": ("c++", "cpp", "c/c++", ".c"), "csharp": ("c#", "csharp", ".cs"), "php": ("php",),
    "sql": ("sql", "mysql", "postgres", "postgresql"), "rust": ("rust", "cargo"),
    "go": ("golang", ".go"), "json": ("json", "yaml", "yml", "toml"),
}


def detect_specialists(files=None, request=""):
    """Activa solo especialistas relacionados con la petición actual."""
    text = f" {request.lower()} "
    selected = []

    for name, keywords in REQUEST_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            selected.append(SUBAGENTS[name])

    if any(word in text for word in ("web", "pagina", "página", "html")):
        for name in ("html", "css"):
            if SUBAGENTS[name] not in selected:
                selected.append(SUBAGENTS[name])
        if "javascript" in text or "node" in text or " js " in text:
            selected.append(SUBAGENTS["javascript"])

    build_request = any(word in text for word in ("crea", "crear", "creame", "créame", "haz", "hazme", "construye", "desarrolla", "programa", "corrige", "arregla", "modifica", "implementa", "repara"))
    if build_request:
        selected.append(SUBAGENTS["tester"])

    unique = []
    seen = set()
    for agent in selected:
        if agent.name not in seen:
            seen.add(agent.name)
            unique.append(agent)
    return unique


def build_team_prompt(agents):
    if not agents:
        return "ESPECIALISTAS: ninguno adicional. Resuelve la petición directamente con el agente principal."
    lines = ["ESPECIALISTAS ACTIVOS PARA ESTA PETICIÓN:"]
    for agent in agents:
        langs = ", ".join(agent.languages) or "general"
        lines.append(f"- {agent.name}: {agent.role} [{langs}] -> {agent.instructions}")
    lines.append("No actives ni imites especialistas o dominios que no correspondan a la petición actual.")
    return "\n".join(lines)
