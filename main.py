import os
from dotenv import load_dotenv
from openai import OpenAI
from neural_agent import NeuralAgent

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL") or "qwen3-coder:30b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
agent = NeuralAgent()

print("Asistente Juan - constructor de proyectos + laboratorio neuronal")
print(f"Modelo: {MODEL}")
print(f"Workspace: {agent.workspace}")
print("Puede crear proyectos, entrenar redes neuronales y probar resultados.")
print("Escribe 'salir' para cerrar.\n")


def ask_agent():
    rounds = 0
    max_rounds = 40

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
                "Para Python, valida y ejecuta pruebas razonables. "
                "Para redes neuronales, prepara datos, entrena con train_neural_network, inspecciona la perdida y prueba predicciones. "
                "Si una validacion, ejecucion o entrenamiento falla, usa el error como evidencia, corrige y vuelve a comprobar. "
                "No afirmes que algo funciona sin una comprobacion razonable. "
                "Cuando termines, responde solo con un resumen corto de archivos, pruebas y resultados de entrenamiento."
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
