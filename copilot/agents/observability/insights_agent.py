from langgraph.prebuilt.chat_agent_executor import create_react_agent

from copilot.config import OBSERVABILITY_MODEL_NAME, OBSERVABILITY_TEMPERATURE
from copilot.providers.models import get_chat_model
from copilot.tools.graph_lookup_tool import (
    flow_lookup_tool,
    log_lookup_tool,
    telemetry_lookup_tool
)

def create_insights_agent():
    """
    An InsightsAgent that uses create_react_agent from langgraph.
    This agent provides numeric or data-driven insights using adjacency-based queries
    for flows, logs, or telemetry in Neo4j.
    """
    model = get_chat_model(
        model_name=OBSERVABILITY_MODEL_NAME,
        temperature=OBSERVABILITY_TEMPERATURE,
    )
    tools = [
        flow_lookup_tool,
        log_lookup_tool,
        telemetry_lookup_tool
    ]
    prompt = (
        "You are an `insights_agent` tasked with providing numeric or data-driven insights.\n\n"
        "You have access to the following adjacency-based tools in Memgraph:\n"
        "1) flow_lookup_tool => queries flows from a device or entire org.\n"
        "2) log_lookup_tool => queries logs from a device or entire org.\n"
        "3) telemetry_lookup_tool => queries telemetry from a device or entire org.\n\n"

        "Guidelines:\n"
        "- Always pass `org_id` from config. If a `device_id` is available, you can also pass that.\n"
        "- Use `flow_lookup_tool` if user wants adjacency-based flow relationships.\n"
        "- Use `log_lookup_tool` if user wants adjacency-based logs.\n"
        "- Use `telemetry_lookup_tool` if user wants adjacency-based telemetry.\n"
        "- Summarize or highlight interesting numeric or data-driven insights once you have the data.\n"
        "- Return ONLY your final answer (no chain-of-thought). Respect org_id.\n\n"

        "Example usage:\n"
        "- If user requests 'Show me logs for device dev-7?': use `log_lookup_tool`.\n"
        "- If user requests 'Which flows are connected to dev-3?': use `flow_lookup_tool`.\n"
        "- If user requests 'Telemetry for dev-5?': use `telemetry_lookup_tool`.\n"
        "- Provide any numeric stats or summaries about the data.\n"
        "Proceed accordingly and do not reveal chain-of-thought."
    )

    # Create a ReAct-style agent
    agent = create_react_agent(
        name="insights_agent",
        model=model,
        tools=tools,
        prompt=prompt
    )
    return agent
