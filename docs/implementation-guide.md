# Implementation Guide

## Python-Elasticsearch Architecture

The system follows a **"Search-then-Traverse"** pattern:

1. **Client-Side Inference:** Use `sentence-transformers` to convert text into vectors locally before sending them to Elasticsearch.
2. **Vector Retrieval:** Elasticsearch uses kNN search to find the initial "Entry Point" skill based on the query vector.
3. **Recursive Fetching:** The Python agent inspects the `sub_skills` pointers in the retrieved document to decide if it needs to "drill down" for more detail.

---

## Prerequisites

Install the required Python libraries:

```bash
uv sync
```

---

## Core Implementation

### A. Embedding & Traversal Logic

This script handles embedding of queries and progressive loading of skill data:

```python
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

# 1. Initialize Model and Client
# all-MiniLM-L6-v2 is fast and efficient for skill matching
model = SentenceTransformer('all-MiniLM-L6-v2')
es = Elasticsearch("http://localhost:9200")


def get_skill_by_intent(user_query: str) -> dict:
    """
    Discovery Phase: Find the top-level matching skill via vector search.
    Returns only skill_id, summary, and sub_skills — no heavy instructions.
    """
    query_vector = model.encode(user_query).tolist()
    
    response = es.search(
        index="agent_skills",
        knn={
            "field": "skill_desc_vector",
            "query_vector": query_vector,
            "k": 1,
            "num_candidates": 10
        },
        _source=["skill_id", "summary", "sub_skills"]  # Progressive: no instructions yet
    )
    return response['hits']['hits'][0]['_source']


def fetch_sub_skill(skill_id: str, include_instruction: bool = True) -> dict:
    """
    Targeted Fetch: Get specific sub-skill details only when requested.
    """
    fields = ["skill_id", "summary", "sub_skills"]
    if include_instruction:
        fields.append("instruction")
        
    doc = es.get(index="agent_skills", id=skill_id, _source=fields)
    return doc['_source']
```

### B. Agentic Logic Flow

```python
# --- Agentic Logic Flow ---

# 1. User asks a question
discovery = get_skill_by_intent("How do I handle SQL sharding?")
print(f"Found Entry Skill: {discovery['skill_id']}")

# 2. Agent reasons about which sub-skill to fetch
if "SQL_SKILL_MIGRATION" in discovery.get('sub_skills', []):
    migration_details = fetch_sub_skill("SQL_SKILL_MIGRATION", include_instruction=True)
    print(f"Loaded Instructions: {migration_details['instruction'][:50]}...")
```

### C. Index Initialization (Idempotent)

```python
def ensure_index_exists():
    """
    Create the agent_skills index with the correct mapping if it doesn't exist.
    Safe to call on every startup.
    """
    if not es.indices.exists(index="agent_skills"):
        es.indices.create(
            index="agent_skills",
            body={
                "mappings": {
                    "properties": {
                        "skill_id": {"type": "keyword"},
                        "skill_desc_vector": {
                            "type": "dense_vector",
                            "dims": 384,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "summary": {"type": "text", "index": False},
                        "is_folder": {"type": "boolean"},
                        "sub_skills": {"type": "keyword"},
                        "instruction": {"type": "text", "index": False}
                    }
                }
            }
        )
        print("Index 'agent_skills' created.")
    else:
        print("Index 'agent_skills' already exists.")
```

### D. Bulk Ingestion

```python
from elasticsearch.helpers import bulk


def ingest_skills(skills: list[dict]):
    """
    Bulk-ingest skill documents into Elasticsearch.
    Each skill dict should contain: skill_id, summary, is_folder, sub_skills, instruction.
    The skill_desc_vector is generated automatically from the summary.
    """
    actions = []
    for skill in skills:
        vector = model.encode(skill['summary']).tolist()
        actions.append({
            "_index": "agent_skills",
            "_id": skill['skill_id'],
            "_source": {
                "skill_id": skill['skill_id'],
                "skill_desc_vector": vector,
                "summary": skill['summary'],
                "is_folder": skill.get('is_folder', False),
                "sub_skills": skill.get('sub_skills', []),
                "instruction": skill.get('instruction', '')
            }
        })
    
    success, errors = bulk(es, actions)
    print(f"Ingested {success} skills. Errors: {errors}")
```

---

## Key Architectural Benefits

| Benefit | Description |
|---|---|
| **Minimal Context Bloat** | The initial search only returns IDs and summaries. The high-token `instruction` field is loaded only after the Agent locks onto the correct sub-skill. |
| **No Heavy Joins** | Using `skill_id` as the document ID enables ultra-fast point lookups instead of expensive nested searches. |
| **Model Flexibility** | Swap `all-MiniLM-L6-v2` for a more powerful model (e.g., Gemma 2) without changing the Elasticsearch structure — just update `dims`. |

---

## MCP Tool Integration

The MCP layer exposes two primary tools to the Agent:

### `find_relevant_skill(query: str) -> list[dict]`

Runs the vector search and returns a list of matching Skill IDs with summaries.

### `load_instruction(skill_id: str) -> dict`

Fetches the non-indexed `instruction` field for a specific skill by its ID.

**Progressive Context** ensures the Agent only "sees" what it explicitly asks for through the MCP interface — preventing the full instruction corpus from being loaded into memory at once.

---

> **Next:** See [Design Patterns](design-patterns.md) for the architectural patterns that make this system database- and model-agnostic.
