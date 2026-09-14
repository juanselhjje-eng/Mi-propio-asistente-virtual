import os

from dotenv import load_dotenv
from openai import OpenAI
from neural_agent import NeuralAgent

load_dotenv()

# 8B prioriza velocidad. Cambia OLLAMA_MODEL en .env si tienes un modelo mejor.
MODEL = os.getenv("OLLAMA_MODEL") or "qwen3:8b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
agent = NeuralAgent()

INSTRUCTIONS = """
Trabaja como un agente de programación preciso y eficiente.
Usa herramientas para crear y modificar archivos; no inventes archivos, APIs ni resultados.
Antes de modificar código existente, inspecciónalo.
Para proyectos nuevos, crea primero una estructura pequeña y coherente.
Después de escribir Python, valida su sintaxis y, si es seguro, ejecútalo para detectar errores.
Para redes neuronales, prepara datos, entrena, valida y prueba; no inventes métricas.
No repitas herramientas innecesariamente y no hagas más operaciones de las necesarias.
No afirmes que algo funciona si no lo comprobaste.
Al terminar, responde brevemente con los cambios y las pruebas realizadas.
""".strip()


def ask_agent():
    # 12 rondas evitan que un error provoque un ciclo demasiado largo.
    for _ in range(12):
        response = client.responses.create(
            model=MODEL,
            input=agent.messages,
            tools=agent.tools,
            instructions=INSTRUCTIONS,
        )
        tool_calls, text = agent.process_response(response)
        if not tool_calls:
            print(f"Asistente: {text or getattr(response, 'output_text', '') or 'Listo.'}")
            return
        agent.add_tool_outputs(tool_calls)

    print("Asistente: detuve el proceso tras 12 rondas para evitar un ciclo largo.")


print("Asistente Juan - constructor y laboratorio de IA")
print(f"Modelo: {MODEL}")
print(f"Workspace: {agent.workspace}")
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
        ask_agent()
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}")
        print("Comprueba que Ollama esté ejecutándose y que el modelo configurado exista.")
