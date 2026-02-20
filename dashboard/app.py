"""
Streamlit Dashboard — main entry point.

Tabs:
  1. Health Check      → dashboard/tabs/health.py
  2. Skill Studio      → dashboard/tabs/studio.py   (incl. edit)
  3. Security          → dashboard/tabs/security.py
  4. Users & Perms     → dashboard/tabs/users.py
  5. Logs / Audit      → dashboard/tabs/logs.py

HTTP calls are centralised in dashboard/api_client.py.
"""
from __future__ import annotations

import streamlit as st

try:
    from dashboard.api_client import login
    from dashboard.tabs import health, logs, security, studio, users
except ModuleNotFoundError:
    from api_client import login
    from tabs import health, logs, security, studio, users

# ─── Page config ───────────────────────────────────────────────────────────

st.set_page_config(page_title="Cloud Agentic Skill", page_icon="🧠", layout="wide")

# ─── Sidebar ───────────────────────────────────────────────────────────────

BACKEND: str = st.sidebar.text_input("Backend URL", value="http://localhost:8000")

if "token" not in st.session_state:
    st.sidebar.subheader("Login")
    _u = st.sidebar.text_input("Username", value="admin")
    _p = st.sidebar.text_input("Password", type="password", value="admin")
    if st.sidebar.button("Log in"):
        token, err = login(BACKEND, _u, _p)
        if token:
            st.session_state["token"] = token
            st.session_state["username"] = _u
            st.rerun()
        else:
            st.sidebar.error(err or "Login failed.")
    st.stop()
else:
    st.sidebar.success(f"Logged in as **{st.session_state['username']}**")
    if st.sidebar.button("Log out"):
        del st.session_state["token"]
        del st.session_state["username"]
        st.rerun()


def _headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


# ─── Tabs ──────────────────────────────────────────────────────────────────

tab_health, tab_studio, tab_security, tab_users, tab_logs = st.tabs(
    ["🩺 Health Check", "🛠️ Skill Studio", "🔑 Security", "👤 Users", "📋 Logs"]
)

with tab_health:
    health.render(BACKEND)

with tab_studio:
    studio.render(BACKEND, _headers())

with tab_security:
    security.render(BACKEND, _headers())

with tab_users:
    users.render(BACKEND, _headers(), current_username=st.session_state.get("username", ""))

with tab_logs:
    logs.render()
