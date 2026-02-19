"""
Streamlit Dashboard — main entry point.

Tabs:
  1. Health Check
  2. Skill Studio (tree + CRUD)
  3. Security (API keys)
  4. Users & Permissions
  5. Logs / Audit Trail
"""
from __future__ import annotations

import json
from datetime import datetime

import requests
import streamlit as st

# ─── Configuration ─────────────────────────────────────────────

BACKEND = st.sidebar.text_input("Backend URL", value="http://localhost:8000")

# ─── Session helpers ───────────────────────────────────────────


def _headers() -> dict:
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _login(username: str, password: str) -> bool:
    try:
        r = requests.post(f"{BACKEND}/auth/login", json={"username": username, "password": password}, timeout=5)
        if r.ok:
            st.session_state["token"] = r.json()["access_token"]
            st.session_state["username"] = username
            return True
    except requests.ConnectionError:
        st.error("Cannot reach backend.")
    return False


# ─── Sidebar: Auth ─────────────────────────────────────────────

if "token" not in st.session_state:
    st.sidebar.subheader("Login")
    _u = st.sidebar.text_input("Username", value="admin")
    _p = st.sidebar.text_input("Password", type="password", value="admin")
    if st.sidebar.button("Log in"):
        if _login(_u, _p):
            st.rerun()
        else:
            st.sidebar.error("Login failed.")
    st.stop()
else:
    st.sidebar.success(f"Logged in as **{st.session_state['username']}**")
    if st.sidebar.button("Log out"):
        del st.session_state["token"]
        del st.session_state["username"]
        st.rerun()

# ─── Tabs ──────────────────────────────────────────────────────

tab_health, tab_studio, tab_security, tab_users, tab_logs = st.tabs(
    ["🩺 Health Check", "🛠️ Skill Studio", "🔑 Security", "👤 Users", "📋 Logs"]
)

# ──────────────────────────────────────────────────────────────
# TAB 1 — Health Check
# ──────────────────────────────────────────────────────────────

with tab_health:
    st.header("System Health")
    try:
        r = requests.get(f"{BACKEND}/health", timeout=5)
        if r.ok:
            data = r.json()
            col1, col2, col3 = st.columns(3)
            with col1:
                es_status = data.get("elasticsearch", "unknown")
                st.metric("Elasticsearch", es_status)
                if es_status == "ok":
                    st.success("Connected")
                else:
                    st.error("Unreachable")
            with col2:
                st.metric("Embedding Model", data.get("embedding_model", "unknown"))
                st.success("Loaded")
            with col3:
                st.metric("Embedding Dims", data.get("embedding_dims", "?"))
        else:
            st.error(f"Backend returned {r.status_code}")
    except requests.ConnectionError:
        st.error("Cannot reach the backend. Is it running?")

# ──────────────────────────────────────────────────────────────
# TAB 2 — Skill Studio
# ──────────────────────────────────────────────────────────────

with tab_studio:
    st.header("Skill Studio")

    # Search
    st.subheader("🔍 Semantic Search")
    query = st.text_input("Search skills by intent")
    if query:
        r = requests.get(f"{BACKEND}/skills/search", params={"q": query, "k": 5}, headers=_headers(), timeout=10)
        if r.ok:
            results = r.json()
            for s in results:
                with st.expander(f"**{s['skill_id']}** — {s['summary']}  (score: {s.get('score', 0):.3f})"):
                    if s.get("sub_skills"):
                        st.write("Sub-skills:", ", ".join(s["sub_skills"]))
                    if st.button(f"Load full instruction for {s['skill_id']}", key=f"load_{s['skill_id']}"):
                        det = requests.get(f"{BACKEND}/skills/{s['skill_id']}", headers=_headers(), timeout=10)
                        if det.ok:
                            st.markdown(det.json().get("instruction", "_no instruction_"))
        else:
            st.warning(f"Search failed: {r.text}")

    st.divider()

    # Skill tree
    st.subheader("🌳 Skill Tree")
    if st.button("Refresh tree"):
        st.session_state["_tree_refresh"] = True

    try:
        tree_resp = requests.get(f"{BACKEND}/skills/tree", headers=_headers(), timeout=10)
        if tree_resp.ok:
            tree_data = tree_resp.json()

            def _render_tree(nodes: list, indent: int = 0):
                for n in nodes:
                    prefix = "&nbsp;" * indent * 4
                    icon = "📂" if n.get("is_folder") else "📄"
                    st.markdown(f"{prefix}{icon} **{n['skill_id']}** — {n['summary']}", unsafe_allow_html=True)
                    if n.get("children"):
                        _render_tree(n["children"], indent + 1)

            if tree_data:
                _render_tree(tree_data)
            else:
                st.info("No skills yet. Create one below!")
    except requests.ConnectionError:
        st.error("Backend unreachable.")

    st.divider()

    # Create / update skill
    st.subheader("➕ Create or Update Skill")
    with st.form("skill_form"):
        sid = st.text_input("Skill ID", placeholder="SQL_SKILL_MIGRATION")
        summary = st.text_input("Summary", placeholder="Database migration including sharding, partitioning…")
        is_folder = st.checkbox("Is Folder (branch node)?")
        sub_skills_raw = st.text_input("Sub-skill IDs (comma-separated)", placeholder="SQL_SKILL_MIGRATION, SQL_SKILL_OPT")
        instruction = st.text_area("Instruction (Markdown)", height=200)
        submitted = st.form_submit_button("Save Skill")

    if submitted and sid:
        sub_list = [s.strip() for s in sub_skills_raw.split(",") if s.strip()] if sub_skills_raw else []
        payload = {
            "skill_id": sid,
            "summary": summary,
            "is_folder": is_folder,
            "sub_skills": sub_list,
            "instruction": instruction,
        }
        r = requests.post(f"{BACKEND}/skills/", json=payload, headers=_headers(), timeout=10)
        if r.status_code in (200, 201):
            st.success(f"Skill **{sid}** saved!")
        else:
            st.error(f"Error {r.status_code}: {r.text}")

    st.divider()

    # Delete
    st.subheader("🗑️ Delete Skill")
    del_id = st.text_input("Skill ID to delete", key="del_skill")
    if st.button("Delete") and del_id:
        r = requests.delete(f"{BACKEND}/skills/{del_id}", headers=_headers(), timeout=10)
        if r.status_code == 204:
            st.success(f"Deleted **{del_id}**")
        else:
            st.error(f"Error {r.status_code}: {r.text}")

