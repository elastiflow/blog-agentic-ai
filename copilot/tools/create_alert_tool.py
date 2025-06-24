import os
import uuid
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig


class CreateAlertUserParams(BaseModel):
    """User-facing schema for creating an alert (excluding org_id)."""
    summary: str = Field(..., description="Alert summary text to be put in the HTML file.")

@tool("create_alert_tool", parse_docstring=True)
def create_alert_tool(
        user_params: CreateAlertUserParams,
        config: RunnableConfig,
) -> str:
    """
    Generate an alert with the provided summary text,
    storing it in data/alerts. Returns the file path of the created alert.

    Args:
        user_params: includes alert summary and visualization_html from the user
    """
    org_id = config.get("configurable", {}).get("org_id")
    if not org_id:
        return "Error: missing org_id in config. Cannot create alert."
    summary = user_params.summary
    alert_id = str(uuid.uuid4())
    alerts_dir = os.path.join("data", "alerts")
    os.makedirs(alerts_dir, exist_ok=True)
    filename = f"alert_{org_id}_{alert_id}.html"
    filepath = os.path.join(alerts_dir, filename)
    html_content = f"""
    <html>
      <head><title>Alert for org {org_id}</title></head>
      <body>
        <h2>Alert Summary</h2>
        <p>{summary}</p>
        <hr>
      </body>
    </html>
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    return f"Alert created at {filepath}"
