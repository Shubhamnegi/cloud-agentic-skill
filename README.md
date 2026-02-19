# Cloud Agentic Skill
**Alternate of [mcpdoc](https://github.com/langchain-ai/mcpdoc)  | Better at handling context size for agent | Inspired from agent skill | All Skills at one place (opensearch)**

A **Recursive Agentic Skill Management** system built on Elasticsearch using a **Link-Graph Architecture**. Every skill is a node that can be a leaf (with content) or a branch (pointing to other skills), enabling progressive context loading for AI agents.

---

## Overview

This system provides an intelligent skill management platform where AI agents can discover, navigate, and load skill instructions using semantic search and recursive traversal — without context bloat.

### Key Features

- **Semantic Skill Discovery** — Vector search (kNN) over skill descriptions to find relevant capabilities.
- **Progressive Context Loading** — Agent fetches only summaries initially, drilling into full instructions only when needed.
- **Link-Graph Traversal** — Skills reference sub-skills via pointers, enabling tree-like navigation with O(1) lookups.
- **Database & Model Agnostic** — Clean architecture with Strategy, Repository, and Adapter patterns for easy swapping.
- **MCP Integration** — Exposes skills as Model Context Protocol tools for any compatible Agent (Claude, GPT-4, custom LLMs).
- **Multi-Tenant Access Control** — Hierarchical permissions with JWT scoping and Elasticsearch Document Level Security.
- **Streamlit Dashboard** — Visual management console with a Startup Wizard for zero-config onboarding.

---

## Architecture

```mermaid
graph TD
    User([User Query]) -->|Natural Language| Agent[AI Agent]
    
    subgraph Elasticsearch
        Discovery[Discovery Index]
        subgraph Skill_Documents
            S1[SQL_Skill <br/> Pointers: Migration, Opti]
            S2[SQL_Migration <br/> Content: Sharding/Partitioning]
        end
    end

    Agent -->|1. Vector Search| Discovery
    Discovery -.->|Returns Skill_ID| Agent
    Agent -->|2. Get by ID| S1
    S1 -.->|Returns Sub-Skill List| Agent
    Agent -->|3. Decides & Fetches| S2
    S2 -.->|Returns Detailed Markdown| Agent
    Agent -->|4. Final Execution| User
```

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Inference** | Sentence-Transformers (MiniLM / Gemma 2) | Text-to-vector embedding |
| **Database** | Elasticsearch | Vector + Document store |
| **API Layer** | FastAPI | REST API and MCP bridge |
| **UI Layer** | Streamlit | Management dashboard |
| **Agent Bridge** | MCP (Model Context Protocol) | LLM-to-skill connectivity |
| **Containerization** | Docker / Kubernetes | Deployment and orchestration |

---

## Quick Start

### Option A: Docker Compose (recommended)

```bash
git clone <repo-url>
cd cloud-agentic-skill
cp .env.example .env          # adjust settings if needed

docker-compose up -d

# Open the dashboard
open http://localhost:8501
```

### Option B: Local development

```bash
# 1. Start Elasticsearch (Docker or native)
docker run -d --name es -p 9200:9200 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:8.12.0

# 2. Install Python dependencies (uv creates a .venv automatically)
uv sync

# 3. Seed sample data
uv run python -m scripts.seed_data

# 4. Start the FastAPI backend
uv run uvicorn app.main:app --reload

# 5. (in another terminal) Start the Streamlit dashboard
uv run streamlit run dashboard/app.py
```

### Option C: Run tests (no Elasticsearch needed)

```bash
uv sync --dev
uv run pytest tests/ -v
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | System health check |
| `GET` | `/skills/` | — | List all skills |
| `GET` | `/skills/search?q=…` | — | Semantic skill search |
| `GET` | `/skills/{id}` | — | Get skill by ID |
| `GET` | `/skills/{id}/children` | — | Get sub-skills |
| `GET` | `/skills/tree` | — | Full skill tree |
| `POST` | `/skills/` | Admin | Create/update skill |
| `DELETE` | `/skills/{id}` | Admin | Delete skill |
| `POST` | `/auth/login` | — | Get JWT token |
| `POST` | `/auth/register` | Admin | Create user |
| `GET` | `/auth/users` | Admin | List users |
| `POST` | `/api-keys/` | Admin | Generate API key |
| `POST` | `/mcp` | API Key | **Standard MCP — JSON-RPC 2.0** (use with mcp-remote / Claude Desktop) |
| `GET` | `/mcp/tools` | API Key | _(Legacy)_ List MCP tools |
| `POST` | `/mcp/tools/call` | API Key | _(Legacy)_ Invoke MCP tool |

---

## Connecting via MCP

This server implements the **Model Context Protocol (MCP) over JSON-RPC 2.0**.
All MCP clients (`mcp-remote`, Claude Desktop, VS Code MCP extension, MCP Inspector)
must talk to a single endpoint:

```
POST http://localhost:8000/mcp
```

All requests require an `X-API-Key` header.

---

### Step 1 — Start the backend

```bash
docker-compose up -d        # or: uv run uvicorn app.main:app --reload
```

### Step 2 — Generate an API Key

**Via Dashboard** → `http://localhost:8501` → **Security** tab → **Generate Key**

**Or via API:**

```bash
# 1. Login to get a JWT token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# 2. Create an API key (replace <jwt-token> below)
curl -X POST http://localhost:8000/api-keys/ \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "scopes": ["SQL_SKILL"]}'
```

---

### Step 3 — Test with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the easiest way to
verify your server before wiring up a real agent.

```bash
npx @modelcontextprotocol/inspector
```

Then enter `http://localhost:8000/mcp` as the server URL and add
`X-API-Key: <your-api-key>` as a custom header.

![MCP Inspector demo](docs/mcp-inspector-demo.png)

---

### Step 4 — Use the MCP Tools via JSON-RPC

All three calls go to **`POST /mcp`** with a JSON-RPC 2.0 body.

#### Capability handshake (required by most clients)
```bash
curl -X POST http://localhost:8000/mcp \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
```

#### List available tools
```bash
curl -X POST http://localhost:8000/mcp \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
```

#### `find_relevant_skill` — Semantic search
```bash
curl -X POST http://localhost:8000/mcp \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {
      "name": "find_relevant_skill",
      "arguments": {"query": "How do I shard my database?", "k": 3}
    }
  }'
```

#### `list_sub_skills` — Navigate a skill branch
```bash
curl -X POST http://localhost:8000/mcp \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 4, "method": "tools/call",
    "params": {"name": "list_sub_skills", "arguments": {"skill_id": "SQL_SKILL"}}
  }'
```

#### `load_instruction` — Fetch full Markdown content
```bash
curl -X POST http://localhost:8000/mcp \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 5, "method": "tools/call",
    "params": {"name": "load_instruction", "arguments": {"skill_id": "SQL_SKILL_MIGRATION"}}
  }'
```

---

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cloud-agentic-skill": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "http://localhost:8000/mcp",
        "--header", "X-API-Key: <your-api-key>"
      ]
    }
  }
}
```

> **Note:** `mcp-remote` does **not** add auth headers automatically — the `--header` flag is required.

---

### Python Agent Integration

```python
import requests

