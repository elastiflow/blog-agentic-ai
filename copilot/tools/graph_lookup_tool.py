from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from copilot.db.memgraph_connect import memgraph_conn

#
# Flow Lookup Tool
#

class MemgraphFlowLookupUserParams(BaseModel):
    """
    Only user-facing fields (device_id). org_id is from config.
    """
    device_id: Optional[str] = Field(None, description="Look up flows from this device ID.")

@tool("flow_lookup_tool", parse_docstring=True)
def flow_lookup_tool(
    user_params: MemgraphFlowLookupUserParams,
    config: RunnableConfig
) -> str:
    """
    Adjacency-based flow data from Memgraph. org_id is read from config,
    so the LLM can't override it.

    Args:
        user_params (MemgraphFlowLookupUserParams): includes device_id if any

    Returns:
        str: A human-readable multiline string with flow details (or a message if none are found).
    """
    org_id = config.get("configurable", {}).get("org_id")
    if not org_id:
        return "Missing org_id in config. Cannot proceed."
    device_id = user_params.device_id
    if device_id:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(:Role)-[:CONTROLS_ACCESS]->(:Collector)-[:COLLECTS_FROM]->(d:Device {dev_id:$devId})
        OPTIONAL MATCH (d)-[:SENDS_FLOW]->(f:Flow)
        RETURN 
          f.flow_id as flow_id, 
          f.src_ip as src_ip, 
          f.dst_ip as dst_ip, 
          f.protocol as protocol,
          f.src_port as src_port,
          f.dst_port as dst_port,
          f.bytes as bytes,
          f.packets as packets,
          f.start_time as start_time,
          f.end_time as end_time,
          f.application as application
        ORDER BY flow_id
        """
        params = {"orgId": org_id, "devId": device_id}
        results = memgraph_conn.run_cypher(query, params)
        if not results:
            return f"No flows for device_id={device_id} in org_id={org_id}"
        lines = [f"Flows from device_id={device_id} in org_id={org_id}:"]
        for row in results:
            lines.append(str(row))
        return "\n".join(lines)
    else:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(:Role)-[:CONTROLS_ACCESS]->(:Collector)-[:COLLECTS_FROM]->(d:Device)
        OPTIONAL MATCH (d)-[:SENDS_FLOW]->(f:Flow)
        RETURN 
          d.dev_id as device_id, 
          f.flow_id as flow_id, 
          f.src_ip as src_ip, 
          f.dst_ip as dst_ip, 
          f.protocol as protocol,
          f.src_port as src_port,
          f.dst_port as dst_port,
          f.bytes as bytes,
          f.packets as packets,
          f.start_time as start_time,
          f.end_time as end_time,
          f.application as application
        ORDER BY device_id, flow_id
        """
        params = {"orgId": org_id}
        results = memgraph_conn.run_cypher(query, params)
        if not results:
            return f"No devices or flows found for org_id={org_id}."
        lines = [f"Flows for org_id={org_id}:"]
        for row in results:
            lines.append(str(row))
        return "\n".join(lines)


#
# Log Lookup Tool
#

class MemgraphLogLookupUserParams(BaseModel):
    """Optional device_id for logs."""
    device_id: Optional[str] = Field(None, description="Look up logs from this device ID.")

