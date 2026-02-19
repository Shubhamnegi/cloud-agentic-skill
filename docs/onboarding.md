# Onboarding Guide — Real-World Example

This guide walks through a complete end-to-end scenario so you can see exactly how the system works in practice before writing a single line of code.

---

## Scenario

> **You are a backend developer who just joined a team. Your first task is to containerize the Python API, add CI/CD automation, and optimize the slow SQL queries the previous developer left behind. You have no prior knowledge of how the team does any of this.**

Instead of Googling or reading pages of internal wikis, you ask the AI agent — and it finds the right instructions automatically.

---

## Prerequisites

1. Backend running (`docker-compose up -d`)
2. An API key in hand (see [Connecting via MCP](../README.md#connecting-via-mcp))

Set your key once and reuse it throughout:

```bash
export API_KEY="sk-your-key-here"
```

---

## Step 1 — Explore What Skills Exist

Before asking specific questions, get a feel for what the system knows.

```bash
curl http://localhost:8000/skills/tree \
  -H "X-API-Key: $API_KEY" | python3 -m json.tool
```

**Response (trimmed):**
```json
[
  { "skill_id": "DEVOPS_SKILL",  "summary": "DevOps skills — CI/CD, containerization, monitoring, and infrastructure.", "is_folder": true,  "sub_skills": ["DEVOPS_SKILL_DOCKER", "DEVOPS_SKILL_CICD"] },
  { "skill_id": "PYTHON_SKILL",  "summary": "Python programming skills for backend development.",                         "is_folder": true,  "sub_skills": ["PYTHON_SKILL_ASYNC", "PYTHON_SKILL_TESTING"] },
  { "skill_id": "SQL_SKILL",     "summary": "SQL database management, migration, and optimization skills.",              "is_folder": true,  "sub_skills": ["SQL_SKILL_MIGRATION", "SQL_SKILL_OPTIMIZATION"] }
]
```

Three top-level skill groups. Each is a **folder** with child skills inside it.

---

## Step 2 — Discover Skills with Natural Language

Your first task is Docker. Ask in plain English — no need to know any IDs upfront.

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "find_relevant_skill",
    "arguments": { "query": "How do I containerize my Python app using Docker?", "k": 3 }
  }'
```

**Response:**
```json
{
  "results": [
    {
      "skill_id": "DEVOPS_SKILL_DOCKER",
      "summary": "Docker containerization — Dockerfile best practices and multi-stage builds.",
      "score": 0.94,
      "has_children": false
    },
    {
      "skill_id": "DEVOPS_SKILL",
      "summary": "DevOps skills — CI/CD, containerization, monitoring, and infrastructure.",
      "score": 0.81,
      "has_children": true
    },
    {
      "skill_id": "DEVOPS_SKILL_CICD",
      "summary": "CI/CD pipelines with GitHub Actions and GitLab CI.",
      "score": 0.72,
      "has_children": false
    }
  ]
}
```

**What happened:**
- The query was encoded into a vector and matched against all skill descriptions using semantic search (kNN).
- `DEVOPS_SKILL_DOCKER` scored highest (0.94) — it's a leaf skill, so it has the actual instructions.
- `has_children: false` means you can load it directly without further navigation.

---

## Step 3 — Load the Docker Instruction

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "load_instruction",
    "arguments": { "skill_id": "DEVOPS_SKILL_DOCKER" }
  }'
```

**Response:**
```json
{
  "skill_id": "DEVOPS_SKILL_DOCKER",
  "content": "# Docker Best Practices\n\n## 1. Multi-Stage Builds\n```dockerfile\nFROM python:3.12 AS builder\nCOPY requirements.txt .\nRUN pip install --prefix=/install -r requirements.txt\n\nFROM python:3.12-slim\nCOPY --from=builder /install /usr/local\nCOPY app/ app/\nCMD [\"uvicorn\", \"app.main:app\"]\n```\n\n## 2. Layer Caching\n...\n\n## 3. Security\n- Run as non-root: `USER 1000`.\n- Scan images with `trivy` or `grype`."
}
```

The agent now has the complete Markdown instructions for Docker — only **one skill's content** was loaded into context, keeping the token footprint minimal.

---

## Step 4 — Navigate a Folder Skill (Optional Drill-Down)

The second search result (`DEVOPS_SKILL`) was a folder. If you weren't sure which sub-skill you wanted, you'd list its children first:

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "list_sub_skills",
    "arguments": { "skill_id": "DEVOPS_SKILL" }
  }'
```

**Response:**
```json
{
  "skill_id": "DEVOPS_SKILL",
  "summary": "Top-level DevOps skill collection.",
  "children": [
    { "skill_id": "DEVOPS_SKILL_DOCKER", "summary": "Docker containerization — Dockerfile best practices and multi-stage builds.", "has_children": false },
    { "skill_id": "DEVOPS_SKILL_CICD",   "summary": "CI/CD pipelines with GitHub Actions and GitLab CI.",                       "has_children": false }
  ]
}
```

Now the agent can reason: *"The user asked about Docker, so pick `DEVOPS_SKILL_DOCKER`"* — and then call `load_instruction`.

---

## Step 5 — Tackle the Next Task (SQL Optimization)

Same pattern — ask in plain English:

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "find_relevant_skill",
    "arguments": { "query": "Our SELECT queries are slow, how do I use indexes to speed them up?", "k": 2 }
  }'
```

**Response:**
```json
{
  "results": [
    { "skill_id": "SQL_SKILL_OPTIMIZATION", "summary": "SQL query tuning, indexing strategies, and performance optimization.", "score": 0.91, "has_children": false },
    { "skill_id": "SQL_SKILL",              "summary": "SQL database management, migration, and optimization skills.",         "score": 0.78, "has_children": true  }
  ]
}
```

Load it directly:

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "load_instruction",
    "arguments": { "skill_id": "SQL_SKILL_OPTIMIZATION" }
  }'
```