BASE    = "http://localhost:8000/mcp"
HEADERS = {"X-API-Key": "<your-api-key>", "Content-Type": "application/json"}
_id     = 0

def rpc(method: str, params: dict = {}) -> dict:
    global _id
    _id += 1
    r = requests.post(BASE, headers=HEADERS, json={
        "jsonrpc": "2.0", "id": _id, "method": method, "params": params
    })
    r.raise_for_status()
    return r.json()["result"]

# 1. Handshake
rpc("initialize")

# 2. Discover relevant skills
result = rpc("tools/call", {
    "name": "find_relevant_skill",
    "arguments": {"query": "optimize SQL queries", "k": 3}
})
print(result["content"][0]["text"])

# 3. Load a specific skill instruction
result = rpc("tools/call", {
    "name": "load_instruction",
    "arguments": {"skill_id": "SQL_SKILL_OPTIMIZATION"}
})
print(result["content"][0]["text"])
```

---

### Endpoint Reference

| Endpoint | Protocol | Use when |
|---|---|---|
| `POST /mcp` | **JSON-RPC 2.0 (MCP spec)** | mcp-remote, Claude Desktop, MCP Inspector, any MCP client |
| `GET /mcp/tools` | REST _(legacy)_ | Direct HTTP testing / older integrations |
| `POST /mcp/tools/call` | REST _(legacy)_ | Direct HTTP testing / older integrations |

---

### Agentic Flow

```
Agent Query
    │
    ▼  POST /mcp  {method: "tools/call", params: {name: "find_relevant_skill", …}}
