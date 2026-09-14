import os
from dotenv import load_dotenv
from openai import OpenAI
from agent import Agent


load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL") or "qwen3:8b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"

client = OpenAI(base_url=BASE_URL, api_key=os.getenv("OLLAMA_API_KEY", "ollama"))
agent = Agent()

print("Asistente Juan - modo creador de proyectos")
print(f"Modelo: {MODEL}")
print(f"Workspace: {agent.workspace}")
print("Escribe 'salir' para cerrar.\n")


def ask_agent():
    """Ejecuta el ciclo Responses API -> herramientas -> Responses API."""
    while True:
        response = client.responses.create(
            model=MODEL,
            input=agent.messages,
            tools=agent.tools,
            instructions=(
                "Trabaja directamente sobre el workspace mediante tus herramientas. "
                "Si te piden crear un juego o programa, crea los archivos necesarios y no solo el codigo en la respuesta. "
                "Si modificas codigo existente, lee primero el archivo relevante. "
                "Cuando termines las operaciones, responde con un resumen corto."
            ),
        )

        tool_calls, text = agent.process_response(response)

        if tool_calls:
            agent.add_tool_outputs(tool_calls)
            continue

        if text:
            print(f"Asistente: {text}")
        else:
            output_text = getattr(response, "output_text", "")
            if output_text:
                print(f"Asistente: {output_text}")
        break


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
        print(f"Error del asistente: {type(exc).__name__}: {exc}")
        print("Revisa que Ollama este ejecutandose y que OLLAMA_MODEL exista.")
