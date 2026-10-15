import os
import zipfile
from pathlib import Path
target_zip = Path(__file__).resolve().parent / "demo_sample_project.zip"

files = {
    "server.py": """\"\"\"
Main Web Server Module
Demonstrates imports, routing, and dynamic execution risks.
\"\"\"
import os
import requests
from auth_service import authenticate_user, generate_session_token
from db_manager import DatabaseManager
from data_exporter import export_user_data

# [SEC008] Debug mode enabled
DEBUG = True

def handle_user_login(username, password):
    db = DatabaseManager()
    is_valid = authenticate_user(username, password)
    if is_valid:
        return generate_session_token(username)
    return None

def execute_dynamic_calculation(expression_str):
    # [SEC001] Dangerous dynamic code evaluation using eval
    return eval(expression_str)

def main():
    print("Server starting with DEBUG =", DEBUG)

if __name__ == "__main__":
    main()
""",

    "auth_service.py": """\"\"\"
Authentication Service
Creates circular coupling by importing db_manager.
\"\"\"
import hashlib
from db_manager import get_user_record

# [SEC005] Hardcoded private API secret
API_SECRET_KEY = "sk_live_9876543210abcdef123456"

def hash_user_password(password):
    # [SEC007] Weak cryptographic hash (MD5)
    return hashlib.md5(password.encode()).hexdigest()

def authenticate_user(username, raw_password):
    hashed = hash_user_password(raw_password)
    user = get_user_record(username)
    return user is not None and user.get("password") == hashed

def generate_session_token(username):
    return f"token_{username}_{hash_user_password(username)}"
""",

    "db_manager.py": """\"\"\"
Database Persistence Layer
Imports auth_service, forming a circular dependency:
(auth_service.py <-> db_manager.py)
\"\"\"
import auth_service

class DatabaseManager:
    def __init__(self, host="localhost"):
        self.host = host

    def find_user_by_name(self, cursor, username):
        # [SEC002] SQL Injection risk from dynamic formatting
        sql_query = f"SELECT id, username, password FROM users WHERE username = '{username}'"
        return cursor.execute(sql_query)

    def execute_raw_search(self, cursor, request_obj):
        # [SEC003] Direct raw request concatenation into query
        query = "SELECT * FROM products WHERE category = " + request_obj.args["category"]
        return cursor.execute(query)

def get_user_record(username):
    return {"username": username, "password": "mock_hashed_password"}
""",

    "data_exporter.py": """\"\"\"
Data Backup and System Utilities
\"\"\"
import os
import pickle
import subprocess

def deserialize_backup(blob_data):
    # [SEC006] Unsafe deserialization using pickle
    return pickle.loads(blob_data)

def compress_export_archive(archive_name):
    # [SEC004] Unsafe command execution via shell=True
    subprocess.call(f"tar -czf {archive_name}.tar.gz /data", shell=True)

def cleanup_temp_files(temp_folder):
    # [SEC004] Unsafe shell execution via os.system
    os.system(f"rm -rf {temp_folder}")
""",

    "client.py": """\"\"\"
External Payment Client
\"\"\"
import requests

def fetch_payment_status():
    # [SEC010] TLS certificate verification disabled
    return requests.get("https://payments.internal.api/status", verify=False)
""",

    "frontend_app.js": """/**
 * Frontend UI Script
 */
function renderUserProfile(containerId, username) {
    // [SEC009] Potential XSS sink using innerHTML
    document.getElementById(containerId).innerHTML = "<h3>Welcome, " + username + "</h3>";
}
""",

    "requirements.txt": """requests>=2.31.0
pyyaml>=6.0.1
psycopg2-binary>=2.9.9
"""
}

with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for filename, content in files.items():
        z.writestr(filename, content.strip())

print("SUCCESS: demo_sample_project.zip created at:", target_zip)
