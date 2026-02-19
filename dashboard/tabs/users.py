"""Users & Permissions tab."""
from __future__ import annotations

import streamlit as st
from dashboard.api_client import (
    delete_user,
    list_users,
    register_user,
    update_user_permissions,
)


def render(backend: str, headers: dict, current_username: str) -> None:
    st.header("User Management")

    # ── Create User ────────────────────────────────────────────────────────
    st.subheader("➕ Create New User")
    with st.form("user_form"):
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["viewer", "editor", "admin"])
        new_skills = st.text_input("Allowed skills (comma-separated)")
        user_submit = st.form_submit_button("Create User")

    if user_submit and new_user:
        skills_list = [s.strip() for s in new_skills.split(",") if s.strip()] if new_skills else []
        _, err = register_user(backend, headers, new_user, new_pass, new_role, skills_list)
        if err:
            st.error(err)
        else:
            st.success(f"User **{new_user}** created!")
            st.rerun()

    st.divider()

    # ── Existing Users ─────────────────────────────────────────────────────
    st.subheader("Existing Users")
    users, err = list_users(backend, headers)
    if err:
        st.error(err)
        return

    for u in users:
        with st.expander(f"**{u['username']}** — role: {u['role']}"):
            current_perms = u.get("allowed_skills", [])
            st.write("Current permissions:", ", ".join(current_perms) if current_perms else "Unrestricted (admin)")

            new_perms = st.text_input(
                "Update allowed skills (comma-separated)",
                value=", ".join(current_perms),
                key=f"perm_{u['username']}",
            )
            if st.button("Save permissions", key=f"save_{u['username']}"):
                plist = [s.strip() for s in new_perms.split(",") if s.strip()]
                ok, uerr = update_user_permissions(backend, headers, u["username"], plist)
                if ok:
                    st.success("Permissions updated")
                    st.rerun()
                else:
                    st.error(uerr)

            if u["username"] != current_username:
                if st.button("Delete user", key=f"del_{u['username']}"):
                    delete_user(backend, headers, u["username"])
                    st.rerun()
