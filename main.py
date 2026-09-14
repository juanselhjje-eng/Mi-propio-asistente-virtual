import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from agent import Agent


print("Asistente juan 1")

load_dotenv()

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)
agent = Agent()

ollama_model = os.getenv("OLLAMA_MODEL")


while True:

    user_input = input("Tu: ").strip()

    # Validaciones
    if not user_input:
        print("Por favor, ingresa un mensaje.")
        continue

    if user_input.lower() in ["salir", "exit", "quit"]:
        print("Cerrando asistente")
        break

    # Historial
    agent.messages.append({"role": "user", "content": user_input})

    while True:
        response = client.responses.create(
            model=ollama_model,
            input=agent.messages,
            tools=agent.tools
        )

        called_tool = agent.process_response(response)

        if not called_tool:
            break