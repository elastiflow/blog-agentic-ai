from typing import LiteralString, List, Dict, Any
from neo4j import GraphDatabase
from datetime import datetime

from copilot.config import MEMGRAPH_URI, MEMGRAPH_USER, MEMGRAPH_PASSWORD

class MemgraphClient:
    """
    A helper class for connecting and running queries in MemGraph.
    """

    def __init__(self, uri=MEMGRAPH_URI, user=MEMGRAPH_USER, password=MEMGRAPH_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_cypher(self, query: LiteralString, params: dict = None, db: str = None):
        if params is None:
            params = {}
        with self.driver.session(database=db) as session:
            result = session.run(query, **params)
            data = []
            for record in result:
                data.append(dict(record))
            return data

    def store_conversation_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: str = None,
        embedding: List[float] = None,
    ):
        """
        Stores a single message in Memgraph:
          (u:User {id:user_id})-[:HAS_CONVERSATION]->(conv:Conversation {conv_id:conversation_id})
          -[:HAS_MESSAGE]->(m:Message {role, text, timestamp, embedding?})
        Creates nodes and relationships if not existing.
        """
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()

        query = """
        MERGE (u:User {id:$userId})
        MERGE (conv:Conversation {conv_id:$convId})
        MERGE (u)-[:HAS_CONVERSATION]->(conv)
        CREATE (m:Message {role:$role, text:$text, timestamp:$ts})
        MERGE (conv)-[:HAS_MESSAGE]->(m)
        """
        if embedding is not None:
            query += """
            SET m.embedding = $embedding
            """

        params = {
            "userId": user_id,
            "convId": conversation_id,
            "role": role,
            "text": content,
            "ts": timestamp,
            "embedding": embedding,
        }
        return self.run_cypher(query, params)


    def get_users_conversations(self, user_id: str) -> List[str]:
        """
        Retrieves all conversationIds for a given userId.
        """
        query = """
        MATCH (u:User {id:$userId})-[:HAS_CONVERSATION]->(c:Conversation)
        RETURN c.conv_id AS conversationId
        ORDER BY conversationId
        """
        results = self.run_cypher(query, {"userId": user_id})
        return [row["conversationId"] for row in results]


    def get_conversation(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Returns all the messages in a conversation in raw text format.
        """
        query = """
        MATCH (u:User {id:$userId})-[:HAS_CONVERSATION]->(c:Conversation {conv_id:$convId})
              -[:HAS_MESSAGE]->(m:Message)
        RETURN m.role AS role, m.text AS text, m.timestamp AS ts
        ORDER BY m.timestamp
        """
        results = self.run_cypher(query, {"userId": user_id, "convId": conversation_id})
        out = []
        for row in results:
            out.append({
                "role": row["role"],
                "content": row["text"],
                "timestamp": row["ts"]
            })
        return out

memgraph_conn = MemgraphClient()

