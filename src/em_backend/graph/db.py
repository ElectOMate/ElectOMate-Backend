"""Apache AGE graph database connection manager."""

from __future__ import annotations

import json
from typing import Any

import psycopg2
import structlog

from em_backend.core.config import settings

logger = structlog.get_logger(__name__)

# Graph name used for the argument knowledge graph
GRAPH_NAME = "hungarian_politics"


def get_connection() -> psycopg2.extensions.connection:
    """Create a new synchronous connection to the AGE PostgreSQL database."""
    conn = psycopg2.connect(settings.age_postgres_url)
    conn.autocommit = False
    return conn


def ensure_graph_exists(conn: psycopg2.extensions.connection) -> None:
    """Create the graph if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")
        # Check if graph exists
        cur.execute(
            "SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s;",
            (GRAPH_NAME,),
        )
        if cur.fetchone()[0] == 0:
            cur.execute(f"SELECT create_graph('{GRAPH_NAME}');")
            logger.info("Created AGE graph", graph=GRAPH_NAME)
        conn.commit()


def execute_cypher(
    conn: psycopg2.extensions.connection,
    cypher: str,
    params: dict[str, Any] | None = None,
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Execute a Cypher query against the AGE graph.

    Args:
        conn: Database connection.
        cypher: Cypher query string.
        params: Optional parameters for the query.
        columns: Expected column names for the result set.

    Returns:
        List of result dictionaries.
    """
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")

        # Build the AGE query wrapper
        if columns:
            col_defs = ", ".join(f"{c} agtype" for c in columns)
        else:
            col_defs = "v agtype"

        # Substitute params into cypher if provided
        query_cypher = cypher
        if params:
            for key, value in params.items():
                placeholder = f"${key}"
                if isinstance(value, str):
                    query_cypher = query_cypher.replace(
                        placeholder, f"'{value}'"
                    )
                elif isinstance(value, (int, float)):
                    query_cypher = query_cypher.replace(
                        placeholder, str(value)
                    )
                elif isinstance(value, bool):
                    query_cypher = query_cypher.replace(
                        placeholder, str(value).lower()
                    )
                elif isinstance(value, list):
                    query_cypher = query_cypher.replace(
                        placeholder, json.dumps(value)
                    )
                else:
                    query_cypher = query_cypher.replace(
                        placeholder, f"'{value}'"
                    )

        sql = f"""
            SELECT * FROM cypher('{GRAPH_NAME}', $$
                {query_cypher}
            $$) as ({col_defs});
        """

        cur.execute(sql)
        rows = cur.fetchall()

        results = []
        if columns:
            for row in rows:
                result = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    if isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    result[col] = val
                results.append(result)
        else:
            for row in rows:
                val = row[0]
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append({"v": val})

        return results


def execute_cypher_write(
    conn: psycopg2.extensions.connection,
    cypher: str,
    params: dict[str, Any] | None = None,
) -> None:
    """Execute a write Cypher query (CREATE, MERGE, SET, DELETE)."""
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")

        query_cypher = cypher
        if params:
            for key, value in params.items():
                placeholder = f"${key}"
                if isinstance(value, str):
                    escaped = value.replace("'", "\\'")
                    query_cypher = query_cypher.replace(
                        placeholder, f"'{escaped}'"
                    )
                elif isinstance(value, (int, float)):
                    query_cypher = query_cypher.replace(
                        placeholder, str(value)
                    )
                elif isinstance(value, bool):
                    query_cypher = query_cypher.replace(
                        placeholder, str(value).lower()
                    )
                else:
                    query_cypher = query_cypher.replace(
                        placeholder, f"'{value}'"
                    )

        sql = f"""
            SELECT * FROM cypher('{GRAPH_NAME}', $$
                {query_cypher}
            $$) as (v agtype);
        """

        cur.execute(sql)


class GraphDB:
    """High-level graph database manager."""

    def __init__(self) -> None:
        self._conn: psycopg2.extensions.connection | None = None

    def connect(self) -> None:
        """Establish connection and ensure graph exists."""
        self._conn = get_connection()
        ensure_graph_exists(self._conn)
        logger.info("Connected to AGE graph database", graph=GRAPH_NAME)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("Closed AGE graph database connection")

    @property
    def conn(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            self.connect()
        return self._conn  # type: ignore[return-value]

    def query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read query."""
        results = execute_cypher(self.conn, cypher, params, columns)
        self.conn.commit()
        return results

    def write(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Execute a write query."""
        execute_cypher_write(self.conn, cypher, params)
        self.conn.commit()


# Singleton instance
_graph_db: GraphDB | None = None


def get_graph_db() -> GraphDB:
    """Get or create the singleton GraphDB instance."""
    global _graph_db
    if _graph_db is None:
        _graph_db = GraphDB()
    return _graph_db