---

## Full Automated Agentic Loop (Python)

The script below automates the entire workflow — it takes a natural language task, finds the best skill, navigates folders if needed, and returns the final instruction.

```python
"""
onboarding_example.py — Demonstrates the full agentic skill-lookup loop.
Run: python onboarding_example.py
"""
import requests

BASE    = "http://localhost:8000"
API_KEY = "sk-your-key-here"   # replace with your key
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def find_skill(query: str, k: int = 3) -> list[dict]:
    r = requests.post(f"{BASE}/mcp/tools/call", headers=HEADERS, json={
        "name": "find_relevant_skill",
        "arguments": {"query": query, "k": k}
    })
    r.raise_for_status()
    return r.json()["results"]


def list_children(skill_id: str) -> list[dict]:
    r = requests.post(f"{BASE}/mcp/tools/call", headers=HEADERS, json={
        "name": "list_sub_skills",
        "arguments": {"skill_id": skill_id}
    })
    r.raise_for_status()
    return r.json()["children"]


def load_instruction(skill_id: str) -> str:
    r = requests.post(f"{BASE}/mcp/tools/call", headers=HEADERS, json={
        "name": "load_instruction",
        "arguments": {"skill_id": skill_id}
    })
    r.raise_for_status()
    return r.json()["content"]


def solve_task(query: str) -> str:
    """Given a natural language task, return the relevant skill instruction."""
    print(f"\n[1] Searching for: '{query}'")
    results = find_skill(query, k=3)

    for result in results:
        skill_id    = result["skill_id"]
        has_children = result["has_children"]
        score        = result["score"]

        print(f"    → {skill_id} (score={score:.2f}, folder={has_children})")

        if not has_children:
            # Leaf skill — load it directly
            print(f"[2] Loading instruction for '{skill_id}' ...")
            return load_instruction(skill_id)

        # Folder skill — drill one level deeper
        print(f"[2] '{skill_id}' is a folder, listing children ...")
        children = list_children(skill_id)
        for child in children:
            print(f"    → {child['skill_id']}: {child['summary']}")

        # Pick the first child (a real agent would reason here)
        best = children[0]["skill_id"]
        print(f"[3] Loading best child '{best}' ...")
        return load_instruction(best)

    return "No matching skill found."


# ── Run three real-world tasks ──────────────────────────────────────────────

tasks = [
    "How do I containerize my Python app using Docker?",
    "Our SELECT queries are slow, how do I use indexes to speed them up?",
    "How do I set up a GitHub Actions CI pipeline?",
]

for task in tasks:
    instruction = solve_task(task)
    print("\n" + "="*60)
    print(instruction[:400] + "...")   # truncate for readability
    print("="*60)
```

**Expected Output:**
```
[1] Searching for: 'How do I containerize my Python app using Docker?'
    → DEVOPS_SKILL_DOCKER (score=0.94, folder=False)
[2] Loading instruction for 'DEVOPS_SKILL_DOCKER' ...
============================================================
# Docker Best Practices
## 1. Multi-Stage Builds ...
============================================================

[1] Searching for: 'Our SELECT queries are slow, how do I use indexes to speed them up?'
    → SQL_SKILL_OPTIMIZATION (score=0.91, folder=False)
[2] Loading instruction for 'SQL_SKILL_OPTIMIZATION' ...
============================================================
# SQL Optimization Guide
## 1. Indexing ...
============================================================

[1] Searching for: 'How do I set up a GitHub Actions CI pipeline?'
    → DEVOPS_SKILL_CICD (score=0.93, folder=False)
[2] Loading instruction for 'DEVOPS_SKILL_CICD' ...
============================================================
# CI/CD Pipeline Guide ...
============================================================
```

---

## What You Just Learned

| Concept | What It Means in Practice |
|---|---|
| **Semantic search** | You never need to know a skill ID — a natural language sentence is enough |
| **Folder vs Leaf** | Folders group related skills; leaves hold the actual instructions |
| **Progressive loading** | Only the relevant skill's content enters the agent's context — no bloat |
| **O(1) fetch** | `load_instruction` is a direct document GET — fast regardless of total skill count |
| **MCP compatibility** | Any MCP-compatible agent (Claude, custom LLM loop) can call these same tools |

---

## Skill Tree Reference

```
DEVOPS_SKILL  (folder)
├── DEVOPS_SKILL_DOCKER     Docker multi-stage builds, layer caching, security
└── DEVOPS_SKILL_CICD       GitHub Actions, GitLab CI pipelines

PYTHON_SKILL  (folder)
├── PYTHON_SKILL_ASYNC      asyncio, coroutines, TaskGroup
└── PYTHON_SKILL_TESTING    pytest, fixtures, mocking, coverage

SQL_SKILL  (folder)
├── SQL_SKILL_MIGRATION     Sharding, partitioning, schema migrations
└── SQL_SKILL_OPTIMIZATION  Indexing, query tuning, connection pooling
```

---

## Next Steps

- **Add your own skills** — Use the Dashboard (`http://localhost:8501`) or `POST /skills/` to add company-specific skills.
- **Scope API keys** — Restrict an agent key to only `SQL_SKILL` or `DEVOPS_SKILL` via scopes.
- **Integrate with Claude** — See the [Claude Desktop config](../README.md#claude-desktop-integration) section.
- **Read the architecture** — [docs/architecture.md](architecture.md) explains how the vector search and link-graph work under the hood.
