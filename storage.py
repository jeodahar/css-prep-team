"""Saves and loads user data (preparation packages and assessment reports) in Supabase.

If Supabase secrets are missing, is_enabled() is False and the app works session-only.
"""
import streamlit as st

TABLE = "css_data"


@st.cache_resource
def _client():
    try:
        from supabase import create_client

        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None


def is_enabled() -> bool:
    return _client() is not None


def save_package(user_id: str, subject: str, content: dict):
    """Keep one package per user and subject (old one is replaced). Returns an error text or None."""
    client = _client()
    if client is None:
        return "Cloud saving is not set up."
    try:
        client.table(TABLE).delete().eq("user_id", user_id).eq("kind", "package").eq(
            "subject", subject
        ).execute()
        client.table(TABLE).insert(
            {"user_id": user_id, "kind": "package", "subject": subject, "content": content}
        ).execute()
        return None
    except Exception as e:
        return f"Could not save the package: {e}"


def save_report(user_id: str, subject: str, item: dict):
    """Add one assessment report. Returns an error text or None."""
    client = _client()
    if client is None:
        return "Cloud saving is not set up."
    try:
        client.table(TABLE).insert(
            {"user_id": user_id, "kind": "report", "subject": subject, "content": item}
        ).execute()
        return None
    except Exception as e:
        return f"Could not save the report: {e}"


def load_items(user_id: str, kind: str, subject: str = None):
    """Returns (rows, error). Rows are sorted oldest to newest."""
    client = _client()
    if client is None:
        return [], "Cloud saving is not set up."
    try:
        query = client.table(TABLE).select("*").eq("user_id", user_id).eq("kind", kind)
        if subject:
            query = query.eq("subject", subject)
        rows = query.execute().data or []
        rows.sort(key=lambda r: r.get("created_at") or "")
        return rows, None
    except Exception as e:
        return [], f"Could not load saved data: {e}"
