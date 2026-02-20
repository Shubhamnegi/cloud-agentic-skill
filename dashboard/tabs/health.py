"""Health Check tab."""
from __future__ import annotations

import streamlit as st
try:
    from dashboard.api_client import get_health
except ModuleNotFoundError:
    from api_client import get_health


def render(backend: str) -> None:
    st.header("System Health")
    data, err = get_health(backend)
    if err:
        st.error(err)
        return

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
