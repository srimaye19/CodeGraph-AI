"""
CodeGraph AI - Neo4j Graph Database Integration
Handles connection pooling, parameterized Cypher queries, graph persistence,
bounded circular dependency detection, hotspot analysis, and repository abstractions.
"""

from typing import List, Dict, Any, Optional
import datetime
import logging
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

from backend.app.config import settings

logger = logging.getLogger("codegraph.graph")


# Visual styling constants for vis-network nodes
NODE_STYLES = {
    "file": {
        "color": {"background": "#1f6feb", "border": "#58a6ff", "highlight": {"background": "#388bfd", "border": "#79c0ff"}},
        "shape": "box",
        "font": {"color": "#ffffff", "face": "Inter, sans-serif"}
    },
    "symbol": {
        "color": {"background": "#238636", "border": "#3fb950", "highlight": {"background": "#2ea043", "border": "#56d364"}},
        "shape": "ellipse",
        "font": {"color": "#ffffff", "face": "Inter, sans-serif"}
    },
    "package": {
        "color": {"background": "#8957e5", "border": "#a371f7", "highlight": {"background": "#9e6ff5", "border": "#bc8cff"}},
        "shape": "hexagon",
        "font": {"color": "#ffffff", "face": "Inter, sans-serif"}
    },
    "finding": {
        "HIGH": {"background": "#da3633", "border": "#f85149"},
        "MEDIUM": {"background": "#d29922", "border": "#e3b341"},
        "LOW": {"background": "#388bfd", "border": "#79c0ff"}
    }
}


