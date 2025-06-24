import asyncio
from typing import Dict, Any, Optional

from copilot.agents.observability.supervisor_agent import build_observability_supervisor
from copilot.agents.alerting_agent import create_alerting_agent

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from copilot.config import DEFAULT_MODEL_NAME, DEFAULT_TEMPERATURE
from copilot.db.memgraph_connect import memgraph_conn
from copilot.providers.models import get_chat_model
from copilot.supervisor.supervisor import create_supervisor


class RootLevelSupervisor:
    """
    A root-level multi-agent supervisor system using langgraph_supervisor,
    managing Observability Team and Alerting Agent.
    """

    def __init__(self):
        self.observability_supervisor  = build_observability_supervisor()
        self.alerting_agent = create_alerting_agent()
        model = get_chat_model(
            model_name=DEFAULT_MODEL_NAME,
            temperature=DEFAULT_TEMPERATURE,
        )
        prompt = (
            "You are the `root_level_supervisor` orchestrating three specialized teams:\n\n"
            "1) observability_team => data queries (flows/logs/telemetry), analysis, or summarizing.\n"
            "2) alerting_agent => create or dispatch HTML alerts.\n\n"

            "Routing Guidelines:\n"
            " - If user wants data retrieval (duckdb logs/flows) or semantic search or numeric insights, use observability_team.\n"
            " - If user wants an alert, use alerting_agent.\n\n"

            "Always read `org_id` (and possibly `device_id`) from config for guard rails. "
            "Return ONLY the final answer. Do not disclose chain-of-thought.\n\n"

            "Example usage:\n"
            " - \"List flows above 500 bytes for dev-7\": Observability (data retrieval or adjacency-based insight).\n"
            " - \"Create an alert about suspicious IP 103.16.102.30\": Alerting (alerting_agent).\n\n"

            "Proceed by deciding the best suited team or agent and producing a final response only."
        )
        checkpointer = InMemorySaver()
        store = InMemoryStore()
        self.root_supervisor = create_supervisor(
            agents=[
                self.observability_supervisor,
                self.alerting_agent,
            ],
            model=model,
            prompt=prompt,
            supervisor_name="root_level_supervisor",
            output_mode="last_message",
        ).compile(name="root_level_supervisor", checkpointer=checkpointer, store=store)

    def handle_request(
        self,
        org_id: str,
        role_id: str,
        user_id: str,
        conversation_id: str,
        device_id: Optional[str],
        user_query: str
    ) -> Dict[str, Any]:
        """
        Single method to handle the user's request, injecting guard rails
        into a 'system' or 'context' message. Then pass to the top-level
        supervisor for multi-agent orchestration.
        """
        system_guard = (
            f"Guard Rails:\n"
            f"org_id={org_id}\n"
            f"role_id={role_id}\n"
            f"user_id={user_id}\n"
            f"conversation_id={conversation_id}\n"
        )
        config = {
            "configurable": {
                "org_id": org_id,
                "role_id": role_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "thread_id": conversation_id
            }
        }
        if device_id is not None:
            config["configurable"]["device_id"] = device_id
        messages = [
            {"role": "system", "content": system_guard},
            {"role": "user", "content": user_query}
        ]
        state = {"messages": messages}
        result = self.root_supervisor.invoke(state, config=config)
        final_message = result["messages"][-1].content if result["messages"] else "(No response)"
        def do_longterm_store():
            memgraph_conn.store_conversation_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="user",
                content=user_query
            )
            memgraph_conn.store_conversation_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                content=final_message
            )
        asyncio.create_task(asyncio.to_thread(do_longterm_store))
        return {
            "type": "root_supervisor_result",
            "content": final_message
        }