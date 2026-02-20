"""Security tab — API Key management."""
from __future__ import annotations

import streamlit as st
try:
    from dashboard.api_client import create_api_key, list_api_keys, revoke_api_key
except ModuleNotFoundError:
    from api_client import create_api_key, list_api_keys, revoke_api_key


def render(backend: str, headers: dict) -> None:
    st.header("API Key Management")

    # ── Generate Key ───────────────────────────────────────────────────────
    st.subheader("➕ Generate New Key")
    with st.form("key_form"):
        key_name = st.text_input("Key name", placeholder="production-agent")
        key_scopes = st.text_input(
            "Scopes (comma-separated skill IDs)", placeholder="SQL_SKILL, PYTHON_SKILL"
        )
        key_submit = st.form_submit_button("Generate Key")

    if key_submit and key_name:
        scopes = [s.strip() for s in key_scopes.split(",") if s.strip()] if key_scopes else []
        data, err = create_api_key(backend, headers, key_name, scopes)
        if err:
            st.error(err)
        else:
            st.success("Key created! **Copy it now — it won't be shown again.**")
            st.code(data["full_key"], language="text")

    st.divider()

    # ── Existing Keys ──────────────────────────────────────────────────────
    st.subheader("Existing Keys")
    keys, err = list_api_keys(backend, headers)
    if err:
        st.error(err)
    elif keys:
        for k in keys:
            col1, col2, col3 = st.columns([3, 4, 1])
            col1.write(f"**{k['name']}** (`{k['prefix']}…`)")
            col2.write(f"Scopes: {', '.join(k.get('scopes', [])) or '—'}")
            if col3.button("Revoke", key=f"rev_{k['key_id']}"):
                ok, rev_err = revoke_api_key(backend, headers, k["key_id"])
                if ok:
                    st.rerun()
                else:
                    st.error(rev_err)
    else:
        st.info("No API keys yet.")
