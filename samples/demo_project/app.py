"""
Sample Demo Project - Application Entry Point
Demonstrates internal module dependencies, class instantiation, external packages,
and static analysis security rules.
"""

import os
import requests
from database import DatabaseConnection
from utils import SecurityTokenService, DataTransformer

# [DEMO SEC008]: Intentional static analysis demonstration of debug mode enabled
DEBUG = True


def start_service():
    """Service entry point orchestrating database and security components."""
    db = DatabaseConnection()
    status = db.connect()
    
    token_service = SecurityTokenService()
    token = token_service.generate_token_safe("admin_session")
    
    transformer = DataTransformer()
    transformed = transformer.transform_key("session_id")
    
    return {"status": status, "token": token, "key": transformed}


def fetch_external_status_insecure_demo():
    # [DEMO SEC010]: Intentional static analysis demonstration of verify=False
    return requests.get("https://api.internal.service/health", verify=False)


def run_shell_command_demo(command_arg: str):
    # [DEMO SEC004]: Intentional static analysis demonstration of os.system command execution
    os.system(f"echo Status: {command_arg}")


if __name__ == "__main__":
    print("CodeGraph Demo Project running in demo mode...")
    result = start_service()
    print("Initialized service:", result)
