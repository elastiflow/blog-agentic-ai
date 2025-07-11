import logging
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from copilot.db.memgraph_connect import memgraph_conn
from copilot.providers.embedders import get_embedder
logger = logging.getLogger(__name__)

class BaseVectorSearchParams(BaseModel):
    """Base class for vector search parameters."""
    text: str = Field(..., description="User's semantic query text.")
    top_k: int = Field(3, description="Number of results to return.")
    device_id: Optional[str] = Field(None, description="An optional device_id to filter by.")

class FlowVectorSearchParams(BaseVectorSearchParams):
    """User can specify text query + top_k for flows."""
    text: str = Field(..., description="User's semantic query text for flows.")
    top_k: int = Field(3, description="Number of flow results to return.")
    device_id: Optional[str] = Field(None, description="An optional device_id to filter flows by.")

class LogVectorSearchParams(BaseVectorSearchParams):
    """User can specify text query + top_k for logs."""
    text: str = Field(..., description="User's semantic query text for logs.")
    top_k: int = Field(3, description="Number of log results to return.")
    device_id: Optional[str] = Field(None, description="Optional device_id to filter logs.")

class TelemetryVectorSearchParams(BaseVectorSearchParams):
    """User can specify text query + top_k for telemetry."""
    text: str = Field(..., description="User's semantic query text for telemetry.")
    top_k: int = Field(3, description="Number of telemetry results to return.")
    device_id: Optional[str] = Field(None, description="Optional device_id to filter telemetry.")

def _format_flow_result(node_data: Dict[str, Any], score: float) -> Dict[str, Any]:
    """Formats a flow node and its score into the desired dictionary structure."""
    return {
        "flow_id": node_data.get("flow_id"),
        "src_ip": node_data.get("src_ip"),
        "dst_ip": node_data.get("dst_ip"),
        "protocol": node_data.get("protocol"),
        "src_port": node_data.get("src_port"),
        "dst_port": node_data.get("dst_port"),
        "bytes": node_data.get("bytes"),
        "packets": node_data.get("packets"),
        "start_time": node_data.get("start_time"),
        "end_time": node_data.get("end_time"),
        "application": node_data.get("application"),
        "score": score
    }

def _format_log_result(node_data: Dict[str, Any], score: float) -> Dict[str, Any]:
    """Formats a log node and its score into the desired dictionary structure."""
    return {
        "trap_id": node_data.get("trap_id"),
        "trap_type": node_data.get("trap_type"),
        "severity": node_data.get("severity"),
        "description": node_data.get("description"),
        "timestamp": node_data.get("timestamp"),
        "device_ip": node_data.get("device_ip"),
        "collector_id": node_data.get("collector_id"),
        "additional_info": node_data.get("additional_info"),
        "score": score
    }

def _format_telemetry_result(node_data: Dict[str, Any], score: float) -> Dict[str, Any]:
    """Formats a telemetry node and its score into the desired dictionary structure."""
    return {
        "telemetry_id": node_data.get("telemetry_id"),
        "metric": node_data.get("metric"),
        "value": node_data.get("value"),
        "unit": node_data.get("unit"),
        "timestamp": node_data.get("timestamp"),
        "additional_info": node_data.get("additional_info"),
        "device_ip": node_data.get("device_ip"),
        "collector_id": node_data.get("collector_id"),
        "score": score
    }

