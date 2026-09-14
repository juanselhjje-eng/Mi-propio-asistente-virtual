import os

from dotenv import load_dotenv
from openai import OpenAI
from subagents import build_team_prompt, detect_specialists
from agent import Agent

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL") or "qwen3:8b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
MAX_ROUNDS = max(4, min(int(os.getenv("ASSISTANT_MAX_ROUNDS", "8")), 12))
MAX_HISTORY = max(8, min(int(os.getenv("ASSISTANT_MAX_HISTORY", "18")), 40))

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
agent = Agent()

BASE_INSTRUCTIONS = """
Eres el orquestador de un asistente local de programacion.
Tu objetivo es construir proyectos reales dentro del workspace, no solamente explicar codigo.

COMPORTAMIENTO:
- Para 'creame un juego/app/pagina de X', crea los archivos necesarios y dejalos conectados.
- Si el usuario especifica un lenguaje, respeta ese lenguaje. Soporta Python, pygame, HTML, CSS, JavaScript, TypeScript, C, C++, C#, Java, Rust, Go, PHP y SQL.
- Empieza con la estructura minima que pueda funcionar. No llenes el proyecto de archivos innecesarios.
- Para juegos y apps, crea una carpeta de proyecto clara. Si necesita sprites, imagenes, sonidos o iconos que no existen, crea carpetas assets y dile exactamente donde ponerlos.
- Si es posible, usa placeholders generados por codigo para que el proyecto pueda probarse sin assets externos.
- Antes de modificar un proyecto existente, inspecciona los archivos relevantes.
- Despues de crear/modificar, valida y repara errores. En proyectos de varios archivos usa validate_project.
- Para Python usa validate_python y, si es seguro y no es interactivo, run_python.
- No ejecutes programas que esperen entrada indefinidamente.
- No inventes APIs, librerias, archivos, capturas, resultados ni pruebas.
- Al terminar indica claramente que archivos se crearon/modificaron, que pruebas pasaron, que errores se corrigieron y que recursos faltan.

SUBAGENTES:
El equipo activo se incluye en estas instrucciones. Son roles del mismo modelo local, no 20 modelos distintos. El planner organiza; cada especialista se concentra en su tecnologia; el tester revisa el resultado.
""".strip()


def compact_history():
    if len(agent.messages) <= MAX_HISTORY + 1:
        return
    # Conserva el system prompt y las interacciones mas recientes.
    agent.messages[:] = [agent.messages[0]] + agent.messages[-MAX_HISTORY:]


def ask_agent(request):
    try:
        listing = agent.list_files(".", recursive=True)
        current_files = [item["path"] for item in listing.get("files", []) if item.get("type") == "file"]
    except Exception:
        current_files = []

    team = detect_specialists(current_files, request)
    instructions = BASE_INSTRUCTIONS + "\n\n" + build_team_prompt(team)

    for _ in range(MAX_ROUNDS):
        response = client.responses.create(
            model=MODEL,
            input=agent.messages,
            tools=agent.tools,
            instructions=instructions,
        )
        tool_calls, text = agent.process_response(response)
        if not tool_calls:
            print(f"Asistente: {text or getattr(response, 'output_text', '') or 'Listo.'}")
            return
        agent.add_tool_outputs(tool_calls)

    print(f"Asistente: detuve el proceso tras {MAX_ROUNDS} rondas para evitar ciclos largos.")


print("Asistente Juan - constructor de proyectos local")
print(f"Modelo: {MODEL}")
print(f"Workspace: {agent.workspace}")
print("Subagentes: planner + especialistas por lenguaje + tester.")
print("Escribe 'salir' para cerrar.\n")

while True:
    try:
        user_input = input("Tu: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCerrando asistente")
        break

    if not user_input:
        continue
    if user_input.lower() in {"salir", "exit", "quit"}:
        print("Cerrando asistente")
        break

    agent.messages.append({"role": "user", "content": user_input})
    try:
        ask_agent(user_input)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}")
        print("Comprueba que Ollama esté ejecutándose y que el modelo configurado exista.")
    finally:
        compact_history()
