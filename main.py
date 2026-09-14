import os
from dotenv import load_dotenv
from openai import OpenAI
from agent import Agent

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL") or "qwen3-coder:30b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
agent = Agent()

print("Asistente Juan - constructor de proyectos")
print(f"Modelo: {MODEL}")
print(f"Workspace: {agent.workspace}")
print("Escribe 'salir' para cerrar.\n")


def ask_agent():
    """Mantiene el bucle Responses API -> herramientas -> validacion."""
    rounds = 0
    max_rounds = 30

    while rounds < max_rounds:
        rounds += 1
        response = client.responses.create(
            model=MODEL,
            input=agent.messages,
            tools=agent.tools,
            instructions=(
                "Construye y corrige el proyecto directamente en el workspace. "
                "No pegues grandes bloques de codigo en la respuesta si puedes escribirlos con herramientas. "
                "Para codigo nuevo, crea primero una estructura coherente y luego implementa. "
                "Para Python, usa validate_python despues de escribir o modificar. "
                "Si una validacion o ejecucion falla, corrige el problema y vuelve a comprobar. "
                "No afirmes que funciona sin una comprobacion razonable. "
                "Cuando termines, responde solo con un resumen corto de archivos y pruebas."
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
        return

    print("Asistente: detuve el ciclo porque alcanzo el limite de operaciones. Revisa el proyecto antes de continuar.")


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
        print("Comprueba que Ollama este ejecutandose, que el modelo exista y que el endpoint /v1 responda.")
