"""
Custom exceptions for CodeGraph AI backend.
"""

class CodeGraphException(Exception):
    """Base exception for CodeGraph AI."""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class DatabaseConnectionError(CodeGraphException):
    """Raised when Neo4j is unreachable or authentication fails."""
    def __init__(self, message: str = "Unable to connect to Neo4j database", details: dict = None):
        super().__init__(message, status_code=503, details=details)


class InvalidUploadError(CodeGraphException):
    """Raised when an uploaded ZIP file is invalid, corrupt, or exceeds limits."""
    def __init__(self, message: str = "Invalid upload package", details: dict = None):
        super().__init__(message, status_code=400, details=details)


class PathTraversalError(CodeGraphException):
    """Raised when a zip or file path attempts directory traversal."""
    def __init__(self, message: str = "Path traversal detected and rejected", details: dict = None):
        super().__init__(message, status_code=400, details=details)


class ProjectNotFoundError(CodeGraphException):
    """Raised when requested project cannot be found."""
    def __init__(self, project_id: str, message: str = None):
        msg = message or f"Project with ID '{project_id}' not found."
        super().__init__(msg, status_code=404, details={"project_id": project_id})


class ScanError(CodeGraphException):
    """Raised when a project scan fails."""
    def __init__(self, message: str = "Failed to scan codebase", details: dict = None):
        super().__init__(message, status_code=500, details=details)


class AIServiceError(CodeGraphException):
    """Raised when AI review generation fails."""
    def __init__(self, message: str = "AI service error", details: dict = None):
        super().__init__(message, status_code=502, details=details)
