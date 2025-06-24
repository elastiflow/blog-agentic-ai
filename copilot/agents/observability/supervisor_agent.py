from copilot.providers.models import get_chat_model
from copilot.supervisor.supervisor import create_supervisor

from copilot.agents.observability.insights_agent import create_insights_agent
from copilot.agents.observability.research_agent import create_research_agent
from copilot.config import OBSERVABILITY_MODEL_NAME, OBSERVABILITY_TEMPERATURE


def build_observability_supervisor():
    research = create_research_agent()
    insights = create_insights_agent()
    model = get_chat_model(
        model_name=OBSERVABILITY_MODEL_NAME,
        temperature=OBSERVABILITY_TEMPERATURE,
    )
    supervisor_prompt = (
        "You are an `observability_supervisor` responsible for routing queries to:\n"
        "1) insights_agent => summarization, numeric data analysis, adjacency-based insights (via GraphDB lookup).\n"
        "2) research_agent => unstructured or semantic vector-based searching (flow/log/telemetry embeddings in GraphDB RAG).\n\n"

        "Guidelines:\n"
        " - If the user wants numeric summarization or adjacency-based flow insights, use insights_agent.\n"
        " - If the user wants semantic/unstructured searching (e.g. 'search logs about suspicious activity'), use research_agent.\n"
        " - Always pass `org_id` from config. If relevant, also pass `device_id` or other guard rails.\n"
        " - Return ONLY your final answer. Do not show chain-of-thought.\n\n"

        "Example usage:\n"
        " - 'Give me a summary of flows between dev-3 and dev-5' => insights_agent (adjacency-based summarization).\n"
        " - 'List logs about critical traps for org-123' => insights_agent.\n"
        " - 'Search for logs mentioning DDoS or malicious patterns' => research_agent (semantic vector search).\n\n"

        "Respect all guard rails (org_id, device_id if present) in calls to sub-agents. Output final answer only."
    )
    workflow = create_supervisor(
        agents=[research, insights],
        model=model,
        prompt=supervisor_prompt,
        supervisor_name="observability_supervisor",
        output_mode="last_message",
        include_agent_name="inline",
    )
    return workflow.compile(name="observability_team")