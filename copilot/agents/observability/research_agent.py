from langgraph.prebuilt.chat_agent_executor import create_react_agent
from copilot.config import OBSERVABILITY_MODEL_NAME, OBSERVABILITY_TEMPERATURE
from copilot.providers.models import get_chat_model
from copilot.tools.graph_rag_tools import (
    flow_vector_search_tool,
    log_vector_search_tool,
    telemetry_vector_search_tool
)

def create_research_agent():
    """
    A Research Agent focusing on unstructured retrieval or web searching,
    but also with capabilities for:
     - IP location lookups via dns_proximity_duckdb_tool,
     - semantic flow queries with flow_vector_search_tool,
     - semantic log queries with log_vector_search_tool,
     - semantic telemetry queries with telemetry_vector_search_tool.
    """
    model = get_chat_model(
        model_name=OBSERVABILITY_MODEL_NAME,
        temperature=OBSERVABILITY_TEMPERATURE,
    )
    tools = [
        flow_vector_search_tool,
        log_vector_search_tool,
        telemetry_vector_search_tool
    ]
    prompt = (
        "You are a `research_agent` specializing in unstructured or semantic queries over vector embeddings. \n\n"
        "Tools at your disposal:\n"
        "1) flow_vector_search_tool => semantic search over flows in Memgraph.\n"
        "2) log_vector_search_tool => semantic search over logs in Memgraph.\n"
        "3) telemetry_vector_search_tool => semantic search over telemetry in Memgraph.\n\n"

        "Guidelines:\n"
        " - Always pass `org_id` from config for guard rails (and `device_id` if relevant).\n"
        " - If user wants to find flows by textual or conceptual content (e.g. 'suspicious activity'), use flow_vector_search_tool.\n"
        " - If user wants logs by textual or conceptual content (e.g. 'critical trap' or 'error'), use log_vector_search_tool.\n"
        " - If user wants telemetry metrics by textual or conceptual content (e.g. 'CPU usage over 90%'), use telemetry_vector_search_tool.\n"
        " - Return ONLY the final answer. Do NOT show chain-of-thought.\n\n"

        "Example usage:\n"
        "1) 'Search suspicious flows about DDoS' => flow_vector_search_tool.\n"
        "2) 'Find logs mentioning critical or urgent traps' => log_vector_search_tool.\n"
        "3) 'Any telemetry referencing disk usage or memory over 95%?' => telemetry_vector_search_tool.\n"
        "If the user references a device, pass `device_id` in the config or user_params.\n"
        "Ensure you do not override org_id or device_id, which come from the config.\n"
        "Proceed accordingly.\n"
    )


    return create_react_agent(
        name="research_agent",
        model=model,
        tools=tools,
        prompt=prompt
    )
