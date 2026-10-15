"""
Sample Demo Project - Utilities Module
Provides utility functions, formatting helpers, and test demonstrations.
NOTE: Insecure functions below are intentional static analysis test demonstrations and are not executed.
"""

import hashlib
import yaml
import json
from typing import Dict, Any


class DataTransformer:
    """Utility class for data sanitization and transformations."""
    def __init__(self, prefix: str = "item_"):
        self.prefix = prefix

    def transform_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def serialize(self, data: Dict[str, Any]) -> str:
        return json.dumps(data)


class SecurityTokenService:
    """Security token utility demonstration."""
    def __init__(self, salt: str = "demo_salt"):
        self.salt = salt

    def generate_token_md5_demo(self, secret_input: str) -> str:
        # [DEMO SEC007]: Intentional static analysis demonstration of weak MD5 hash
        return hashlib.md5(f"{self.salt}_{secret_input}".encode()).hexdigest()

    def generate_token_safe(self, secret_input: str) -> str:
        # Safe recommended alternative
        return hashlib.sha256(f"{self.salt}_{secret_input}".encode()).hexdigest()


def load_yaml_config_demo(raw_yaml_string: str) -> Any:
    # [DEMO SEC006]: Intentional static analysis demonstration of unsafe yaml load
    return yaml.load(raw_yaml_string)


def load_yaml_config_safe(raw_yaml_string: str) -> Any:
    # Safe recommended alternative
    return yaml.safe_load(raw_yaml_string)
