import csv
import os
from pathlib import Path
from typing import Dict, Any
from neo4j import GraphDatabase

from copilot.config import (
    MEMGRAPH_URI,
    MEMGRAPH_USER,
    MEMGRAPH_PASSWORD,
)
from copilot.providers.embedders import get_embedding_dimension, get_embedder


def create_index_constraints_and_vector_indexes(session, dimension: int):
    """
    Creates uniqueness constraints for Org, Role, User, etc.
    Then creates vector indexes for flows, telemetry, logs in Memgraph.
    """
    def safe_run(tx, query):
        try:
            tx.run(query)
        except Exception as e:
            raise e
    constraints = [
        "CREATE CONSTRAINT ON (o:Org) ASSERT o.id IS UNIQUE",
        "CREATE CONSTRAINT ON (r:Role) ASSERT r.id IS UNIQUE",
        "CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE",
        "CREATE CONSTRAINT ON (c:Collector) ASSERT c.id IS UNIQUE",
        "CREATE CONSTRAINT ON (d:Device) ASSERT d.dev_id IS UNIQUE",
        "CREATE CONSTRAINT ON (f:Flow) ASSERT f.flow_id IS UNIQUE",
        "CREATE CONSTRAINT ON (t:Telemetry) ASSERT t.telemetry_id IS UNIQUE",
        "CREATE CONSTRAINT ON (lg:Log) ASSERT lg.trap_id IS UNIQUE"
    ]
    for c in constraints:
        safe_run(session, c)
    vector_indexes = [
         f"""
        CREATE VECTOR INDEX flow_embeddings
        ON :Flow(embedding)
        WITH CONFIG {{
          "dimension": {dimension},
          "capacity": 1000,
          "metric": "cos"
        }}
        """,
        f"""
        CREATE VECTOR INDEX telemetry_embeddings
        ON :Telemetry(embedding)
        WITH CONFIG {{
          "dimension": {dimension},
          "capacity": 1000,
          "metric": "cos"
        }}
        """,
        f"""
        CREATE VECTOR INDEX log_embeddings
        ON :Log(embedding)
        WITH CONFIG {{
          "dimension": {dimension},
          "capacity": 1000,
          "metric": "cos"
        }}
        """
    ]
    for idx in vector_indexes:
        safe_run(session, idx)
    conversation_constraints = [
        "CREATE CONSTRAINT ON (c:Conversation) ASSERT c.conv_id IS UNIQUE"
    ]
    for cc in conversation_constraints:
        safe_run(session, cc)
    safe_run(session, f"""
    CREATE VECTOR INDEX message_embeddings
    ON :Message(embedding)
    WITH CONFIG {{
      "dimension": {dimension},
      "capacity": 1000,
      "metric": "cos"
    }}
    """)



def row_to_text(row: Dict[str, Any]) -> str:
    """
    Convert a CSV row into a textual representation for embedding.
    """
    text_snippets = []
    if "protocol" in row:
        text_snippets.append(f"protocol={row['protocol']}")
    if "src_ip" in row and "dst_ip" in row:
        text_snippets.append(f"src={row['src_ip']} dst={row['dst_ip']}")
    if "application" in row:
        text_snippets.append(f"app={row['application']}")
    if "src_port" in row:
        text_snippets.append(f"src_port={row['src_port']}")
    if "dst_port" in row:
        text_snippets.append(f"dst_port={row['dst_port']}")
    if "bytes" in row:
        text_snippets.append(f"bytes={row['bytes']}")
    if "packets" in row:
        text_snippets.append(f"packets={row['packets']}")
    if "start_time" in row:
        text_snippets.append(f"start={row['start_time']}")
    if "end_time" in row:
        text_snippets.append(f"end={row['end_time']}")
    return " | ".join(text_snippets)


def load_csv_rows(filepath: str):
    """
    Utility to load CSV rows and return a DictReader instance.
    """
    if not os.path.exists(filepath):
        print(f"*** CSV file not found: {filepath}. Skipping.")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) <= 1:
            print(f"*** CSV file is empty or only header: {filepath}")
            return []
        f.seek(0)
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"Loading {len(rows)} row(s) from {filepath}")
        return rows