@tool("log_lookup_tool", parse_docstring=True)
def log_lookup_tool(
    user_params: MemgraphLogLookupUserParams,
    config: RunnableConfig
) -> str:
    """
    Adjacency-based log data from Memgraph. org_id is read from config,
    so the LLM can't override it.

    Args:
        user_params (MemgraphLogLookupUserParams): includes device_id if any

    Returns:
        str: A human-readable multiline string with log details (or a message if none are found).
    """
    org_id = config.get("configurable", {}).get("org_id")
    if not org_id:
        return "Missing org_id in config. Cannot proceed."
    device_id = user_params.device_id
    if device_id:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(:Role)-[:CONTROLS_ACCESS]->(:Collector)-[:COLLECTS_FROM]->(d:Device {dev_id:$devId})
        OPTIONAL MATCH (d)-[:SENDS_LOG]->(lg:Log)
        RETURN 
          lg.trap_id as trap_id,
          lg.trap_type as trap_type,
          lg.severity as severity,
          lg.description as description,
          lg.timestamp as timestamp,
          lg.device_ip as device_ip,
          lg.collector_id as collector_id,
          lg.additional_info as additional_info
        ORDER BY trap_id
        """
        params = {"orgId": org_id, "devId": device_id}
        results = memgraph_conn.run_cypher(query, params)
        if not results:
            return f"No logs for device_id={device_id} in org_id={org_id}"
        lines = [f"Logs from device_id={device_id} in org_id={org_id}:"]
        for row in results:
            lines.append(str(row))
        return "\n".join(lines)
    else:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(:Role)-[:CONTROLS_ACCESS]->(:Collector)-[:COLLECTS_FROM]->(d:Device)
        OPTIONAL MATCH (d)-[:SENDS_LOG]->(lg:Log)
        RETURN 
          d.dev_id as device_id,
          lg.trap_id as trap_id,
          lg.trap_type as trap_type,
          lg.severity as severity,
          lg.description as description,
          lg.timestamp as timestamp,
          lg.device_ip as device_ip,
          lg.collector_id as collector_id,
          lg.additional_info as additional_info
        ORDER BY device_id, trap_id
        """
        params = {"orgId": org_id}
        results = memgraph_conn.run_cypher(query, params)
        if not results:
            return f"No devices or logs found for org_id={org_id}."
        lines = [f"Logs for org_id={org_id}:"]
        for row in results:
            lines.append(str(row))
        return "\n".join(lines)


#
# Telemetry Lookup Tool
#

class MemgraphTelemetryLookupUserParams(BaseModel):
    """Optional device_id for telemetry."""
    device_id: Optional[str] = Field(None, description="Look up telemetry from this device ID.")

@tool("telemetry_lookup_tool", parse_docstring=True)
def telemetry_lookup_tool(
    user_params: MemgraphTelemetryLookupUserParams,
    config: RunnableConfig
) -> str:
    """
    Adjacency-based telemetry data from Memgraph. org_id is read from config,
    so the LLM can't override it.

    Args:
        user_params (MemgraphTelemetryLookupUserParams): includes device_id if any

    Returns:
        str: A human-readable multiline string with telemetry details (or a message if none are found).
    """
    org_id = config.get("configurable", {}).get("org_id")
    if not org_id:
        return "Missing org_id in config. Cannot proceed."
    device_id = user_params.device_id
    if device_id:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(:Role)-[:CONTROLS_ACCESS]->(:Collector)-[:COLLECTS_FROM]->(d:Device {dev_id:$devId})
        OPTIONAL MATCH (d)-[:SENDS_METRIC]->(t:Telemetry)
        RETURN 
          t.telemetry_id as telemetry_id, 
          t.metric as metric, 
          t.value as value, 
          t.unit as unit, 
          t.timestamp as timestamp,
          t.additional_info as additional_info,
          t.device_ip as device_ip,
          t.collector_id as collector_id
        ORDER BY telemetry_id
        """
        params = {"orgId": org_id, "devId": device_id}
        results = memgraph_conn.run_cypher(query, params)
        if not results:
            return f"No telemetry for device_id={device_id} in org_id={org_id}"
        lines = [f"Telemetry from device_id={device_id} in org_id={org_id}:"]
        for row in results:
            lines.append(str(row))
        return "\n".join(lines)
    else:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(:Role)-[:CONTROLS_ACCESS]->(:Collector)-[:COLLECTS_FROM]->(d:Device)
        OPTIONAL MATCH (d)-[:SENDS_METRIC]->(t:Telemetry)
        RETURN 
          d.dev_id as device_id, 
          t.telemetry_id as telemetry_id, 
          t.metric as metric, 
          t.value as value, 
          t.unit as unit,
          t.timestamp as timestamp,
          t.additional_info as additional_info,
          t.device_ip as device_ip,
          t.collector_id as collector_id
        ORDER BY device_id, telemetry_id
        """
        params = {"orgId": org_id}
        results = memgraph_conn.run_cypher(query, params)
        if not results:
            return f"No devices or telemetry found for org_id={org_id}."
        lines = [f"Telemetry for org_id={org_id}:"]
        for row in results:
            lines.append(str(row))
        return "\n".join(lines)
