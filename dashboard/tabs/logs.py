"""Audit Logs tab."""
from __future__ import annotations

import streamlit as st


def render() -> None:
    st.header("Audit Trail")
    st.info(
        "This tab shows real-time logs of skill fetches. "
        "In production, connect to a log aggregator (ELK, Loki, etc.)."
    )

    if st.button("Refresh logs"):
        st.rerun()

    st.caption("Recent skill queries (from search endpoint):")
    st.code(
        "# To enable full audit logging, configure the Python backend\n"
        "# to emit structured logs to stdout/Elasticsearch.\n"
        "# Example log entry:\n"
        '{"timestamp": "2026-02-19T10:00:00Z", "action": "discover", '
        '"query": "How do I shard my DB?", "result": "SQL_SKILL"}',
        language="json",
    )