def load_orgs(session, filepath):
    """
    Expects orgs.csv with columns: id, name
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        query = """
        MERGE (o:Org {id:$id})
        SET o.name = $name
        """
        params = {"id": row["id"], "name": row["name"]}
        session.run(query, params)


def load_roles(session, filepath):
    """
    Expects roles.csv with columns: org_id, role_id, role_name
    Creates (Org)-[:HAS_ROLE]->(Role)
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        query = """
        MATCH (o:Org {id:$orgId})
        MERGE (r:Role {id:$roleId})
        ON CREATE SET r.name = $roleName
        MERGE (o)-[:HAS_ROLE]->(r)
        """
        params = {
            "orgId": row["org_id"],
            "roleId": row["role_id"],
            "roleName": row["role_name"]
        }
        session.run(query, params)


def load_users(session, filepath):
    """
    Expects users.csv with columns: org_id, role_id, user_id, name
    Creates (Role)-[:ASSIGNED_TO]->(User)
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(r:Role {id:$roleId})
        MERGE (u:User {id:$userId})
        ON CREATE SET u.name = $name
        MERGE (r)-[:ASSIGNED_TO]->(u)
        """
        params = {
            "orgId": row["org_id"],
            "roleId": row["role_id"],
            "userId": row["user_id"],
            "name": row["name"]
        }
        session.run(query, params)


def load_collectors(session, filepath):
    """
    Expects collectors.csv with columns: org_id, role_id, collector_id, name
    Creates (Role)-[:CONTROLS_ACCESS]->(Collector)
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        query = """
        MATCH (o:Org {id:$orgId})-[:HAS_ROLE]->(r:Role {id:$roleId})
        MERGE (c:Collector {id:$collId})
        ON CREATE SET c.name = $collName
        MERGE (r)-[:CONTROLS_ACCESS]->(c)
        """
        params = {
            "orgId": row["org_id"],
            "roleId": row["role_id"],
            "collId": row["collector_id"],
            "collName": row["name"]
        }
        session.run(query, params)


def load_devices(session, filepath):
    """
    Expects devices.csv with columns: org_id, role_id, collector_id, dev_id, ip
    Creates (Collector)-[:COLLECTS_FROM]->(Device)
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        query = """
        MATCH (r:Role {id:$roleId})-[:CONTROLS_ACCESS]->(coll:Collector {id:$collId})
        MERGE (d:Device {dev_id:$devId})
        ON CREATE SET d.ip = $ip
        MERGE (coll)-[:COLLECTS_FROM]->(d)
        """
        params = {
            "roleId": row["role_id"],
            "collId": row["collector_id"],
            "devId": row["dev_id"],
            "ip": row["ip"]
        }
        session.run(query, params)


def load_flows(session, filepath, embedder):
    """
    Loads flows.csv with flow fields.
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        text = row_to_text(row)
        emb = embedder.embed_query(text)
        query_merge = """
        MATCH (d:Device {dev_id:$devId})
        MERGE (f:Flow {flow_id:$flowId})
        ON CREATE SET
          f.src_ip = $src_ip,
          f.dst_ip = $dst_ip,
          f.protocol = $protocol,
          f.src_port = $src_port,
          f.dst_port = $dst_port,
          f.bytes = $bytes,
          f.packets = $packets,
          f.start_time = $start_time,
          f.end_time = $end_time,
          f.application = $application,
          f.org_id = $orgId
        MERGE (d)-[:SENDS_FLOW]->(f)
        """
        params_merge = {
            "devId": row["device_id"],
            "flowId": row["flow_id"],
            "src_ip": row["src_ip"],
            "dst_ip": row["dst_ip"],
            "protocol": row["protocol"],
            "src_port": row["src_port"],
            "dst_port": row["dst_port"],
            "bytes": row["bytes"],
            "packets": row["packets"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "application": row["application"],
            "orgId": row["org_id"]
        }
        session.run(query_merge, params_merge)
        query_embed = """
        MATCH (f:Flow {flow_id:$flowId})
        SET f.embedding = $embedding
        """
        params_embed = {
            "flowId": row["flow_id"],
            "embedding": emb
        }
        session.run(query_embed, params_embed)


def load_telemetry(session, filepath, embedder):
    """
    Loads telemetry.csv with telemetry fields.
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        text = (
            f"metric={row['metric']} value={row['value']}{row.get('unit','')} "
            f"timestamp={row.get('timestamp','')} info={row.get('additional_info','')}"
        )
        emb = embedder.embed_query(text)
        query_merge = """
        MATCH (d:Device {dev_id:$devId})
        MERGE (t:Telemetry {telemetry_id:$telemetryId})
        ON CREATE SET
          t.metric = $metric,
          t.value = $value,
          t.unit = $unit,
          t.timestamp = $timestamp,
          t.additional_info = $additional_info,
          t.device_ip = $device_ip,
          t.collector_id = $collector_id,
          t.org_id = $orgId
        MERGE (d)-[:SENDS_METRIC]->(t)
        """
        params_merge = {
            "devId": row["device_id"],
            "telemetryId": row["telemetry_id"],
            "metric": row["metric"],
            "value": row["value"],
            "unit": row.get("unit", ""),
            "timestamp": row.get("timestamp", ""),
            "additional_info": row.get("additional_info", ""),
            "device_ip": row.get("device_ip", ""),
            "collector_id": row.get("collector_id", ""),
            "orgId": row["org_id"]
        }
        session.run(query_merge, params_merge)
        query_embed = """
        MATCH (t:Telemetry {telemetry_id:$telemetryId})
        SET t.embedding = $embedding
        """
        params_embed = {
            "telemetryId": row["telemetry_id"],
            "embedding": emb
        }
        session.run(query_embed, params_embed)