## Common Vector Search Logic
def _common_vector_search(
    user_params: BaseVectorSearchParams, # Accepts any subclass like FlowVectorSearchParams
    config: RunnableConfig,
    embedding_index_name: str,
    device_filter_relationship_type: str, # e.g., "SENDS_FLOW"
    result_formatter: Callable[[Dict[str, Any], float], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Internal helper function to perform a generic vector-based search in Memgraph.
    Handles common tasks like config extraction, embedding generation, Cypher query
    construction, execution, and result processing.
    """
    conf = config.get("configurable", {})
    org_id = conf.get("org_id")
    if not org_id:
        logger.warning("No org_id found in config.")
        return [{"error": "No org_id in config"}]
    device_id = conf.get("device_id") or user_params.device_id
    embedder = get_embedder()
    embedding_vec = embedder.embed_query(user_params.text)
    top_k = user_params.top_k
    if hasattr(embedding_vec, "tolist"):
        embedding_vec = embedding_vec.tolist()
    initial_search_candidate_count = min(max(top_k * 20, 100), 1000)
    query_parts = [
        f"CALL vector_search.search('{embedding_index_name}', $initial_k_param, $emb)",
        "YIELD node, similarity",  # 'node' is the entity (Flow, Log, Metric) from the index
    ]
    query_params: Dict[str, Any] = {
        "initial_k_param": initial_search_candidate_count,
        "emb": embedding_vec,
        "orgId": org_id,
        "final_limit_k": top_k,
    }
    query_parts.append("WITH node, similarity")
    where_conditions = ["node.org_id = $orgId"]
    if device_id:
        query_parts.append(
            f"MATCH (device_filter_node:Device {{dev_id: $devId}})-[:{device_filter_relationship_type}]->(node)"
        )
        query_params["devId"] = device_id
    query_parts.append("WHERE " + " AND ".join(where_conditions))
    query_parts.extend([
        "RETURN node, similarity AS score",
        "ORDER BY score DESC",
        "LIMIT $final_limit_k"
    ])
    cypher_query = "\n".join(query_parts)
    try:
        query_results = memgraph_conn.run_cypher(cypher_query, query_params)
        formatted_output = []
        for row in query_results:
            node_data = row.get("node", {})
            score = row.get("score")
            if node_data is not None:
                formatted_result = result_formatter(node_data, score)
                formatted_output.append(formatted_result)
            else:
                logger.warning(
                    f"Node data from query result was None (row possibly had 'node: null'). "
                    f"Type: {type(node_data)}. Row: {row}. Skipping this result."
                )
        return formatted_output
    except Exception as e:
        logger.error(f"Error during Cypher query or result processing for {embedding_index_name}: {e}", exc_info=True)
        return [{"error": str(e)}]

@tool("flow_vector_search_tool", parse_docstring=True)
def flow_vector_search_tool(
        user_params: FlowVectorSearchParams,
        config: RunnableConfig
) -> List[Dict[str, Any]]:
    """
    Vector-based search in Memgraph for flows using a 'flow_embeddings' index.
    org_id is forcibly read from config to guard cross-org data.

    Args:
        user_params (FlowVectorSearchParams): The user-supplied text and top_k.

    Returns:
        List[Dict[str, Any]]: A list of flow nodes with their scores.
          Each entry includes flow_id, IPs, ports, start/end times, etc.
    """
    return _common_vector_search(
        user_params=user_params,
        config=config,
        embedding_index_name="flow_embeddings",
        device_filter_relationship_type="SENDS_FLOW",
        result_formatter=_format_flow_result
    )

@tool("log_vector_search_tool", parse_docstring=True)
def log_vector_search_tool(
        user_params: LogVectorSearchParams,
        config: RunnableConfig
) -> List[Dict[str, Any]]:
    """
    Vector-based search in Memgraph for logs using a 'log_embeddings' index.
    org_id is forcibly read from config to guard cross-org data.

    Args:
        user_params (LogVectorSearchParams): The user-supplied text and top_k.

    Returns:
        List[Dict[str, Any]]: A list of log nodes with their scores.
          Each entry includes trap_id, severity, description, timestamp, etc.
    """
    return _common_vector_search(
        user_params=user_params,
        config=config,
        embedding_index_name="log_embeddings",
        device_filter_relationship_type="SENDS_LOG",
        result_formatter=_format_log_result
    )

@tool("telemetry_vector_search_tool", parse_docstring=True)
def telemetry_vector_search_tool(
        user_params: TelemetryVectorSearchParams,
        config: RunnableConfig
) -> List[Dict[str, Any]]:
    """
    Vector-based search in Memgraph for telemetry using a 'telemetry_embeddings' index.
    org_id is forcibly read from config to guard cross-org data.

    Args:
        user_params (TelemetryVectorSearchParams): The user-supplied text and top_k.

    Returns:
        List[Dict[str, Any]]: A list of telemetry nodes with their scores.
          Each entry includes telemetry_id, metric, value, timestamp, etc.
    """
    return _common_vector_search(
        user_params=user_params,
        config=config,
        embedding_index_name="telemetry_embeddings",
        device_filter_relationship_type="SENDS_METRIC",
        result_formatter=_format_telemetry_result
    )