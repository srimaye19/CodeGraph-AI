# CodeGraph AI — Neo4j Database Setup Guide

CodeGraph AI persists codebase architecture into a graph database. You can connect it to **Neo4j Aura Free** (cloud database, recommended for college submissions) or a **Local Neo4j** instance using Docker or Neo4j Desktop.

---

## Option A: Neo4j Aura Free (Recommended Cloud Setup)

Neo4j Aura Free provides a completely free, fully managed cloud graph database instance with no credit card required.

### Step 1: Create a Neo4j Aura Account
1. Open [https://console.neo4j.io/](https://console.neo4j.io/) in your browser.
2. Sign up using your Google account or email address.

### Step 2: Create a Free AuraDB Instance
1. In the Neo4j Aura Console dashboard, click **"New Instance"**.
2. Select **"AuraDB Free"**.
3. Choose your nearest cloud region (e.g., US-East, Europe-West, or Asia-East).
4. Give your instance a name, such as `CodeGraph-DB`.
5. Click **"Create Instance"**.

### Step 3: Save Your Credentials Securely
> **IMPORTANT:** Neo4j will display a generated database password and offer a credentials file download.  
> **Save this password immediately!** Neo4j does not store plain-text passwords and cannot recover it if lost.
- **Default Username:** `neo4j`
- **Password:** `<The generated string from Aura>`

### Step 4: Copy the Connection URI
Once your instance transitions to the green **"Running"** status:
1. Locate the **Connection URI** shown on your instance card.
2. It looks like:
   ```
   neo4j+s://xxxxxxxx.databases.neo4j.io
   ```
3. Copy this URI.

### Step 5: Configure `.env` in CodeGraph AI
Open `.env` in the root of the `codegraph-ai` folder:
```env
NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-actual-saved-password
NEO4J_DATABASE=neo4j
```

### Step 6: Start CodeGraph AI
Run the cloud workflow script:
```cmd
run-cloud.bat
```
Open `http://127.0.0.1:8000/`. The header pill should now display:
`Neo4j Connected` with a green indicator dot!

---

## Option B: Local Neo4j via Docker Compose

If you have Docker Desktop installed on Windows:
1. Start the container using the provided `docker-compose.yml`:
   ```cmd
   docker compose up -d
   ```
2. Configure `.env`:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password123
   NEO4J_DATABASE=neo4j
   ```
3. Open the Neo4j Browser at `http://localhost:7474/`.

---

## Verifying Data with Cypher Queries

You can execute Cypher queries directly inside the **Neo4j Aura Query Tab** or **Neo4j Browser**:

### 1. View Files in Scanned Projects
```cypher
MATCH (p:Project)-[:CONTAINS_FILE]->(f:File)
RETURN p.name AS Project, f.path AS FilePath, f.language AS Language, f.loc AS LinesOfCode
ORDER BY Project, FilePath
LIMIT 25;
```

### 2. View Security Findings by Severity
```cypher
MATCH (f:File)-[:HAS_FINDING]->(x:Finding)
RETURN f.path AS FilePath, x.rule_id AS Rule, x.severity AS Severity, x.line AS LineNumber, x.message AS Description
ORDER BY x.severity, f.path;
```

### 3. View Internal File Dependencies (Coupling Graph)
```cypher
MATCH (a:File)-[:DEPENDS_ON]->(b:File)
RETURN a.path AS SourceModule, b.path AS ImportedModule
LIMIT 50;
```

### 4. View Function Call Invocations
```cypher
MATCH (s1:Symbol)-[c:CALLS]->(s2:Symbol)
RETURN s1.name AS Caller, s2.name AS Callee, c.line AS CallLine
LIMIT 30;
```

### 5. Inspect Independent Projects Scoped by ID
```cypher
MATCH (p:Project {id: "your_project_id"})-[:CONTAINS_FILE]->(f:File)-[:HAS_FINDING]->(fd:Finding)
RETURN p.name, f.path, fd.rule_id;
```

---

## Troubleshooting Guide

| Issue | Cause | Solution |
|---|---|---|
| **`AuthError: The client is unauthorized due to authentication failure`** | Incorrect username or password in `.env`. | Verify that `NEO4J_PASSWORD` matches the generated password string from Aura. |
| **`ServiceUnavailable: Failed to establish connection`** | Invalid URI or Aura instance is paused. | Ensure URI starts with `neo4j+s://` for Aura, and verify instance status is "Running" in Aura Console. |
| **`Connection Timeout`** | Firewall blocking outgoing port 7687. | Ensure outbound TCP port 7687 is allowed on your network or hotspot. |
| **Status badge shows "Offline (In-Memory)"** | `.env` file contains placeholder values. | Replace placeholder strings (e.g. `your-instance-id`) with your real Aura credentials. |
