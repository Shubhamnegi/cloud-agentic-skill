# Deployment Guide

## Overview

The system is deployed using **Infrastructure as Code** principles with Docker Compose for local/single-server use and Helm Charts for Kubernetes.

---

## 1. Docker Compose Deployment

### Architecture

Docker Compose spins up three containers:

| Container | Image | Role |
|---|---|---|
| `elasticsearch` | `elasticsearch:8.x` | Vector + Document store |
| `python-backend` | Custom (FastAPI) | API Gateway and MCP bridge |
| `dashboard-ui` | Custom (Streamlit) | Management console |

### Key Configuration

- **Persistent Volumes:** Elasticsearch data is mapped to a volume so skill data persists across restarts.
- **Private Network:** A Docker network ensures the Python backend talks to Elasticsearch via `http://elasticsearch:9200` without exposing the DB to the public internet.

### Example `docker-compose.yml`

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: skill-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    networks:
      - skill-network
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: skill-backend
    environment:
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - EMBEDDING_MODEL=all-MiniLM-L6-v2
    ports:
      - "8000:8000"
    depends_on:
      elasticsearch:
        condition: service_healthy
    networks:
      - skill-network

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    container_name: skill-dashboard
    environment:
      - BACKEND_URL=http://backend:8000
    ports:
      - "8501:8501"
    depends_on:
      - backend
    networks:
      - skill-network

volumes:
  es_data:
    driver: local

networks:
  skill-network:
    driver: bridge
```

### Quick Start

```bash
docker-compose up -d
```

Then open `http://localhost:8501` — the Startup Wizard will guide you through the rest.

---

## 2. The Startup Wizard Pattern

Instead of manual `curl` commands to create indices, the Python backend uses **Idempotent Initialization Logic**.

### Boot-up Check

On container start, the Python app checks: "Does the `agent_skills` index exist?"

### Auto-Migration

If the index doesn't exist, the application automatically applies the JSON mappings.

```python
def startup_initialization():
    """Called during FastAPI lifespan startup."""
    # 1. Wait for Elasticsearch to be ready
    wait_for_elasticsearch()
    
    # 2. Ensure index exists (idempotent)
    ensure_index_exists()
    
    # 3. Download embedding model if not cached
    ensure_model_downloaded()
```

### Streamlit Wizard

If the database is empty, the UI redirects the user to a `/setup` page where they can:

1. **Upload** their first Markdown skill file.
2. **Select** which Embedding Model to download (Gemma 2, MiniLM, etc.).
3. **Enter** their MCP API Keys.

---

## 3. MCP Security & Authentication

The Python backend acts as the **Gatekeeper** for all external communication.

### Internal Communication (Trust)

- Python and Elasticsearch connect with simple "Service-to-Service" trust.
- No password required if both are inside a private VPC/Docker network.
- For production: use `.env` credentials or Elasticsearch API keys.

### External Communication (Verify)

To prevent unauthorized Agents from using the MCP tool:

- Implement **API Key Rotation** or **OAuth2** via the Python backend.
- Every MCP request must include a valid `X-API-KEY` header.
- The backend verifies the key against a "Tenant" or "User" table.

### MCP Header Check

```python
from fastapi import Header, HTTPException


async def verify_api_key(x_api_key: str = Header(...)):
    """Validate API key on every MCP tool invocation."""
    if not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

---

## 4. Deployment Architecture Summary

| Component | Technology | Role |
|---|---|---|
| **Container Engine** | Docker / Kubernetes | Standardized environment |
| **Inference Server** | FastChat / Ollama | Host Gemma 2 (separate container) |
| **Search Engine** | Elasticsearch | Vector + Document storage |
| **Gateway / MCP** | FastAPI | Auth, Logic, and MCP protocol |
| **Control Plane** | Streamlit | Wizard for layman users |

---

## 5. The Wizard Dashboard (Streamlit)

The Streamlit dashboard provides a visual management interface:

| Tab | Purpose |
|---|---|
| **Health Check** | Visual indicators showing if Elasticsearch and the Embedding Model are "Live." |
| **Skill Studio** | Drag-and-drop interface to link Parent Skills to Sub-Skills visually. |
| **Security** | Generate and revoke API Keys for the MCP tool. |
| **Logs** | See which instructions the Agent is fetching in real-time (Audit Trail). |

---

## 6. Kubernetes Deployment (Production)

For production workloads, use Helm Charts to deploy on Kubernetes:

```bash
helm install skill-manager ./charts/skill-manager \
  --set elasticsearch.replicas=3 \
  --set backend.replicas=2 \
  --set dashboard.replicas=1
```

Key Kubernetes considerations:

- **Horizontal Pod Autoscaler (HPA):** Scale the backend pods based on request rate.
- **Persistent Volume Claims (PVC):** Ensure Elasticsearch data survives pod restarts.
- **Ingress Controller:** Route traffic to the dashboard and API endpoints securely.
- **Secrets Management:** Store API keys and Elasticsearch credentials as Kubernetes Secrets.

---

> **Next:** See [Access Management](access-management.md) for user permissions, multi-tenancy, and MCP authentication.
