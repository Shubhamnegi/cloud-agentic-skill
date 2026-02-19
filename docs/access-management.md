# Access Management

## Overview

The system implements a **Hierarchical Access Architecture** that combines user-level permissions with skill-tree inheritance, ensuring users only access the skills they are authorized to use.

---

## 1. Hierarchical Access Architecture

Access control is managed by storing an `allowed_skills` list in each user's profile and performing recursive lookups in the Python backend.

### Key Concepts

| Concept | Description |
|---|---|
| **User Document** | Stores top-level `skill_id`s the user is permitted to use. |
| **Skill Document** | Contains the `sub_skills` array (part of the existing Link-Graph design). |
| **Inheritance** | Access to a parent skill automatically grants access to all its sub-skills. |

### Auth Flow

```
1. MCP Request     → Client sends API key or token
2. Identity Map    → Python resolves to user_id + allowed_skills
3. Inheritance     → When fetching a sub-skill, Python checks if it's
                     a descendant of any allowed_skills
4. Grant/Deny     → Return data or 403 Forbidden
```

### Example: Permission Check

```python
def is_skill_accessible(skill_id: str, allowed_skills: list[str], repository) -> bool:
    """
    Check if a skill_id is accessible given the user's allowed top-level skills.
    Recursively walks up or down the tree to verify inheritance.
    """
    # Direct match
    if skill_id in allowed_skills:
        return True
    
    # Check if skill_id is a descendant of any allowed skill
    for parent_id in allowed_skills:
        if is_descendant(skill_id, parent_id, repository):
            return True
    
    return False


def is_descendant(target_id: str, parent_id: str, repository) -> bool:
    """
    Recursively check if target_id is a descendant of parent_id
    in the skill tree.
    """
    parent = repository.get_by_id(parent_id, fields=["sub_skills"])
    sub_skills = parent.get('sub_skills', [])
    
    if target_id in sub_skills:
        return True
    
    for child_id in sub_skills:
        if is_descendant(target_id, child_id, repository):
            return True
    
    return False
```

---

## 2. Multi-Tenant Security (Elasticsearch DLS)

For an additional layer of security, enforce access **directly at the database level** using Elasticsearch **Document Level Security (DLS)**.

### How It Works

- Configure per-user roles in Elasticsearch that include a DLS query.
- Even if the Python code has a bug, Elasticsearch will refuse to return unauthorized documents.

### DLS Role Configuration

```json
POST /_security/role/user_sql_role
{
  "indices": [
    {
      "names": ["agent_skills"],
      "privileges": ["read"],
      "query": {
        "terms": {
          "skill_id": ["SQL_SKILL", "SQL_SKILL_MIGRATION", "SQL_SKILL_OPTIMIZATION"]
        }
      }
    }
  ]
}
```

### Benefits

- **Defense in Depth:** Database-level enforcement as a safety net.
- **Private Views:** Each user sees only their permitted slice of the index.
- **Audit Compliance:** Elasticsearch logs all access attempts, simplifying compliance audits.

---

## 3. MCP Consumer Authentication

Following MCP Security Best Practices, use **OAuth 2.1 with PKCE** for remote clients.

### Token-Based Auth

| Component | Description |
|---|---|
| **The Token** | When a user authenticates via the Dashboard Wizard, they receive a **Scoped JWT**. |
| **The Scope** | The JWT contains a `scopes` claim (e.g., `skill:SQL_Skill`). |
| **Validation** | The Python backend validates this token on every request. If the Agent asks for a "Migration" instruction, the backend verifies the token carries the parent `SQL_Skill` scope. |

### JWT Validation Example

```python
import jwt
from fastapi import Header, HTTPException


SECRET_KEY = "your-secret-key"  # In production, use env variable


def validate_mcp_token(authorization: str = Header(...)) -> dict:
    """
    Validate the JWT token from MCP requests.
    Returns the decoded token payload with user scopes.
    """
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def check_skill_scope(payload: dict, skill_id: str) -> bool:
    """
    Verify that the token's scopes grant access to the requested skill.
    """
    scopes = payload.get('scopes', [])
    # Check if the requested skill (or its parent) is in the token scopes
    for scope in scopes:
        if scope.startswith("skill:"):
            allowed_skill = scope.replace("skill:", "")
            if skill_id == allowed_skill or is_descendant(skill_id, allowed_skill):
                return True
    return False
```

---

## 4. Dashboard: User Management Tab

The Streamlit Dashboard includes a **User Management** interface to make permission management accessible to non-technical users.

### Features

| Feature | Description |
|---|---|
| **Visual Mapping** | A simple checklist of "Main Skills" for each user. |
| **Auto-Propagation** | A "Preview Permissions" button that shows the full tree of sub-skills the user will inherit based on their selection. |
| **Bulk Assignment** | Assign a role template (e.g., "SQL Admin," "Read-Only Viewer") to multiple users at once. |
| **Audit Log** | View a history of permission changes with timestamps and admin identity. |

### Streamlit UI Example

```python
import streamlit as st


def render_user_permissions(user_id: str, all_skills: list[dict]):
    """Render the permission management UI for a user."""
    st.subheader(f"Permissions for: {user_id}")
    
    # Get current allowed skills
    user = get_user(user_id)
    current_skills = user.get('allowed_skills', [])
    
    # Display top-level skills as checkboxes
    selected = []
    for skill in all_skills:
        if skill['is_folder']:
            checked = skill['skill_id'] in current_skills
            if st.checkbox(skill['summary'], value=checked, key=skill['skill_id']):
                selected.append(skill['skill_id'])
    
    # Preview inherited permissions
    if st.button("Preview Permissions"):
        inherited = get_all_descendants(selected)
        st.info(f"User will have access to {len(inherited)} total skills")
        for s in inherited:
            st.write(f"  - {s}")
    
    # Save
    if st.button("Save Permissions"):
        update_user_permissions(user_id, selected)
        st.success("Permissions updated!")
```

---

## 5. Security Summary

| Layer | Mechanism | Purpose |
|---|---|---|
| **Transport** | HTTPS / TLS | Encrypt data in transit |
| **Authentication** | OAuth 2.1 + JWT | Verify client identity |
| **Authorization** | Scoped tokens + inheritance check | Control skill access |
| **Database** | Elasticsearch DLS | Defense-in-depth enforcement |
| **Audit** | Request logging | Compliance and debugging |

---

> **Back to:** [Architecture](architecture.md) | [Deployment Guide](deployment-guide.md)
