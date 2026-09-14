import os

from dotenv import load_dotenv
from openai import OpenAI
from neural_agent import NeuralAgent
from subagents import build_team_prompt, detect_specialists

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL") or "qwen3:8b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
agent = NeuralAgent()

BASE_INSTRUCTIONS = """
Trabaja como un orquestador de subagentes de programación preciso y eficiente.
Usa herramientas para crear y modificar archivos; no inventes archivos, APIs ni resultados.
Antes de modificar código existente, inspecciónalo.
Para proyectos nuevos, crea primero una estructura pequeña y coherente.
Asigna cada parte al especialista apropiado y usa al tester al final.
No hagas que todos los subagentes repitan el mismo trabajo: cada uno tiene una responsabilidad.
Después de escribir Python, valida su sintaxis y, si es seguro, ejecútalo.
Para redes neuronales, prepara datos, entrena, valida y prueba; no inventes métricas.
No afirmes que algo funciona si no lo comprobaste.
Al terminar, responde brevemente con los cambios y las pruebas realizadas.
""".strip()


def ask_agent(request):
    # Selecciona un equipo pequeño para no aumentar innecesariamente la latencia.
    current_files = []
    try:
        listing = agent.list_files(".", recursive=True)
        current_files = [x["path"] for x in listing.get("files", []) if x.get("type") == "file"]
    except Exception:
        pass

    team = detect_specialists(current_files, request)
    agent.messages.append({
        "role": "system",
        "content": build_team_prompt(team),
    })

    for _ in range(12):
        response = client.responses.create(
            model=MODEL,
            input=agent.messages,
            tools=agent.tools,
            instructions=BASE_INSTRUCTIONS,
        )
        tool_calls, text = agent.process_response(response)
        if not tool_calls:
            print(f"Asistente: {text or getattr(response, 'output_text', '') or 'Listo.'}")
            return
        agent.add_tool_outputs(tool_calls)

    print("Asistente: detuve el proceso tras 12 rondas para evitar un ciclo largo.")


print("Asistente Juan - orquestador de subagentes + laboratorio de IA")
print(f"Modelo: {MODEL}")
print(f"Workspace: {agent.workspace}")
print("Especialistas: planner, Python, JS, TS, HTML, CSS, Java, C/C++, C#, PHP, SQL, Rust, Go, ML y tester.")
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