def load_logs(session, filepath, embedder):
    """
    Loads log.csv with log fields.
    """
    rows = load_csv_rows(filepath)
    if not rows:
        return
    for row in rows:
        text = (
            f"{row['trap_type']} - {row['description']} "
            f"info={row.get('additional_info','')}"
        )
        emb = embedder.embed_query(text)
        query_merge = """
        MATCH (d:Device {dev_id:$devId})
        MERGE (lg:Log {trap_id:$trapId})
        ON CREATE SET
          lg.trap_type = $trapType,
          lg.severity = $severity,
          lg.description = $desc,
          lg.timestamp = $ts,
          lg.device_ip = $deviceIp,
          lg.collector_id = $collectorId,
          lg.additional_info = $additionalInfo,
          lg.org_id = $orgId
        MERGE (d)-[:SENDS_LOG]->(lg)
        """
        params_merge = {
            "devId": row["device_id"],
            "trapId": row["trap_id"],
            "trapType": row["trap_type"],
            "severity": row["severity"],
            "desc": row["description"],
            "ts": row["timestamp"],
            "deviceIp": row.get("device_ip", ""),
            "collectorId": row.get("collector_id", ""),
            "additionalInfo": row.get("additional_info", ""),
            "orgId": row["org_id"]
        }
        session.run(query_merge, params_merge)
        query_embed = """
        MATCH (lg:Log {trap_id:$trapId})
        SET lg.embedding = $embedding
        """
        params_embed = {
            "trapId": row["trap_id"],
            "embedding": emb
        }
        session.run(query_embed, params_embed)


def main():
    dimension = get_embedding_dimension()
    driver = GraphDatabase.driver(MEMGRAPH_URI, auth=(MEMGRAPH_USER, MEMGRAPH_PASSWORD))
    embedder = get_embedder()
    base_path = Path(__file__).resolve().parent
    data_dir = (base_path / "../data/demo").resolve()
    if not os.path.exists(data_dir):
        print(f"Data dir {data_dir} not found, adjust path!")
        return
    orgs_csv = os.path.join(data_dir, "orgs.csv")
    roles_csv = os.path.join(data_dir, "roles.csv")
    users_csv = os.path.join(data_dir, "users.csv")
    collectors_csv = os.path.join(data_dir, "collectors.csv")
    devices_csv = os.path.join(data_dir, "devices.csv")
    flows_csv = os.path.join(data_dir, "flows.csv")
    telemetry_csv = os.path.join(data_dir, "telemetry.csv")
    logs_csv = os.path.join(data_dir, "logs.csv")
    with driver.session() as session:
        print("Creating constraints and vector indexes...")
        create_index_constraints_and_vector_indexes(session, dimension)
        print("Loading orgs...")
        load_orgs(session, orgs_csv)
        print("Loading roles...")
        load_roles(session, roles_csv)
        print("Loading users...")
        load_users(session, users_csv)
        print("Loading collectors...")
        load_collectors(session, collectors_csv)
        print("Loading devices...")
        load_devices(session, devices_csv)
        print("Loading flows...")
        load_flows(session, flows_csv, embedder)
        print("Loading telemetry...")
        load_telemetry(session, telemetry_csv, embedder)
        print("Loading logs...")
        load_logs(session, logs_csv, embedder)
    driver.close()
    print("Memgraph ingestion complete. Vector indexes created, embeddings set on flows/telemetry/logs")


if __name__ == "__main__":
    main()