# ──────────────────────────────────────────────────────────────
# TAB 3 — Security (API Keys)
# ──────────────────────────────────────────────────────────────

with tab_security:
    st.header("API Key Management")

    # Create
    with st.form("key_form"):
        key_name = st.text_input("Key name", placeholder="production-agent")
        key_scopes = st.text_input("Scopes (comma-separated skill IDs)", placeholder="SQL_SKILL, PYTHON_SKILL")
        key_submit = st.form_submit_button("Generate Key")

    if key_submit and key_name:
        scopes = [s.strip() for s in key_scopes.split(",") if s.strip()] if key_scopes else []
        r = requests.post(
            f"{BACKEND}/api-keys/",
            json={"name": key_name, "scopes": scopes},
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 201:
            data = r.json()
            st.success("Key created! **Copy it now — it won't be shown again.**")
            st.code(data["full_key"], language="text")
        else:
            st.error(f"Error {r.status_code}: {r.text}")

    st.divider()

    # List / revoke
    st.subheader("Existing Keys")
    try:
        r = requests.get(f"{BACKEND}/api-keys/", headers=_headers(), timeout=10)
        if r.ok:
            keys = r.json()
            if keys:
                for k in keys:
                    col1, col2, col3 = st.columns([3, 4, 1])
                    col1.write(f"**{k['name']}** (`{k['prefix']}…`)")
                    col2.write(f"Scopes: {', '.join(k.get('scopes', [])) or '—'}")
                    if col3.button("Revoke", key=f"rev_{k['key_id']}"):
                        requests.delete(f"{BACKEND}/api-keys/{k['key_id']}", headers=_headers(), timeout=10)
                        st.rerun()
            else:
                st.info("No API keys yet.")
    except requests.ConnectionError:
        st.error("Backend unreachable.")

# ──────────────────────────────────────────────────────────────
# TAB 4 — Users & Permissions
# ──────────────────────────────────────────────────────────────

with tab_users:
    st.header("User Management")

    # Register
    with st.form("user_form"):
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["viewer", "editor", "admin"])
        new_skills = st.text_input("Allowed skills (comma-separated)")
        user_submit = st.form_submit_button("Create User")

    if user_submit and new_user:
        skills_list = [s.strip() for s in new_skills.split(",") if s.strip()] if new_skills else []
        r = requests.post(
            f"{BACKEND}/auth/register",
            json={
                "username": new_user,
                "password": new_pass,
                "role": new_role,
                "allowed_skills": skills_list,
            },
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 201:
            st.success(f"User **{new_user}** created!")
        else:
            st.error(f"Error {r.status_code}: {r.text}")

    st.divider()

    # List users
    st.subheader("Existing Users")
    try:
        r = requests.get(f"{BACKEND}/auth/users", headers=_headers(), timeout=10)
        if r.ok:
            users = r.json()
            for u in users:
                with st.expander(f"**{u['username']}** — role: {u['role']}"):
                    current = u.get("allowed_skills", [])
                    st.write("Current permissions:", ", ".join(current) if current else "Unrestricted (admin)")

                    # Quick permission update
                    new_perms = st.text_input(
                        "Update allowed skills (comma-separated)",
                        value=", ".join(current),
                        key=f"perm_{u['username']}",
                    )
                    if st.button("Save permissions", key=f"save_{u['username']}"):
                        plist = [s.strip() for s in new_perms.split(",") if s.strip()]
                        rr = requests.put(
                            f"{BACKEND}/auth/users/{u['username']}/permissions",
                            json={"allowed_skills": plist},
                            headers=_headers(),
                            timeout=10,
                        )
                        if rr.ok:
                            st.success("Permissions updated")
                            st.rerun()
                        else:
                            st.error(rr.text)

                    if u["username"] != st.session_state.get("username"):
                        if st.button("Delete user", key=f"del_{u['username']}"):
                            requests.delete(
                                f"{BACKEND}/auth/users/{u['username']}", headers=_headers(), timeout=10
                            )
                            st.rerun()
    except requests.ConnectionError:
        st.error("Backend unreachable.")

# ──────────────────────────────────────────────────────────────
# TAB 5 — Logs (Audit Trail)
# ──────────────────────────────────────────────────────────────

with tab_logs:
    st.header("Audit Trail")
    st.info(
        "This tab shows real-time logs of skill fetches. "
        "In production, connect to a log aggregator (ELK, Loki, etc.)."
    )

    # Simple log viewer: pull the last skills fetched
    if st.button("Refresh logs"):
        pass  # triggers a rerun

    st.caption("Recent skill queries (from search endpoint):")
    st.code(
        "# To enable full audit logging, configure the Python backend\n"
        "# to emit structured logs to stdout/Elasticsearch.\n"
        "# Example log entry:\n"
        '{"timestamp": "2026-02-19T10:00:00Z", "action": "discover", '
        '"query": "How do I shard my DB?", "result": "SQL_SKILL"}',
        language="json",
    )
