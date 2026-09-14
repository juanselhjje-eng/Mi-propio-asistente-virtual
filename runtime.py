from openai import OpenAI

from agent import Agent
from subagents import build_team_prompt, detect_specialists


PROGRAMMING_MARKERS = (
    "programa", "programar", "programación", "programacion", "código", "codigo",
    "archivo", "archivos", "proyecto", "app", "aplicación", "aplicacion", "software",
    "script", "bug", "error", "corrige", "corregir", "arregla", "arreglar", "repara",
    "reparar", "crea", "crear", "construye", "construir", "desarrolla", "desarrollar",
    "implementa", "implementar", "añade", "agrega", "modifica", "cambia", "python",
    "pygame", "javascript", "typescript", "html", "css", "react", "node", "java", "c++",
    "c#", "rust", "go", "php", "sql", "api", "web", "frontend", "backend", "servidor",
    "terminal", "dependencia", "dependencias", "npm", "pip", "github", "minecraft",
    "juego", "videojuego", "interfaz", "ui", "base de datos", "database", "json",
)

GENERAL_MARKERS = (
    "hola", "buenas", "buenos días", "buenos dias", "buenas tardes", "buenas noches",
    "gracias", "qué tal", "que tal", "quién eres", "quien eres", "cómo estás", "como estas",
    "ayuda", "explícame", "explicame", "qué puedes hacer", "que puedes hacer",
)


def _looks_like_programming(text, history):
    value = text.lower().strip()
    if not value:
        return False
    if any(marker in value for marker in PROGRAMMING_MARKERS):
        return True
    if any(marker in value for marker in GENERAL_MARKERS) and len(value.split()) <= 8:
        return False
    recent = " ".join(
        str(item.get("content", ""))
        for item in history[-4:]
        if item.get("role") == "user"
    ).lower()
    return any(marker in recent for marker in PROGRAMMING_MARKERS)


def _general_instructions(settings):
    language = settings.get("language", "Español")
    personality = settings.get("personality", "Preciso")
    return f"""Eres Milo, un asistente local general. Idioma: {language}. Personalidad: {personality}.

Puedes conversar, explicar conceptos, responder preguntas, ayudar a estudiar, razonar sobre ideas y también ayudar a programar y crear software.
No conviertas cada mensaje en una tarea de programación.
Si el usuario solo saluda, conversa de forma natural y responde directamente.
Sé claro, útil y relativamente breve cuando la pregunta sea sencilla.
No afirmes haber ejecutado acciones, creado archivos o comprobado cosas si no las has hecho realmente."""


def _developer_instructions(settings):
    language = settings.get("language", "Español")
    personality = settings.get("personality", "Preciso")
    return f"""Eres Milo, un asistente local general con un enfoque fuerte en desarrollo de software. Idioma: {language}. Personalidad: {personality}.

Puedes conversar normalmente, responder preguntas y explicar temas. Cuando el usuario pide crear, modificar, corregir o validar software, actúas como agente de desarrollo y usas las herramientas reales del workspace.

CREAR PROYECTOS:
- Cuando el usuario pida crear un juego/app/página/programa/proyecto, usa create_project con un nombre basado en lo pedido.
- Todos los archivos nuevos deben quedar dentro de la carpeta del proyecto.
- Crea una estructura completa y coherente, no un único archivo de ejemplo si el proyecto necesita varios.
- Elige la arquitectura según el tipo de software: juegos, desktop, web, API, automatización, servidor, librería, etc.
- Si faltan assets, crea la carpeta correspondiente y usa placeholders generados por código cuando sea posible.

CORREGIR:
- Si pide corregir/arreglar/modificar, inspecciona primero el proyecto existente y modifica esos archivos reales.
- No crees un proyecto paralelo para corregir el actual.
- Usa errores reales de las herramientas para encontrar la causa y reparar.

VERIFICACIÓN:
- Valida el proyecto al terminar cuando corresponda.
- Usa validate_python para Python cuando corresponda.
- Si una herramienta devuelve ERROR, corrige y vuelve a validar.
- No inventes APIs, dependencias, archivos, assets ni resultados.
- No afirmes que algo funciona sin comprobación real.

FLUJO:
Explora → planifica → implementa → valida → prueba → repara si hace falta → valida de nuevo → responde.
OpenCode es un motor auxiliar opcional para tareas complejas; después de usarlo, inspecciona y valida sus cambios con las herramientas de Milo."""


def install(app_module):
    """Instala el enrutador rápido sobre el worker de la interfaz existente."""

    def run(self):
        try:
            client = OpenAI(base_url=app_module.BASE_URL, api_key=app_module.API_KEY)
            programming = _looks_like_programming(self.request, self.history)

            if programming:
                agent = Agent(workspace=app_module.WORKSPACE, on_tool_result=self._tool_result)
                messages = []
                for message in self.history:
                    if message.get("role") in {"user", "assistant"}:
                        messages.append({"role": message["role"], "content": message["content"]})
                messages.append({"role": "user", "content": self.request})
                agent.messages = messages

                listing = agent.list_files(".", recursive=True)
                if not listing.get("ok"):
                    raise RuntimeError(listing.get("error", "No se pudo inspeccionar el workspace."))
                files = [item["path"] for item in listing.get("files", []) if item.get("type") == "file"]
                team = detect_specialists(files, self.request)
                instructions = _developer_instructions(self.settings) + "\n\n" + build_team_prompt(team)
                self.progress.emit(f"Workspace: {app_module.WORKSPACE}")
                self.progress.emit(f"Especialistas: {', '.join(agent_.name for agent_ in team)}")

                max_rounds = 8
                for round_number in range(max_rounds):
                    self.progress.emit(f"Ronda {round_number + 1}: trabajando…")
                    response = client.responses.create(
                        model=app_module.MODEL,
                        input=agent.messages,
                        tools=agent.tools,
                        instructions=instructions,
                    )
                    calls, text = agent.process_response(response)
                    if not calls:
                        answer = text or getattr(response, "output_text", "") or "No hubo una respuesta útil del modelo."
                        self.finished.emit(answer, ", ".join(agent_.name for agent_ in team))
                        return
                    agent.add_tool_outputs(calls)

                self.finished.emit(
                    "Detuve el proceso después de 8 rondas para evitar un ciclo infinito. Revisa la actividad para ver qué alcanzó a ejecutar.",
                    ", ".join(agent_.name for agent_ in team),
                )
                return

            messages = []
            for message in self.history:
                if message.get("role") in {"user", "assistant"}:
                    messages.append({"role": message["role"], "content": message["content"]})
            messages.append({"role": "user", "content": self.request})
            self.progress.emit("Conversación general · respuesta directa")
            response = client.responses.create(
                model=app_module.MODEL,
                input=messages,
                tools=[],
                instructions=_general_instructions(self.settings),
            )
            answer = getattr(response, "output_text", "") or "No hubo una respuesta útil del modelo."
            self.finished.emit(answer, "General")
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")

    app_module.AssistantWorker.run = run
