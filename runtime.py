"""Runtime de Milo: conversación general y agente de desarrollo."""

from __future__ import annotations

from openai import OpenAI

from agent import Agent
from subagents import build_team_prompt, detect_specialists

TECHNICAL_MARKERS = (
    "programa", "programar", "programación", "programacion", "código", "codigo", "archivo", "archivos",
    "proyecto", "app", "aplicación", "aplicacion", "software", "script", "bug", "error", "corrige",
    "corregir", "arregla", "arreglar", "repara", "reparar", "implementa", "implementar", "modifica",
    "modificar", "python", "pygame", "javascript", "typescript", "html", "css", "react", "node", "java",
    "c++", "c#", "rust", "go", "php", "sql", "api", "web", "frontend", "backend", "servidor", "terminal",
    "npm", "pip", "github", "juego", "videojuego", "interfaz", "ui", "base de datos", "database", "json", "bot",
    "asistente ia", "asistente de ia", "inteligencia artificial", "automatización", "automatizacion",
)

BUILD_MARKERS = (
    "crea un", "creame un", "créame un", "haz un", "hazme un", "construye un", "desarrolla un", "programa un",
    "implementa un", "crear un", "hacer un", "desarrollar un", "construir un", "crea la", "creame la", "créame la",
    "haz la", "hazme la", "construye la", "desarrolla la", "programa la", "crea los archivos", "creame los archivos",
    "créame los archivos", "crea una aplicación", "crea una app", "crea un juego", "crea un programa", "crea un asistente",
)

GENERAL_ONLY = (
    "hola", "buenas", "buenos días", "buenos dias", "buenas tardes", "buenas noches", "gracias", "qué tal", "que tal",
    "quién eres", "quien eres", "cómo estás", "como estas", "qué puedes hacer", "que puedes hacer",
)

IMPLEMENTATION_TOOLS = {"write_file", "replace_in_file", "append_file", "make_directory", "delete_file"}


def looks_like_programming(text: str, history: list[dict]) -> bool:
    value = text.lower().strip()
    if not value:
        return False
    if any(marker in value for marker in GENERAL_ONLY) and len(value.split()) <= 8:
        return False
    if any(marker in value for marker in BUILD_MARKERS) or any(marker in value for marker in TECHNICAL_MARKERS):
        return True
    recent = " ".join(str(item.get("content", "")) for item in history[-4:] if item.get("role") == "user").lower()
    return any(marker in recent for marker in TECHNICAL_MARKERS)


def requests_implementation(text: str) -> bool:
    return any(marker in text.lower().strip() for marker in BUILD_MARKERS)


def general_instructions(settings: dict) -> str:
    language = settings.get("language", "Español")
    personality = settings.get("personality", "Preciso")
    return f"""Eres Milo, un asistente general local. Idioma: {language}. Personalidad: {personality}.

Puedes conversar, responder preguntas, explicar conceptos, ayudar a estudiar, analizar ideas y también programar y desarrollar software.
No conviertas cada mensaje en una tarea de programación. Si el usuario saluda o hace una pregunta sencilla, responde directamente.
Adapta la profundidad a la petición y no hagas respuestas enormes para preguntas simples.
No afirmes haber ejecutado acciones, creado archivos o comprobado cosas si no las has hecho realmente."""


def developer_instructions(settings: dict, implementation_required: bool) -> str:
    language = settings.get("language", "Español")
    personality = settings.get("personality", "Preciso")
    completion_rule = """
IMPLEMENTACIÓN OBLIGATORIA:
El usuario pidió construir software. No termines después de crear una carpeta.
Después de create_project debes crear los archivos reales necesarios y escribir código funcional.
Si pide un asistente IA en Python, crea un asistente IA en Python. Si pide un juego de carreras, crea un juego de carreras. Si pide otra cosa, crea exactamente esa otra cosa.
""" if implementation_required else """
Haz exactamente la operación solicitada y no inventes un proyecto adicional.
"""
    return f"""Eres Milo, un asistente general local con nivel de ingeniería senior y una especialización fuerte en desarrollo de software. Idioma: {language}. Personalidad: {personality}.

PRINCIPIO CENTRAL
La petición ACTUAL es la única fuente de verdad sobre el producto.
NO uses ejemplos anteriores como plantilla del producto actual.
NO arrastres el dominio, género, arquitectura, nombre o sistemas de un proyecto anterior a una petición nueva.
{completion_rule}

MODO SENIOR
- Entiende los requisitos actuales y planifica internamente antes de actuar.
- Inspecciona los archivos existentes cuando modifiques un proyecto.
- Elige arquitectura, módulos y dependencias según el software solicitado, nunca según una plantilla fija.
- Escribe código real, completo y coherente; no archivos vacíos ni complejidad falsa.
- Si necesita varios archivos, crea todos los necesarios: entrada, módulos, configuración, recursos, tests y documentación cuando corresponda.
- Mantén separación de responsabilidades, manejo de errores, configuración clara y estructura escalable.
- Para interfaces cuida UX, estados, feedback y escalado.
- Para juegos implementa solo los sistemas que correspondan al juego solicitado.
- Para herramientas, APIs, servidores, automatizaciones o asistentes implementa la lógica real correspondiente.

PROCESO
Comprender → explorar → determinar/crear proyecto → implementar archivos → validar → probar → reparar → validar de nuevo → responder.

REGLAS DE ARCHIVOS
- create_project solo crea la raíz; NO cuenta como implementación completa.
- Después de create_project usa write_file para crear los archivos reales.
- Todos los archivos del proyecto quedan dentro de su carpeta raíz.
- No crees otro proyecto paralelo para corregir uno existente.
- No borres archivos funcionales sin razón técnica o petición explícita.

VERIFICACIÓN
- No digas "creado", "funciona", "corregido" o "terminado" por intuición.
- Si una herramienta devuelve ERROR, corrige la causa y vuelve a probar.
- Si necesitas más iteraciones, continúa trabajando.
- No inventes APIs, dependencias, assets, resultados ni pruebas.

OpenCode es auxiliar y opcional. Si no está instalado, trabaja normalmente con las herramientas propias de Milo."""


