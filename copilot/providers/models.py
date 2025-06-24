from copilot.config import (PROVIDER, OPENAI_API_KEY)

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama


def get_chat_model(model_name: str = None, temperature: float = 0.0):
    if PROVIDER == "openai":
        chosen_model = model_name or "gpt-4o"
        return ChatOpenAI(
            model=chosen_model,
            temperature=temperature,
            api_key=OPENAI_API_KEY
        )
    elif PROVIDER == "local":
        return ChatOllama(model="llama3.1:8b-instruct-fp16", temperature=temperature)
    else:
        raise ValueError(f"Unknown PROVIDER: {PROVIDER}")