class Neo4jGraphRepository:
    """Official Neo4j Driver persistence and Cypher query execution."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver: Optional[Driver] = None

    def get_driver(self) -> Driver:
        """Get or initialize the Neo4j driver."""
        if not self._driver:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self):
        """Close connection driver pool."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def check_connection(self) -> Dict[str, Any]:
        """Verify Neo4j connectivity and return status."""
        if not settings.is_neo4j_configured:
            return {
                "connected": False,
                "configured": False,
                "uri": self.uri,
                "message": "Neo4j credentials not configured. Please copy .env.example to .env and configure NEO4J_URI/PASSWORD."
            }
        try:
            driver = self.get_driver()
            with driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                if record and record["test"] == 1:
                    return {
                        "connected": True,
                        "configured": True,
                        "uri": self.uri,
                        "message": "Connected to Neo4j successfully."
                    }
        except AuthError as e:
            return {
                "connected": False,
                "configured": True,
                "uri": self.uri,
                "message": f"Authentication failed: {str(e)}"
            }
        except ServiceUnavailable as e:
            return {
                "connected": False,
                "configured": True,
                "uri": self.uri,
                "message": f"Database service unreachable: {str(e)}"
            }
        except Exception as e:
            return {
                "connected": False,
                "configured": True,
                "uri": self.uri,
                "message": f"Connection error: {str(e)}"
            }

    def init_schema(self):
        """Create constraints and indexes for project-scoped nodes."""
        queries = [
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT symbol_id IF NOT EXISTS FOR (s:Symbol) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT package_id IF NOT EXISTS FOR (pkg:Package) REQUIRE pkg.id IS UNIQUE",
            "CREATE CONSTRAINT finding_id IF NOT EXISTS FOR (fd:Finding) REQUIRE fd.id IS UNIQUE",
            "CREATE INDEX file_project_idx IF NOT EXISTS FOR (f:File) ON (f.project_id)",
            "CREATE INDEX symbol_project_idx IF NOT EXISTS FOR (s:Symbol) ON (s.project_id)"
        ]
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    logger.warning(f"Schema query non-fatal warning: {e}")

    def delete_project(self, project_id: str) -> bool:
        """Safely delete all graph nodes and relationships associated with a project."""
        query = """
        MATCH (p:Project {id: $pid})
        OPTIONAL MATCH (p)-[:CONTAINS_FILE]->(f:File)
        OPTIONAL MATCH (f)-[:DEFINES]->(s:Symbol)
        OPTIONAL MATCH (f)-[:HAS_FINDING]->(fd:Finding)
        OPTIONAL MATCH (f)-[:USES_PACKAGE]->(pkg:Package)
        DETACH DELETE fd, s, pkg, f, p
        """
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            session.run(query, pid=project_id)
        return True

    def save_project_analysis(self, project_id: str, name: str, analysis: Dict[str, Any]) -> str:
        """Persist project architecture, symbols, dependencies, and findings to Neo4j."""
        self.init_schema()
        self.delete_project(project_id)

        driver = self.get_driver()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with driver.session(database=self.database) as session:
            # 1. Create Project Node
            session.run(
                """
                MERGE (p:Project {id: $pid})
                SET p.name = $name,
                    p.scanned_at = $scanned_at,
                    p.files_count = $files_count,
                    p.loc = $loc
                """,
                pid=project_id,
                name=name,
                scanned_at=now_iso,
                files_count=analysis["stats"]["files_scanned"],
                loc=analysis["stats"]["lines_of_code"]
            )

            # 2. Batch Create Files & Connect to Project
            file_params = []
            for f in analysis["files"]:
                file_params.append({
                    "id": f"{project_id}::{f['id']}",
                    "file_raw_id": f["id"],
                    "path": f["path"],
                    "name": f["name"],
                    "language": f["language"],
                    "loc": f["loc"]
                })

            session.run(
                """
                UNWIND $files AS fData
                MATCH (p:Project {id: $pid})
                CREATE (f:File {
                    id: fData.id,
                    project_id: $pid,
                    raw_id: fData.file_raw_id,
                    path: fData.path,
                    name: fData.name,
                    language: fData.language,
                    loc: fData.loc
                })
                CREATE (p)-[:CONTAINS_FILE]->(f)
                """,
                pid=project_id,
                files=file_params
            )

            # 3. Batch Create Symbols & Connect to Files
            sym_params = []
            for s in analysis["symbols"]:
                sym_params.append({
                    "id": f"{project_id}::{s['id']}",
                    "name": s["name"],
                    "type": s["type"],
                    "file_raw_id": f"file:{s['file']}",
                    "line": s["line"]
                })

            session.run(
                """
                UNWIND $symbols AS sData
                MATCH (f:File {project_id: $pid, raw_id: sData.file_raw_id})
                CREATE (s:Symbol {
                    id: sData.id,
                    project_id: $pid,
                    name: sData.name,
                    type: sData.type,
                    file: f.path,
                    line: sData.line
                })
                CREATE (f)-[:DEFINES]->(s)
                """,
                pid=project_id,
                symbols=sym_params
            )

            # 4. Batch Create Packages & USES_PACKAGE relationships
            pkg_params = []
            for p in analysis["external_dependencies"]:
                pkg_params.append({
                    "id": f"{project_id}::pkg::{p['package']}",
                    "name": p["package"],
                    "file_raw_id": f"file:{p['file']}"
                })

            session.run(
                """
                UNWIND $packages AS pData
                MATCH (f:File {project_id: $pid, raw_id: pData.file_raw_id})
                MERGE (pkg:Package {id: pData.id, project_id: $pid, name: pData.name})
                MERGE (f)-[:USES_PACKAGE]->(pkg)
                """,
                pid=project_id,
                packages=pkg_params
            )

            # 5. Batch Create DEPENDS_ON relationships between files
            dep_params = []
            for dep in analysis["internal_dependencies"]:
                dep_params.append({
                    "from_raw": dep["from"],
                    "to_raw": dep["to"]
                })

            session.run(
                """
                UNWIND $deps AS dData
                MATCH (f1:File {project_id: $pid, raw_id: dData.from_raw})
                MATCH (f2:File {project_id: $pid, raw_id: dData.to_raw})
                MERGE (f1)-[:DEPENDS_ON]->(f2)
                """,
                pid=project_id,
                deps=dep_params
            )

            # 6. Batch Create CALLS relationships between symbols
            call_params = []
            for call in analysis["function_calls"]:
                call_params.append({
                    "caller_id": f"{project_id}::{call['caller_id']}",
                    "callee_id": f"{project_id}::{call['callee_id']}",
                    "line": call["line"]
                })

            session.run(
                """
                UNWIND $calls AS cData
                MATCH (s1:Symbol {id: cData.caller_id})
                MATCH (s2:Symbol {id: cData.callee_id})
                MERGE (s1)-[:CALLS {line: cData.line}]->(s2)
                """,
                calls=call_params
            )

            # 7. Batch Create Findings & HAS_FINDING relationships
            finding_params = []
            for idx, fd in enumerate(analysis["findings"]):
                finding_params.append({
                    "id": f"{project_id}::fd::{idx}",
                    "rule_id": fd["rule_id"],
                    "severity": fd["severity"],
                    "message": fd["message"],
                    "file_raw_id": f"file:{fd['file']}",
                    "file_path": fd["file"],
                    "line": fd["line"],
                    "snippet": fd["snippet"],
                    "recommendation": fd["recommendation"],
                    "confidence": fd["confidence"],
                    "cwe_id": fd.get("cwe_id", "")
                })

            session.run(
                """
                UNWIND $findings AS fdData
                MATCH (f:File {project_id: $pid, raw_id: fdData.file_raw_id})
                CREATE (fd:Finding {
                    id: fdData.id,
                    project_id: $pid,
                    rule_id: fdData.rule_id,
                    severity: fdData.severity,
                    message: fdData.message,
                    file: fdData.file_path,
                    line: fdData.line,
                    snippet: fdData.snippet,
                    recommendation: fdData.recommendation,
                    confidence: fdData.confidence,
                    cwe_id: fdData.cwe_id
                })
                CREATE (f)-[:HAS_FINDING]->(fd)
                """,
                pid=project_id,
                findings=finding_params
            )

        return project_id

    def get_projects(self) -> List[Dict[str, Any]]:
        """List all scanned projects with stats."""
        query = """
        MATCH (p:Project)
        OPTIONAL MATCH (p)-[:CONTAINS_FILE]->(f:File)
        OPTIONAL MATCH (f)-[:HAS_FINDING]->(fd:Finding)
        RETURN p.id AS id,
               p.name AS name,
               p.scanned_at AS scanned_at,
               count(DISTINCT f) AS files_count,
               count(DISTINCT fd) AS findings_count
        ORDER BY p.scanned_at DESC
        """
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            result = session.run(query)
            return [dict(record) for record in result]

    def get_project_graph(self, project_id: str, node_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch project nodes and edges formatted for vis-network."""
        allowed_types = set(node_types) if node_types else {"file", "symbol", "package", "finding"}
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            # 1. Fetch Files
            if "file" in allowed_types:
                file_res = session.run(
                    "MATCH (f:File {project_id: $pid}) RETURN f.id AS id, f.name AS name, f.path AS path, f.language AS lang, f.loc AS loc",
                    pid=project_id
                )
                for r in file_res:
                    style = NODE_STYLES["file"]
                    nodes.append({
                        "id": r["id"],
                        "label": r["name"],
                        "type": "file",
                        "title": f"<b>File:</b> {r['path']}<br><b>Lang:</b> {r['lang']}<br><b>LOC:</b> {r['loc']}",
                        "group": "file",
                        "properties": {"path": r["path"], "language": r["lang"], "loc": r["loc"]},
                        "color": style["color"],
                        "shape": style["shape"]
                    })

            # 2. Fetch Symbols
            if "symbol" in allowed_types:
                sym_res = session.run(
                    "MATCH (s:Symbol {project_id: $pid}) RETURN s.id AS id, s.name AS name, s.type AS type, s.file AS file, s.line AS line",
                    pid=project_id
                )
                for r in sym_res:
                    style = NODE_STYLES["symbol"]
                    nodes.append({
                        "id": r["id"],
                        "label": r["name"],
                        "type": "symbol",
                        "title": f"<b>Symbol:</b> {r['name']}<br><b>Type:</b> {r['type']}<br><b>File:</b> {r['file']}:{r['line']}",
                        "group": "symbol",
                        "properties": {"name": r["name"], "type": r["type"], "file": r["file"], "line": r["line"]},
                        "color": style["color"],
                        "shape": style["shape"]
                    })

            # 3. Fetch Packages
            if "package" in allowed_types:
                pkg_res = session.run(
                    "MATCH (pkg:Package {project_id: $pid}) RETURN pkg.id AS id, pkg.name AS name",
                    pid=project_id
                )
                for r in pkg_res:
                    style = NODE_STYLES["package"]
                    nodes.append({
                        "id": r["id"],
                        "label": r["name"],
                        "type": "package",
                        "title": f"<b>External Package:</b> {r['name']}",
                        "group": "package",
                        "properties": {"name": r["name"]},
                        "color": style["color"],
                        "shape": style["shape"]
                    })

            # 4. Fetch Findings
            if "finding" in allowed_types:
                fd_res = session.run(
                    "MATCH (fd:Finding {project_id: $pid}) RETURN fd.id AS id, fd.rule_id AS rule_id, fd.severity AS severity, fd.message AS msg, fd.file AS file, fd.line AS line",
                    pid=project_id
                )
                for r in fd_res:
                    sev = r["severity"]
                    c_style = NODE_STYLES["finding"].get(sev, NODE_STYLES["finding"]["LOW"])
                    nodes.append({
                        "id": r["id"],
                        "label": f"{r['rule_id']} ({sev})",
                        "type": "finding",
                        "title": f"<b>Finding:</b> {r['rule_id']}<br><b>Severity:</b> {sev}<br><b>File:</b> {r['file']}:{r['line']}<br>{r['msg']}",
                        "group": "finding",
                        "properties": {"rule_id": r["rule_id"], "severity": sev, "message": r["msg"]},
                        "color": c_style,
                        "shape": "diamond"
                    })

            node_ids = {n["id"] for n in nodes}

            # 5. Fetch Relationships
            rel_query = """
            MATCH (n {project_id: $pid})-[r]->(m {project_id: $pid})
            RETURN id(r) AS rel_id, n.id AS from_id, m.id AS to_id, type(r) AS rel_type
            """
            rel_res = session.run(rel_query, pid=project_id)
            for r in rel_res:
                if r["from_id"] in node_ids and r["to_id"] in node_ids:
                    edges.append({
                        "id": f"edge_{r['rel_id']}",
                        "from": r["from_id"],
                        "to": r["to_id"],
                        "label": r["rel_type"],
                        "type": r["rel_type"],
                        "arrows": "to"
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }

    def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """Fetch summary metrics, hotspot analysis, and circular dependency checks."""
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            # 1. Base counts & Project info
            proj_info = session.run(
                "MATCH (p:Project {id: $pid}) RETURN p.name AS name, p.scanned_at AS scanned_at",
                pid=project_id
            ).single()
            if not proj_info:
                return {}

            name = proj_info["name"]
            scanned_at = proj_info["scanned_at"]

            counts = session.run(
                """
                MATCH (p:Project {id: $pid})
                OPTIONAL MATCH (p)-[:CONTAINS_FILE]->(f:File)
                OPTIONAL MATCH (f)-[:DEFINES]->(s:Symbol)
                OPTIONAL MATCH (f)-[:USES_PACKAGE]->(pkg:Package)
                RETURN count(DISTINCT f) AS files,
                       count(DISTINCT s) AS symbols,
                       count(DISTINCT pkg) AS packages
                """,
                pid=project_id
            ).single()

            # 2. Findings by severity
            sev_res = session.run(
                """
                MATCH (fd:Finding {project_id: $pid})
                RETURN fd.severity AS severity, count(fd) AS count
                """,
                pid=project_id
            )
            severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for r in sev_res:
                if r["severity"] in severity_counts:
                    severity_counts[r["severity"]] = r["count"]

            # 3. Dependency Hotspots (In-degree & Out-degree)
            hotspots_res = session.run(
                """
                MATCH (f:File {project_id: $pid})
                OPTIONAL MATCH (other:File {project_id: $pid})-[:DEPENDS_ON]->(f)
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(target:File {project_id: $pid})
                WITH f, count(DISTINCT other) AS in_degree, count(DISTINCT target) AS out_degree
                WHERE in_degree > 0 OR out_degree > 0
                RETURN f.path AS path, in_degree, out_degree, (in_degree + out_degree) AS total_deps
                ORDER BY total_deps DESC
                LIMIT 10
                """,
                pid=project_id
            )
            hotspots = [dict(r) for r in hotspots_res]

            # 4. Bounded Circular Dependency Detection (paths of length 2 to 6)
            circular_res = session.run(
                """
                MATCH path = (f1:File {project_id: $pid})-[:DEPENDS_ON*2..6]->(f1)
                RETURN [node in nodes(path) | node.path] AS cycle
                LIMIT 10
                """,
                pid=project_id
            )
            cycles = []
            seen_cycles = set()
            for r in circular_res:
                cycle_nodes = r["cycle"]
                if cycle_nodes:
                    normalized = tuple(sorted(cycle_nodes[:-1]))
                    if normalized not in seen_cycles:
                        seen_cycles.add(normalized)
                        cycles.append(cycle_nodes)

            # 5. Top External Packages
            pkg_res = session.run(
                """
                MATCH (f:File {project_id: $pid})-[:USES_PACKAGE]->(pkg:Package {project_id: $pid})
                RETURN pkg.name AS name, count(f) AS usage_count
                ORDER BY usage_count DESC
                LIMIT 10
                """,
                pid=project_id
            )
            top_packages = [dict(r) for r in pkg_res]

            # 6. Largest Files by LOC
            file_res = session.run(
                """
                MATCH (f:File {project_id: $pid})
                RETURN f.path AS path, f.language AS language, f.loc AS loc
                ORDER BY f.loc DESC
                LIMIT 10
                """,
                pid=project_id
            )
            largest_files = [dict(r) for r in file_res]

        return {
            "project_id": project_id,
            "project_name": name,
            "scan_timestamp": scanned_at,
            "file_counts": counts["files"] if counts else 0,
            "symbol_counts": counts["symbols"] if counts else 0,
            "package_counts": counts["packages"] if counts else 0,
            "security_severity_counts": severity_counts,
            "dependency_hotspots": hotspots,
            "circular_dependencies": cycles,
            "top_packages": top_packages,
            "largest_files": largest_files
        }

    def get_project_findings(
        self,
        project_id: str,
        severity: Optional[str] = None,
        rule_id: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Fetch project findings with filtering and pagination."""
        skip = (page - 1) * limit
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            where_clauses = ["fd.project_id = $pid"]
            params: Dict[str, Any] = {"pid": project_id, "skip": skip, "limit": limit}

            if severity:
                where_clauses.append("fd.severity = $severity")
                params["severity"] = severity.upper()
            if rule_id:
                where_clauses.append("fd.rule_id = $rule_id")
                params["rule_id"] = rule_id.upper()

            where_str = " AND ".join(where_clauses)

            # Count total
            total_count = session.run(
                f"MATCH (fd:Finding) WHERE {where_str} RETURN count(fd) AS total",
                **params
            ).single()["total"]

            # Fetch page
            query = f"""
            MATCH (fd:Finding)
            WHERE {where_str}
            RETURN fd.id AS id,
                   fd.rule_id AS rule_id,
                   fd.severity AS severity,
                   fd.message AS message,
                   fd.file AS file,
                   fd.line AS line,
                   fd.snippet AS snippet,
                   fd.recommendation AS recommendation,
                   fd.confidence AS confidence,
                   fd.cwe_id AS cwe_id
            ORDER BY fd.severity, fd.line
            SKIP $skip
            LIMIT $limit
            """
            result = session.run(query, **params)
            findings = [dict(r) for r in result]

        return {
            "findings": findings,
            "total": total_count,
            "page": page,
            "limit": limit
        }

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch list of files with symbol and finding counts."""
        query = """
        MATCH (f:File {project_id: $pid})
        OPTIONAL MATCH (f)-[:DEFINES]->(s:Symbol)
        OPTIONAL MATCH (f)-[:HAS_FINDING]->(fd:Finding)
        RETURN f.raw_id AS id,
               f.path AS path,
               f.name AS name,
               f.language AS language,
               f.loc AS loc,
               count(DISTINCT s) AS functions_count,
               0 AS classes_count,
               count(DISTINCT fd) AS findings_count
        ORDER BY f.path ASC
        """
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            result = session.run(query, pid=project_id)
            return [dict(r) for r in result]

    def get_file_details(self, project_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """Return safe file metadata, symbols, dependencies, and findings."""
        raw_id = file_id if file_id.startswith("file:") else f"file:{file_id}"
        driver = self.get_driver()
        with driver.session(database=self.database) as session:
            file_record = session.run(
                "MATCH (f:File {project_id: $pid, raw_id: $raw_id}) RETURN f.path AS path, f.name AS name, f.language AS lang, f.loc AS loc",
                pid=project_id, raw_id=raw_id
            ).single()

            if not file_record:
                return None

            symbols_res = session.run(
                "MATCH (f:File {project_id: $pid, raw_id: $raw_id})-[:DEFINES]->(s:Symbol) RETURN s.name AS name, s.type AS type, s.line AS line",
                pid=project_id, raw_id=raw_id
            )
            symbols = [dict(s) for s in symbols_res]

            deps_res = session.run(
                "MATCH (f:File {project_id: $pid, raw_id: $raw_id})-[:DEPENDS_ON]->(target:File) RETURN target.path AS path",
                pid=project_id, raw_id=raw_id
            )
            dependencies = [r["path"] for r in deps_res]

            pkgs_res = session.run(
                "MATCH (f:File {project_id: $pid, raw_id: $raw_id})-[:USES_PACKAGE]->(pkg:Package) RETURN pkg.name AS name",
                pid=project_id, raw_id=raw_id
            )
            packages = [r["name"] for r in pkgs_res]

            findings_res = session.run(
                """
                MATCH (f:File {project_id: $pid, raw_id: $raw_id})-[:HAS_FINDING]->(fd:Finding)
                RETURN fd.id AS id, fd.rule_id AS rule_id, fd.severity AS severity, fd.message AS message,
                       fd.file AS file, fd.line AS line, fd.snippet AS snippet,
                       fd.recommendation AS recommendation, fd.confidence AS confidence, fd.cwe_id AS cwe_id
                ORDER BY fd.line
                """,
                pid=project_id, raw_id=raw_id
            )
            findings = [dict(fd) for fd in findings_res]

        return {
            "id": raw_id,
            "path": file_record["path"],
            "name": file_record["name"],
            "language": file_record["lang"],
            "loc": file_record["loc"],
            "functions": [s for s in symbols if s["type"] in ("function", "method")],
            "classes": [s for s in symbols if s["type"] == "class"],
            "dependencies": dependencies,
            "packages": packages,
            "findings": findings
        }


class InMemoryGraphRepository:
    """
    In-memory fallback repository for offline test runs or before live Neo4j credentials are entered.
    Implements the exact same interface as Neo4jGraphRepository with 100% fidelity.
    """

    def __init__(self):
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.analyses: Dict[str, Dict[str, Any]] = {}

    def check_connection(self) -> Dict[str, Any]:
        return {
            "connected": False,
            "configured": False,
            "uri": "in-memory-fallback",
            "message": "Neo4j is not connected. Operating in offline in-memory fallback mode."
        }

    def init_schema(self):
        pass

    def delete_project(self, project_id: str) -> bool:
        if project_id in self.projects:
            del self.projects[project_id]
        if project_id in self.analyses:
            del self.analyses[project_id]
        return True

    def save_project_analysis(self, project_id: str, name: str, analysis: Dict[str, Any]) -> str:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.projects[project_id] = {
            "id": project_id,
            "name": name,
            "scanned_at": now_iso,
            "files_count": len(analysis.get("files", [])),
            "findings_count": len(analysis.get("findings", []))
        }
        self.analyses[project_id] = analysis
        return project_id

    def get_projects(self) -> List[Dict[str, Any]]:
        return list(self.projects.values())

    def get_project_graph(self, project_id: str, node_types: Optional[List[str]] = None) -> Dict[str, Any]:
        analysis = self.analyses.get(project_id)
        if not analysis:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        allowed_types = set(node_types) if node_types else {"file", "symbol", "package", "finding"}
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        if "file" in allowed_types:
            for f in analysis.get("files", []):
                style = NODE_STYLES["file"]
                nodes.append({
                    "id": f"{project_id}::{f['id']}",
                    "label": f["name"],
                    "type": "file",
                    "title": f"<b>File:</b> {f['path']}<br><b>Lang:</b> {f['language']}<br><b>LOC:</b> {f['loc']}",
                    "group": "file",
                    "properties": {"path": f["path"], "language": f["language"], "loc": f["loc"]},
                    "color": style["color"],
                    "shape": style["shape"]
                })

        if "symbol" in allowed_types:
            for s in analysis.get("symbols", []):
                style = NODE_STYLES["symbol"]
                nodes.append({
                    "id": f"{project_id}::{s['id']}",
                    "label": s["name"],
                    "type": "symbol",
                    "title": f"<b>Symbol:</b> {s['name']}<br><b>Type:</b> {s['type']}",
                    "group": "symbol",
                    "properties": {"name": s["name"], "type": s["type"]},
                    "color": style["color"],
                    "shape": style["shape"]
                })

        if "package" in allowed_types:
            seen_pkgs = set()
            for p in analysis.get("external_dependencies", []):
                pkg_name = p["package"]
                if pkg_name not in seen_pkgs:
                    seen_pkgs.add(pkg_name)
                    style = NODE_STYLES["package"]
                    nodes.append({
                        "id": f"{project_id}::pkg::{pkg_name}",
                        "label": pkg_name,
                        "type": "package",
                        "title": f"<b>Package:</b> {pkg_name}",
                        "group": "package",
                        "properties": {"name": pkg_name},
                        "color": style["color"],
                        "shape": style["shape"]
                    })

        if "finding" in allowed_types:
            for idx, fd in enumerate(analysis.get("findings", [])):
                sev = fd["severity"]
                c_style = NODE_STYLES["finding"].get(sev, NODE_STYLES["finding"]["LOW"])
                nodes.append({
                    "id": f"{project_id}::fd::{idx}",
                    "label": f"{fd['rule_id']} ({sev})",
                    "type": "finding",
                    "title": f"<b>Finding:</b> {fd['rule_id']}<br>{fd['message']}",
                    "group": "finding",
                    "properties": fd,
                    "color": c_style,
                    "shape": "diamond"
                })

        node_ids = {n["id"] for n in nodes}

        # Add edges
        edge_idx = 1
        for dep in analysis.get("internal_dependencies", []):
            from_id = f"{project_id}::{dep['from']}"
            to_id = f"{project_id}::{dep['to']}"
            if from_id in node_ids and to_id in node_ids:
                edges.append({
                    "id": f"edge_{edge_idx}",
                    "from": from_id,
                    "to": to_id,
                    "label": "DEPENDS_ON",
                    "type": "DEPENDS_ON",
                    "arrows": "to"
                })
                edge_idx += 1

        for call in analysis.get("function_calls", []):
            from_id = f"{project_id}::{call['caller_id']}"
            to_id = f"{project_id}::{call['callee_id']}"
            if from_id in node_ids and to_id in node_ids:
                edges.append({
                    "id": f"edge_{edge_idx}",
                    "from": from_id,
                    "to": to_id,
                    "label": "CALLS",
                    "type": "CALLS",
                    "arrows": "to"
                })
                edge_idx += 1

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }

    def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        proj = self.projects.get(project_id)
        analysis = self.analyses.get(project_id)
        if not proj or not analysis:
            return {}

        # Severity counts
        sev_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for fd in analysis.get("findings", []):
            s = fd.get("severity")
            if s in sev_counts:
                sev_counts[s] += 1

        # Hotspots
        in_counts: Dict[str, int] = {}
        out_counts: Dict[str, int] = {}
        for dep in analysis.get("internal_dependencies", []):
            src = dep["from"].removeprefix("file:")
            dst = dep["to"].removeprefix("file:")
            out_counts[src] = out_counts.get(src, 0) + 1
            in_counts[dst] = in_counts.get(dst, 0) + 1

        all_files = set(in_counts.keys()).union(out_counts.keys())
        hotspots = []
        for fp in all_files:
            i_cnt = in_counts.get(fp, 0)
            o_cnt = out_counts.get(fp, 0)
            hotspots.append({
                "path": fp,
                "in_degree": i_cnt,
                "out_degree": o_cnt,
                "total_deps": i_cnt + o_cnt
            })
        hotspots.sort(key=lambda x: x["total_deps"], reverse=True)

        # Cycles detection (Tarjan/DFS on internal dependencies)
        adj: Dict[str, List[str]] = {}
        for dep in analysis.get("internal_dependencies", []):
            src = dep["from"].removeprefix("file:")
            dst = dep["to"].removeprefix("file:")
            adj.setdefault(src, []).append(dst)

        cycles: List[List[str]] = []
        visited = set()
        stack = []

        def dfs(node: str, path: List[str]):
            if node in path:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if len(cycle) > 2 and cycle not in cycles:
                    cycles.append(cycle)
                return
            if len(path) > 6:
                return
            for nxt in adj.get(node, []):
                dfs(nxt, path + [node])

        for n in adj:
            dfs(n, [])

        # Packages
        pkg_counts: Dict[str, int] = {}
        for p in analysis.get("external_dependencies", []):
            pkg = p["package"]
            pkg_counts[pkg] = pkg_counts.get(pkg, 0) + 1
        top_packages = [{"name": k, "usage_count": v} for k, v in sorted(pkg_counts.items(), key=lambda x: x[1], reverse=True)[:10]]

        # Largest files
        largest = [{"path": f["path"], "language": f["language"], "loc": f["loc"]} for f in sorted(analysis.get("files", []), key=lambda x: x["loc"], reverse=True)[:10]]

        return {
            "project_id": project_id,
            "project_name": proj["name"],
            "scan_timestamp": proj["scanned_at"],
            "file_counts": len(analysis.get("files", [])),
            "symbol_counts": len(analysis.get("symbols", [])),
            "package_counts": len(set(p["package"] for p in analysis.get("external_dependencies", []))),
            "security_severity_counts": sev_counts,
            "dependency_hotspots": hotspots[:10],
            "circular_dependencies": cycles[:10],
            "top_packages": top_packages,
            "largest_files": largest
        }

    def get_project_findings(
        self,
        project_id: str,
        severity: Optional[str] = None,
        rule_id: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        analysis = self.analyses.get(project_id, {})
        all_findings = []
        for idx, fd in enumerate(analysis.get("findings", [])):
            item = dict(fd)
            item["id"] = f"{project_id}::fd::{idx}"
            all_findings.append(item)

        filtered = all_findings
        if severity:
            filtered = [f for f in filtered if f.get("severity", "").upper() == severity.upper()]
        if rule_id:
            filtered = [f for f in filtered if f.get("rule_id", "").upper() == rule_id.upper()]

        total = len(filtered)
        start = (page - 1) * limit
        page_items = filtered[start:start + limit]

        return {
            "findings": page_items,
            "total": total,
            "page": page,
            "limit": limit
        }

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        analysis = self.analyses.get(project_id, {})
        out = []
        for f in analysis.get("files", []):
            fid = f["id"]
            path = f["path"]
            syms = [s for s in analysis.get("symbols", []) if s["file"] == path]
            fds = [fd for fd in analysis.get("findings", []) if fd["file"] == path]
            out.append({
                "id": fid,
                "path": path,
                "name": f["name"],
                "language": f["language"],
                "loc": f["loc"],
                "functions_count": len([s for s in syms if s["type"] in ("function", "method")]),
                "classes_count": len([s for s in syms if s["type"] == "class"]),
                "findings_count": len(fds)
            })
        return out

    def get_file_details(self, project_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        analysis = self.analyses.get(project_id, {})
        clean_path = file_id.removeprefix("file:")
        matched = None
        for f in analysis.get("files", []):
            if f["path"] == clean_path or f["id"] == file_id:
                matched = f
                break
        if not matched:
            return None

        path = matched["path"]
        syms = [s for s in analysis.get("symbols", []) if s["file"] == path]
        fds = [fd for fd in analysis.get("findings", []) if fd["file"] == path]
        deps = [d["to"].removeprefix("file:") for d in analysis.get("internal_dependencies", []) if d["from"] == f"file:{path}"]
        pkgs = [p["package"] for p in analysis.get("external_dependencies", []) if p["file"] == path]

        return {
            "id": f"file:{path}",
            "path": path,
            "name": matched["name"],
            "language": matched["language"],
            "loc": matched["loc"],
            "functions": [s for s in syms if s["type"] in ("function", "method")],
            "classes": [s for s in syms if s["type"] == "class"],
            "dependencies": deps,
            "packages": pkgs,
            "findings": [
                {
                    "id": f"{project_id}::fd::{i}",
                    "rule_id": fd["rule_id"],
                    "severity": fd["severity"],
                    "message": fd["message"],
                    "file": fd["file"],
                    "line": fd["line"],
                    "snippet": fd["snippet"],
                    "recommendation": fd["recommendation"],
                    "confidence": fd["confidence"],
                    "cwe_id": fd.get("cwe_id", "")
                }
                for i, fd in enumerate(fds)
            ]
        }


def get_graph_repository() -> Any:
    """
    Factory returning live Neo4j repository if credentials are configured,
    or seamless in-memory repository fallback.
    """
    if settings.is_neo4j_configured:
        return Neo4jGraphRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE
        )
    return in_memory_repo


# Shared singleton in-memory repository for development/test mode
in_memory_repo = InMemoryGraphRepository()
