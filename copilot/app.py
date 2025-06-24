import sys
import os

import pandas as pd
import panel as pn
import hvplot.pandas  # noqa
from typing import Any, Dict

from panel.widgets import Button
from panel.chat import ChatInterface, ChatAreaInput

from copilot.agents.root_supervisor import RootLevelSupervisor
from copilot.db.memgraph_connect import MemgraphClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pn.extension("tabulator", sizing_mode="stretch_width")


class ObservabilityApp:
    """
    An application for multi-agent observability, providing a UI for device
    monitoring and interaction with an AI supervisor.
    """

    def __init__(self):
        """Initializes the application, sets up DB connections, and builds the UI."""
        self.conn = MemgraphClient()
        self.top_supervisor = RootLevelSupervisor()
        self.selected_device_id = None
        self.df_devices = self._fetch_devices()

        self.org_id = "org-123"
        self.role_id = "role-xyz"
        self.user_id = "user-999"
        self.conversation_id = "conv-xyz"

        self._init_widgets()
        self._setup_watchers()
        self.template = self._create_layout()

    def _fetch_devices(self):
        """Fetches device data from the database."""
        query = "MATCH (c:Collector)-[:COLLECTS_FROM]->(d:Device) RETURN d{.*, collector_id: c.id} AS properties LIMIT 100"
        records = self.conn.run_cypher(query)
        device_properties = [record['properties'] for record in records]
        return pd.DataFrame(device_properties)


    def _init_widgets(self):
        """Initializes all Panel widgets for the UI."""
        self.devices_table = pn.widgets.Tabulator(
            self.df_devices,
            height=500,
            selectable=True,
            page_size=15,
            show_index=True,
            name="Devices",
            layout="fit_columns",
            hidden_columns=["role_id"],
        )
        self.clear_device_button = Button(
            name="Clear Selection", button_type="warning", width=150
        )
        chat_input = ChatAreaInput(
            placeholder="Ask the AI assistant about devices, anomalies, or insights..."
        )
        self.chat = ChatInterface(
            widgets=[chat_input],
            callback=self._chat_callback,
            height=500,
        )
        self.device_insight_pane = pn.pane.Markdown(
            "Select a row in the devices table to get deeper AI-driven insights.",
            sizing_mode="stretch_both",
        )

    def _setup_watchers(self):
        """Sets up watchers and event handlers for widgets."""
        self.devices_table.param.watch(self._on_device_select, "selection")
        self.clear_device_button.on_click(self._clear_device_click)

    def _call_supervisor(self, user_query: str) -> Dict[str, Any]:
        """
        A centralized method to call the RootLevelSupervisor with the current context.
        """
        return self.top_supervisor.handle_request(
            org_id=self.org_id,
            role_id=self.role_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            device_id=self.selected_device_id,
            user_query=user_query,
        )

    async def _chat_callback(self, message: str, user: str, instance: ChatInterface):
        """
        Callback for the chat interface. Passes the user's message to the supervisor.
        """
        result = self._call_supervisor(user_query=message)
        yield result["content"]

    def _on_device_select(self, event: Any):
        """
        Callback for device selection in the table. Fetches and displays AI insights.
        """
        if not event.new:
            return

        try:
            selected_index = event.new[0]
            device_row = self.df_devices.iloc[selected_index].to_dict()
            self.selected_device_id = device_row.get("dev_id")

            user_query = (
                "A device has been selected from the table. Here is the device data:\n"
                f"{device_row}\n\n"
                "Please perform the following actions:\n"
                "1. Provide a concise summary of the device's key attributes.\n"
                "2. If necessary, query the Observability system for relevant flows, logs, or telemetry.\n"
                "3. Summarize any potential anomalies or noteworthy patterns.\n"
                "Return only your final analysis."
            )

            self.device_insight_pane.object = "Loading AI insights..."
            result = self._call_supervisor(user_query=user_query)
            self.device_insight_pane.object = result["content"]

        except IndexError:
            # This can happen if the selection is cleared.
            pass

    def _clear_device_click(self, event: Any):
        """
        Clears the current device selection and resets the insight pane.
        """
        self.selected_device_id = None
        self.devices_table.selection = []
        self.device_insight_pane.object = (
            "Device selection has been cleared. Select a device to see insights."
        )

    def _create_layout(self):
        """Creates the main application layout using a FastGridTemplate."""
        template = pn.template.FastGridTemplate(
            title="Multi-Agent Observability Dashboard",
            row_height=100,
            header_background="#0072B5",
            prevent_collision=True,
        )

        header_row = pn.Row(
            self.clear_device_button,
            sizing_mode="stretch_width",
            align="center",
        )
        template.header.append(header_row)

        # Use a Card for better visual grouping of the insights
        insight_card = pn.Card(
            self.device_insight_pane,
            title="AI Device Insights",
            sizing_mode="stretch_both",
            scroll=True,
        )

        # Arrange main components on the grid
        template.main[0:5, 0:6] = self.devices_table
        template.main[0:5, 6:12] = self.chat
        template.main[5:8, 0:12] = insight_card  # Use the card here

        return template

    def run(self, port: int = 5006):
        """Shows the application."""
        self.template.servable().show(port=port)


def main():
    """Main function to run the application."""
    app = ObservabilityApp()
    app.run()


if __name__ == "__main__":
    main()