from copilot.config import (PROVIDER, OPENAI_API_KEY)
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings

def get_embedder():
    if PROVIDER == "openai":
        return OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    elif PROVIDER == "local":
        return OllamaEmbeddings(model="nomic-embed-text")
    else:
        raise ValueError(f"Unknown PROVIDER: {PROVIDER}")

def get_embedding_dimension() -> int:
    if PROVIDER == "local":
        return 768
    elif PROVIDER == "openai":
        return 1536
    else:
        raise ValueError(f"Unsupported embedding type: {PROVIDER}")