find_relevant_skill  ──►  [skill summaries + has_children flag]
    │
    ├─ has_children=true  ──►  list_sub_skills  ──►  [child skill list]
    │                                                        │
    └─ has_children=false ◄──────────────────────────────────┘
    │
    ▼  POST /mcp  {method: "tools/call", params: {name: "load_instruction", …}}
load_instruction  ──►  Full Markdown content  ──►  Agent executes task
```

---

## Documentation

Detailed documentation is available in the [`docs/`](docs/) folder:

| Document | Description |
|---|---|
| [Onboarding Guide](docs/onboarding.md) | **Start here** — real-world walkthrough with curl examples and a full Python agent loop |
| [Architecture](docs/architecture.md) | System layers, logic flow, and component stack |
| [Data Schema](docs/data-schema.md) | Elasticsearch index mapping and field definitions |
| [Implementation Guide](docs/implementation-guide.md) | Python code for embedding, search, and traversal |
| [Design Patterns](docs/design-patterns.md) | Strategy, Repository, Adapter, and DI patterns |
| [Deployment Guide](docs/deployment-guide.md) | Docker Compose, Kubernetes, and the Startup Wizard |
| [Access Management](docs/access-management.md) | Permissions, multi-tenancy, and MCP authentication |

---

## How It Works

1. **Discovery** — The Agent sends a natural language query. Python encodes it into a vector and performs a kNN search on Elasticsearch to find matching skill IDs and summaries.

2. **Navigation** — The Agent inspects the returned skill's `sub_skills` pointers and reasons about which sub-skill is most relevant to the user's intent.

3. **Targeted Fetch** — The Agent fetches only the specific sub-skill's detailed instructions by ID — an O(1) point lookup — keeping context minimal.

4. **Execution** — The Agent uses the loaded Markdown instructions to perform the task or guide the user.

---

## Project Structure

```
cloud-agentic-skill/
├── README.md
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.dashboard
├── .env.example
├── .gitignore
│
├── app/                          # Python package
│   ├── main.py                   # FastAPI app entry point
│   ├── core/
│   │   ├── config.py             # Pydantic settings
│   │   ├── models.py             # Data models (Skill, User, Token…)
│   │   └── interfaces.py         # Abstract base classes (Strategy/Repository)
│   ├── providers/
│   │   └── embedding.py          # SentenceTransformer & OpenAI providers
│   ├── repositories/
│   │   └── elasticsearch.py      # ES-backed Skill, User, APIKey repos
│   ├── services/
│   │   ├── orchestrator.py       # Skill search-then-traverse logic
│   │   ├── auth.py               # JWT auth + permission inheritance
│   │   └── api_keys.py           # API key CRUD + validation
│   ├── mcp/
│   │   ├── adapter.py            # MCP response formatter
│   │   └── router.py             # MCP tool dispatcher
│   └── api/
│       ├── deps.py               # Dependency injection & auth guards
│       └── routes/
│           ├── skills.py         # /skills endpoints
│           ├── auth.py           # /auth endpoints
│           ├── mcp.py            # /mcp endpoints
│           └── api_keys.py       # /api-keys endpoints
│
├── dashboard/
│   └── app.py                    # Streamlit multi-tab dashboard
│
├── scripts/
│   └── seed_data.py              # Sample skill data loader
│
├── tests/
│   ├── fakes.py                  # In-memory test doubles
│   ├── test_orchestrator.py      # Orchestrator unit tests
│   ├── test_auth.py              # Auth service unit tests
│   ├── test_mcp.py               # MCP adapter/router tests
│   └── test_api.py               # FastAPI integration tests
│
└── docs/
    ├── architecture.md
    ├── data-schema.md
    ├── implementation-guide.md
    ├── design-patterns.md
    ├── deployment-guide.md
    └── access-management.md
```

---

## Design Patterns

The codebase uses four key patterns for maintainability:

| Pattern | File | Purpose |
|---|---|---|
| **Strategy** | `app/core/interfaces.py` → `app/providers/embedding.py` | Swap embedding models without touching business logic |
| **Repository** | `app/core/interfaces.py` → `app/repositories/elasticsearch.py` | Swap database backends (ES → Pinecone, etc.) |
| **Adapter** | `app/mcp/adapter.py` | Translate internal data to MCP/LLM formats |
| **Dependency Injection** | `app/api/deps.py` | Wire everything at startup; override in tests |

---

## License

See [LICENSE](LICENSE) for details.
