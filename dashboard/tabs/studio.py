"""Skill Studio tab — search, tree, create/edit, delete."""
from __future__ import annotations

import streamlit as st
from dashboard.api_client import (
    delete_skill,
    get_skill,
    get_skill_tree,
    search_skills,
    upsert_skill,
)

# ── helpers ────────────────────────────────────────────────────────────────


def _render_tree(nodes: list, backend: str, headers: dict, indent: int = 0) -> None:
    """Recursively render the skill tree with Edit buttons."""
    for n in nodes:
        prefix = "&nbsp;" * indent * 4
        icon = "📂" if n.get("is_folder") else "📄"
        left, right = st.columns([8, 1])
        with left:
            st.markdown(
                f"{prefix}{icon} **{n['skill_id']}** — {n['summary']}",
                unsafe_allow_html=True,
            )
        with right:
            if st.button("✏️", key=f"edit_btn_{n['skill_id']}", help=f"Edit {n['skill_id']}"):
                skill, err = get_skill(backend, headers, n["skill_id"])
                if err:
                    st.error(err)
                else:
                    st.session_state["edit_skill"] = skill
                    st.rerun()

        if n.get("children"):
            _render_tree(n["children"], backend, headers, indent + 1)


# ── main render ────────────────────────────────────────────────────────────


def render(backend: str, headers: dict) -> None:
    st.header("Skill Studio")

    # ── Semantic Search ────────────────────────────────────────────────────
    st.subheader("🔍 Semantic Search")
    query = st.text_input("Search skills by intent")
    if query:
        results, err = search_skills(backend, headers, query, k=5)
        if err:
            st.warning(err)
        else:
            for s in results:
                with st.expander(f"**{s['skill_id']}** — {s['summary']}  (score: {s.get('score', 0):.3f})"):
                    if s.get("sub_skills"):
                        st.write("Sub-skills:", ", ".join(s["sub_skills"]))
                    col_load, col_edit = st.columns([2, 1])
                    with col_load:
                        if st.button(f"Load instruction", key=f"load_{s['skill_id']}"):
                            detail, derr = get_skill(backend, headers, s["skill_id"])
                            if derr:
                                st.error(derr)
                            else:
                                st.markdown(detail.get("instruction", "_no instruction_"))
                    with col_edit:
                        if st.button("✏️ Edit", key=f"search_edit_{s['skill_id']}"):
                            full, ferr = get_skill(backend, headers, s["skill_id"])
                            if ferr:
                                st.error(ferr)
                            else:
                                st.session_state["edit_skill"] = full
                                st.rerun()

    st.divider()

    # ── Skill Tree ─────────────────────────────────────────────────────────
    st.subheader("🌳 Skill Tree")
    if st.button("Refresh tree"):
        st.session_state.pop("_tree_cache", None)
        st.rerun()

    tree, tree_err = get_skill_tree(backend, headers)
    if tree_err:
        st.error(tree_err)
    elif tree:
        _render_tree(tree, backend, headers)
    else:
        st.info("No skills yet. Create one below!")

    st.divider()

    # ── Create / Edit Form ─────────────────────────────────────────────────
    editing = st.session_state.get("edit_skill")
    if editing:
        st.subheader(f"✏️ Editing: {editing['skill_id']}")
        if st.button("✖ Cancel edit"):
            del st.session_state["edit_skill"]
            st.rerun()
    else:
        st.subheader("➕ Create New Skill")

    with st.form("skill_form"):
        sid = st.text_input(
            "Skill ID",
            value=editing["skill_id"] if editing else "",
            placeholder="SQL_SKILL_MIGRATION",
            disabled=bool(editing),   # ID is immutable when editing
        )
        summary = st.text_input(
            "Summary",
            value=editing.get("summary", "") if editing else "",
            placeholder="Database migration including sharding, partitioning…",
        )
        is_folder = st.checkbox(
            "Is Folder (branch node)?",
            value=editing.get("is_folder", False) if editing else False,
        )
        sub_skills_raw = st.text_input(
            "Sub-skill IDs (comma-separated)",
            value=", ".join(editing.get("sub_skills", [])) if editing else "",
            placeholder="SQL_SKILL_MIGRATION, SQL_SKILL_OPT",
        )
        instruction = st.text_area(
            "Instruction (Markdown)",
            value=editing.get("instruction", "") if editing else "",
            height=250,
        )
        label = "Update Skill" if editing else "Save Skill"
        submitted = st.form_submit_button(label)

    if submitted:
        skill_id = (editing["skill_id"] if editing else sid).strip()
        if not skill_id:
            st.warning("Skill ID is required.")
        else:
            sub_list = [s.strip() for s in sub_skills_raw.split(",") if s.strip()] if sub_skills_raw else []
            payload = {
                "skill_id": skill_id,
                "summary": summary,
                "is_folder": is_folder,
                "sub_skills": sub_list,
                "instruction": instruction,
            }
            _, err = upsert_skill(backend, headers, payload)
            if err:
                st.error(err)
            else:
                st.success(f"Skill **{skill_id}** {'updated' if editing else 'created'}!")
                if editing:
                    del st.session_state["edit_skill"]
                st.rerun()

    st.divider()

    # ── Delete ─────────────────────────────────────────────────────────────
    st.subheader("🗑️ Delete Skill")
    del_id = st.text_input("Skill ID to delete", key="del_skill_input")
    if st.button("Delete") and del_id:
        ok, err = delete_skill(backend, headers, del_id.strip())
        if ok:
            st.success(f"Deleted **{del_id}**")
            st.rerun()
        else:
            st.error(err)
