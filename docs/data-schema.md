# Data Schema

## Elasticsearch Index: `agent_skills`

The system uses a single index called `agent_skills`. The key design element is the `sub_skills` field, which acts as a relational pointer to enable the Link-Graph traversal.

---

## Field Mapping

| Field Name | Type | Indexed? | Purpose |
|---|---|---|---|
| `skill_id` | `keyword` | Yes | Unique identifier (e.g., `SQL_SKILL_MIGRATION`). |
| `skill_desc_vector` | `dense_vector` | Yes | Used to **find** the skill via natural language (vector search). |
| `summary` | `text` | No | A short human-readable description of the skill. |
| `is_folder` | `boolean` | Yes | Flag: `true` if it points to other skills; `false` if it has final instructions. |
| `sub_skills` | `keyword[]` | No | Array of `skill_id`s that belong to this skill (pointer list). |
| `instruction` | `text` | No | The actual content/instructions (not indexed to keep search fast). |

---

## Index Mapping Definition

```json
PUT /agent_skills
{
  "mappings": {
    "properties": {
      "skill_id": {
        "type": "keyword"
      },
      "skill_desc_vector": {
        "type": "dense_vector",
        "dims": 384,
        "index": true,
        "similarity": "cosine"
      },
      "summary": {
        "type": "text",
        "index": false
      },
      "is_folder": {
        "type": "boolean"
      },
      "sub_skills": {
        "type": "keyword"
      },
      "instruction": {
        "type": "text",
        "index": false
      }
    }
  }
}
```

> **Note:** The `dims: 384` value corresponds to the `all-MiniLM-L6-v2` embedding model. If you switch to a different model (e.g., Gemma 2 at 768 dims), update this value accordingly.

---

## Design Decisions

### Why `instruction` is Not Indexed

The `instruction` field contains heavy Markdown content — full tutorials, code samples, and step-by-step guides. Indexing this would:

1. **Bloat the inverted index** with terms that are never searched directly.
2. **Slow down searches** by adding unnecessary scoring overhead.
3. **Increase storage** significantly.

Since the Agent only needs this field during the **Targeted Fetch** phase (Step C), it is stored but not indexed.

### Why `sub_skills` Uses `keyword` Type

The `sub_skills` array stores exact `skill_id` references. Using the `keyword` type ensures:

- **Exact match lookups** — no tokenization or analysis.
- **Fast filtering** when checking permission inheritance.
- **Consistent pointer integrity** across documents.

### Why `summary` is Not Indexed

The `summary` field is a short human-readable description returned alongside the `skill_id` during the Discovery Phase. Since semantic search uses the vector field (`skill_desc_vector`), the text summary doesn't need to be indexed for full-text search.

---

## Example Documents

### Parent Skill (Folder)

```json
{
  "skill_id": "SQL_SKILL",
  "skill_desc_vector": [0.012, -0.034, 0.056, ...],
  "summary": "SQL database management and operations skills.",
  "is_folder": true,
  "sub_skills": ["SQL_SKILL_MIGRATION", "SQL_SKILL_OPTIMIZATION"],
  "instruction": "This is a collection of SQL-related skills. Navigate to sub-skills for specific instructions."
}
```

### Leaf Skill (Content)

```json
{
  "skill_id": "SQL_SKILL_MIGRATION",
  "skill_desc_vector": [0.045, -0.012, 0.078, ...],
  "summary": "Database migration including sharding, partitioning, and schema changes.",
  "is_folder": false,
  "sub_skills": [],
  "instruction": "# SQL Migration Guide\n\n## Sharding Strategy\n\n1. Identify your partition key...\n2. Choose horizontal vs vertical sharding...\n..."
}
```

---

> **Next:** See [Implementation Guide](implementation-guide.md) for the Python code that interacts with this schema.
