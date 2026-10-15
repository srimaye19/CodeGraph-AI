# CodeGraph AI — System Architecture

CodeGraph AI converts software codebases into interactive, queryable architectural knowledge graphs stored in **Neo4j** and delivers automated static security audits and AI-driven architectural evaluations.

---

## 1. High-Level Architecture Overview

```
+-------------------------------------------------------------------------+
|                        Browser Dashboard (SPA)                         |
|  HTML5 + Vanilla CSS3 (Dark Theme) + vis-network + Fetch API Client     |
+------------------------------------+------------------------------------+
                                     |  HTTP REST / JSON
                                     v
+-------------------------------------------------------------------------+
|                       FastAPI Backend Service                           |
|  - Uvicorn ASGI Server                                                  |
|  - Request Validation & Zip Slip / Traversal Guards                     |
|  - CORS & Static Assets Hosting                                         |
+-------------------+--------------------+-------------------+------------+
                    |                    |                   |
                    v                    v                   v
+-----------------------+ +--------------------+ +------------------------+
| Codebase Analyzer     | | Security Scanner   | | AI Review Engine       |
| - Python AST Visitor  | | - AST & Regex Rules| | - Deterministic Engine |
| - JS / PHP Regex      | | - SEC001 - SEC010  | | - Gemini / OpenAI      |
| - Call Graph Extractor| | - CWE Tagging      | | - Refactoring Guidance |
+-----------+-----------+ +----------+---------+ +------------------------+
            |                        |
            +------------+-----------+
                         v
+-------------------------------------------------------------------------+
|                     Graph Persistence Layer                             |
|  - Neo4j Official Python Driver                                         |
|  - Parameterized Cypher Queries                                         |
|  - In-Memory High-Fidelity Fallback Repository                          |
+------------------------------------+------------------------------------+
                                     |  Bolt Protocol / neo4j+s://
                                     v
+-------------------------------------------------------------------------+
|                        Neo4j Graph Database                             |
|            (Neo4j Aura Free Cloud or Local Docker Instance)             |
+-------------------------------------------------------------------------+
```

---

## 2. Graph Data Model

Each node is uniquely identified by a composite key scoped to the project (`{project_id}::{entity_id}`) to ensure complete data isolation across scans.

### Nodes:
- **`Project`**: Root node representing an audited codebase (`id`, `name`, `scanned_at`, `files_count`, `loc`).
- **`File`**: Represents a source file (`id`, `project_id`, `path`, `name`, `language`, `loc`).
- **`Symbol`**: Functions, async functions, methods, and classes (`id`, `project_id`, `name`, `type`, `file`, `line`).
- **`Package`**: Third-party external libraries (`id`, `project_id`, `name`).
- **`Finding`**: Detected security vulnerabilities and code risks (`id`, `project_id`, `rule_id`, `severity`, `message`, `file`, `line`, `snippet`, `recommendation`, `confidence`, `cwe_id`).

### Relationships:
- `(:Project)-[:CONTAINS_FILE]->(:File)`
- `(:File)-[:DEFINES]->(:Symbol)`
- `(:File)-[:DEPENDS_ON]->(:File)` (Internal import coupling)
- `(:File)-[:USES_PACKAGE]->(:Package)` (Third-party library usage)
- `(:Symbol)-[:CALLS]->(:Symbol)` (Function-to-function invocation)
- `(:File)-[:HAS_FINDING]->(:Finding)` (Vulnerability location)

---

## 3. Graph Analysis Algorithms

### A. Circular Dependency Detection
Circular imports between modules lead to fragile coupling, test initialization order bugs, and runtime import exceptions. CodeGraph AI detects circular chains using bounded Cypher graph traversals:

```cypher
MATCH path = (f1:File {project_id: $pid})-[:DEPENDS_ON*2..6]->(f1)
RETURN [node in nodes(path) | node.path] AS cycle
LIMIT 10;
```

### B. Dependency Hotspots (In-Degree & Out-Degree)
CodeGraph AI identifies critical structural bottlenecks by calculating both incoming dependents (files that depend on this module) and outgoing dependencies (files this module imports):

```cypher
MATCH (f:File {project_id: $pid})
OPTIONAL MATCH (other:File {project_id: $pid})-[:DEPENDS_ON]->(f)
OPTIONAL MATCH (f)-[:DEPENDS_ON]->(target:File {project_id: $pid})
WITH f, count(DISTINCT other) AS in_degree, count(DISTINCT target) AS out_degree
WHERE in_degree > 0 OR out_degree > 0
RETURN f.path AS path, in_degree, out_degree, (in_degree + out_degree) AS total_deps
ORDER BY total_deps DESC
LIMIT 10;
```

---

## 4. Security Scanning Pipeline

1. **Python**: Scanned via standard library `ast.NodeVisitor`. Because parsing occurs on the abstract syntax tree, comment text and docstrings never produce false-positive security alerts.
2. **JavaScript / PHP**: Scanned using conservative regex pattern matching with multi-line comment boundary detection.
3. **No Execution Guarantee**: Analyzed source code is never executed, imported into the running Python runtime, or evaluated.

---

## 5. Dual-Mode Graph Architecture

- **Neo4j Production Driver**: Connects to Neo4j Aura Free or local Neo4j over encrypted Bolt connections (`neo4j+s://` or `bolt://`).
- **In-Memory Repository Fallback**: Automatically activates when Neo4j credentials are not configured or offline. Enables unit testing and offline development with 100% feature fidelity.