def _history_messages(history: list[dict], request: str) -> list[dict]:
    messages = [{"role": item["role"], "content": item["content"]} for item in history if item.get("role") in {"user", "assistant"}]
    messages.append({"role": "user", "content": request})
    return messages


def run_request(*, history, request, settings, workspace, model, base_url, api_key, progress, tool_result):
    client = OpenAI(base_url=base_url, api_key=api_key)
    programming = looks_like_programming(request, history)

    if not programming:
        progress("Conversación general · respuesta directa")
        response = client.responses.create(model=model, input=_history_messages(history, request), tools=[], instructions=general_instructions(settings))
        return getattr(response, "output_text", "") or "No hubo una respuesta útil del modelo.", "General"

    agent = Agent(workspace=workspace, on_tool_result=tool_result)
    agent.messages = _history_messages(history, request)
    listing = agent.list_files(".", recursive=True)
    if not listing.get("ok"):
        raise RuntimeError(listing.get("error", "No se pudo inspeccionar el workspace."))

    files = [item["path"] for item in listing.get("files", []) if item.get("type") == "file"]
    team = detect_specialists(files, request)
    implementation_required = requests_implementation(request)
    instructions = developer_instructions(settings, implementation_required) + "\n\n" + build_team_prompt(team)
    progress(f"Modo desarrollo · {', '.join(item.name for item in team)}")

    max_rounds = 40
    previous_signature = None
    repeated_signature_count = 0
    had_implementation = False

    for round_number in range(max_rounds):
        progress(f"Iteración {round_number + 1} · analizando y trabajando…")
        response = client.responses.create(model=model, input=agent.messages, tools=agent.tools, instructions=instructions)
        calls, text = agent.process_response(response)

        if not calls:
            if implementation_required and not had_implementation:
                agent.messages.append({"role": "user", "content": "La implementación todavía no está hecha. No cierres la tarea. Revisa el proyecto y usa las herramientas para crear los archivos y el código solicitado. Continúa hasta tener una implementación real y validada."})
                continue
            return text or getattr(response, "output_text", "") or "No hubo una respuesta útil del modelo.", ", ".join(item.name for item in team)

        names = [getattr(call, "name", "") for call in calls]
        if any(name in IMPLEMENTATION_TOOLS for name in names):
            had_implementation = True
        signature = tuple((getattr(call, "name", ""), getattr(call, "arguments", "")) for call in calls)
        repeated_signature_count = repeated_signature_count + 1 if signature == previous_signature else 0
        previous_signature = signature
        agent.add_tool_outputs(calls)

        if implementation_required and "create_project" in names and not had_implementation:
            agent.messages.append({"role": "user", "content": "La carpeta raíz ya existe. Ahora implementa el proyecto dentro de ella: crea los archivos reales, escribe el código completo y valida el resultado. No respondas todavía."})

        if repeated_signature_count >= 3:
            agent.messages.append({"role": "user", "content": "Estás repitiendo la misma acción sin avanzar. Inspecciona el estado real de los archivos, cambia de estrategia y completa la implementación pendiente."})
            repeated_signature_count = 0

    return "La tarea necesita más trabajo después de 40 iteraciones. Milo detuvo el ciclo para no bloquear la aplicación; puedes continuar con otra petición.", ", ".join(item.name for item in team)
