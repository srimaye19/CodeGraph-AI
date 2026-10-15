"""
Sample Demo Project - Database Module
Handles simulated database connection pooling, queries, and record management.
NOTE: Insecure queries below are intentional static analysis test demonstrations.
"""

from utils import DataTransformer

# [DEMO SEC005]: Intentional static analysis demonstration of hardcoded credential
DB_TEST_PASSWORD = "HardcodedDatabasePassword999!"


class DatabaseConnection:
    """Simulated database connection manager."""
    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port
        self.transformer = DataTransformer(prefix="db_")

    def connect(self) -> str:
        return f"Connected to {self.host}:{self.port}"

    def execute_insecure_query_demo(self, cursor, user_input: str):
        # [DEMO SEC002]: Intentional static analysis demonstration of SQL string formatting
        query = f"SELECT * FROM accounts WHERE username = '{user_input}'"
        return cursor.execute(query)

    def execute_safe_query(self, cursor, user_input: str):
        # Safe parameterized prepared statement
        query = "SELECT * FROM accounts WHERE username = %s"
        return cursor.execute(query, (user_input,))
