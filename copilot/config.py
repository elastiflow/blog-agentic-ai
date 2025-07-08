import os
from dotenv import load_dotenv

load_dotenv()

MEMGRAPH_URI = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "memgraphUser")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "MemgraphPassword1233")

PROVIDER = os.getenv("MODEL_PROVIDER", "openai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key")

DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-4o")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.0"))

OBSERVABILITY_MODEL_NAME = os.getenv("OBSERVABILITY_MODEL_NAME", "gpt-4o")
OBSERVABILITY_TEMPERATURE = float(os.getenv("OBSERVABILITY_TEMPERATURE", "0.0"))

ALERTING_MODEL_NAME = os.getenv("ALERTING_MODEL_NAME", "gpt-4o")
ALERTING_TEMPERATURE = float(os.getenv("ALERTING_TEMPERATURE", "0.0"))