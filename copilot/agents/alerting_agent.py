from langgraph.prebuilt.chat_agent_executor import create_react_agent

from copilot.providers.models import get_chat_model
from copilot.tools.create_alert_tool import create_alert_tool

from copilot.config import ALERTING_MODEL_NAME, ALERTING_TEMPERATURE

def create_alerting_agent():
    """
    Alerting Agent to create alerts referencing IP vantage or flows if needed.
    Gains create_alert_tool + dns_proximity_duckdb_tool for location context.
    """
    model = get_chat_model(
        model_name=ALERTING_MODEL_NAME,
        temperature=ALERTING_TEMPERATURE,
    )
    tools = [create_alert_tool]
    prompt = (
        "You are an alerting_agent, responsible for creating or dispatching alerts. "
        "Use 'create_alert_tool' whenever you need to finalize an HTML alert with a summary text "
        "Always pass the 'org_id' from config as your first argument.\n\n"

        "Guard Rails:\n"
        " - Always pass org_id from config.\n"
        " - If relevant, pass role_id, user_id, conversation_id from config.\n"
        " - Return ONLY the final answer to the user.\n\n"

        "Examples:\n"
        "1) If user says 'Create an alert about suspicious IP 103.16.102.30' then call 'create_alert_tool' with "
        "the org_id, summary text, and optional embedded map link.\n"
        "Proceed. Return the final answer only after the needed steps."
    )

    return create_react_agent(
        name="alerting_agent",
        model=model,
        tools=tools,
        prompt=prompt
    )
