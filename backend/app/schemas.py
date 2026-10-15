"""
Pydantic data schemas for request and response models across CodeGraph AI.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


from pydantic import BaseModel, Field, ConfigDict


# ------------------------------------------------------------------------------
# Health Check Models
# ------------------------------------------------------------------------------

class Neo4jHealth(BaseModel):
    connected: bool
    configured: bool
    uri: str
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "CodeGraph AI"
    version: str = "1.0.0"
    neo4j: Neo4jHealth
    timestamp: str


# ------------------------------------------------------------------------------
# Scan Request & Response Models
# ------------------------------------------------------------------------------

class ScanPathRequest(BaseModel):
    path: str = Field(..., description="Absolute or relative path to project directory")
    project_name: Optional[str] = Field(None, description="Optional custom project name")


class ScanStats(BaseModel):
    files_scanned: int = 0
    lines_of_code: int = 0
    functions_count: int = 0
    classes_count: int = 0
    packages_count: int = 0
    findings_count: int = 0
    duration_ms: float = 0.0


class ScanResponse(BaseModel):
    project_id: str
    project_name: str
    scan_timestamp: str
    stats: ScanStats
    message: str = "Scan completed successfully"


# ------------------------------------------------------------------------------
# Project Models
# ------------------------------------------------------------------------------

class ProjectListItem(BaseModel):
    id: str
    name: str
    scan_timestamp: str
    files_count: int = 0
    findings_count: int = 0


class ProjectSummary(BaseModel):
    project_id: str
    project_name: str
    scan_timestamp: str
    file_counts: int = 0
    symbol_counts: int = 0
    package_counts: int = 0
    security_severity_counts: Dict[str, int] = Field(
        default_factory=lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    )
    dependency_hotspots: List[Dict[str, Any]] = Field(default_factory=list)
    circular_dependencies: List[List[str]] = Field(default_factory=list)
    top_packages: List[Dict[str, Any]] = Field(default_factory=list)
    largest_files: List[Dict[str, Any]] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Graph Models (vis-network compatible)
# ------------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # 'file', 'symbol', 'package', 'finding'
    title: Optional[str] = None
    group: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    color: Optional[Dict[str, Any] | str] = None
    shape: Optional[str] = None
    size: Optional[int] = None


class GraphEdge(BaseModel):
    id: str
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    label: str
    type: str  # 'CONTAINS_FILE', 'DEFINES', 'DEPENDS_ON', 'USES_PACKAGE', 'CALLS', 'HAS_FINDING'
    properties: Dict[str, Any] = Field(default_factory=dict)
    arrows: Optional[str] = "to"
    color: Optional[Dict[str, Any] | str] = None

    model_config = ConfigDict(populate_by_name=True)


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int


# ------------------------------------------------------------------------------
# Security Finding Models
# ------------------------------------------------------------------------------

class FindingItem(BaseModel):
    id: str
    rule_id: str
    severity: str  # HIGH, MEDIUM, LOW
    message: str
    file: str
    line: int
    snippet: str
    recommendation: str
    confidence: str  # HIGH, MEDIUM, LOW
    cwe_id: Optional[str] = None


class FindingsResponse(BaseModel):
    findings: List[FindingItem]
    total: int
    page: int
    limit: int


# ------------------------------------------------------------------------------
# File Metadata Models
# ------------------------------------------------------------------------------

class FileItem(BaseModel):
    id: str
    path: str
    name: str
    language: str
    loc: int
    functions_count: int = 0
    classes_count: int = 0
    findings_count: int = 0


class FileDetailResponse(BaseModel):
    id: str
    path: str
    name: str
    language: str
    loc: int
    functions: List[Dict[str, Any]] = Field(default_factory=list)
    classes: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    packages: List[str] = Field(default_factory=list)
    findings: List[FindingItem] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# AI Review Models
# ------------------------------------------------------------------------------

class AIReviewRequest(BaseModel):
    focus_areas: Optional[List[str]] = None


class RecommendationItem(BaseModel):
    title: str
    category: str
    severity: str
    details: str


class AIReviewResponse(BaseModel):
    project_id: str
    provider_used: str
    is_fallback: bool
    architecture_overview: str
    key_dependencies: List[str]
    security_concerns: List[str]
    recommendations: List[RecommendationItem]
    refactoring_priorities: List[str]
    circular_import_observations: str
    limitations_and_uncertainty: str
    raw_markdown: str
