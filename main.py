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

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
agent = Agent()

BASE_INSTRUCTIONS = """
Eres el orquestador de un asistente local de programacion.
Tu objetivo es construir proyectos reales dentro del workspace, no solamente explicar codigo.

COMPORTAMIENTO:
- Para una peticion como 'creame un juego/app/pagina de X', crea los archivos necesarios y dejalos conectados.
- Si el usuario especifica un lenguaje, respeta ese lenguaje. Si dice Python + pygame, usa pygame; si dice HTML/CSS/JS, crea una web funcional; si pide C, C++, C#, Java, Rust, Go, PHP o SQL, usa la estructura adecuada.
- No crees 20 archivos porque si. Empieza con la estructura minima que pueda funcionar y amplia solo si hace falta.
- Si el proyecto necesita sprites, imagenes, sonidos, iconos u otros recursos que no existen, crea las carpetas assets/sprites, assets/audio, etc. y dile exactamente donde ponerlos. No inventes que esos archivos existen.
- Si un recurso puede reemplazarse temporalmente por una forma generada por codigo, hazlo para que el proyecto pueda probarse sin esperar al usuario.
- Antes de modificar un proyecto existente, inspecciona sus archivos relevantes.
- Despues de crear/modificar archivos, valida lo que puedas. Repara errores encontrados antes de terminar.
- Para Python usa validate_python y, cuando sea seguro, run_python. No ejecutes programas interactivos que puedan quedarse esperando entrada.
- Para webs comprueba referencias locales entre HTML, CSS, JS y assets.
- Usa al tester para revisar el proyecto completo, pero no repitas la misma inspeccion innecesariamente.
- No afirmes que algo funciona si no fue comprobado. Si una herramienta no puede comprobarlo, indicalo.
- Nunca inventes APIs, librerias, archivos, resultados, capturas ni pruebas.
- Responde al final con: archivos creados/modificados, pruebas realizadas, errores corregidos y recursos que el usuario debe aportar, si los hay.

SUBAGENTES:
El equipo activo se incluye en las instrucciones de cada peticion. Son roles de razonamiento del mismo modelo local, no modelos separados. El planner decide la estructura; los especialistas revisan su tecnologia; el tester hace la comprobacion final.
""".strip()


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
