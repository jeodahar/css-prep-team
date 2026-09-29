"""Saves and loads user data (preparation packages and assessment reports) in Supabase.

If Supabase secrets are missing, is_enabled() is False and the app works session-only.
"""
import streamlit as st

TABLE = "css_data"


@st.cache_resource
def _create(url: str, key: str):
    """Only successful connections are cached, so fixing Secrets works without a reboot."""
    from supabase import create_client

    return create_client(url, key)


def _connect():
    try:
        return _create(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _client():
    return _connect()[0]


def setup_error():
    """Why cloud saving is off (or None)."""
    return _connect()[1]


def is_enabled() -> bool:
    return _client() is not None


def check_connection():
    """Returns (ok, message). Used by the 'Test cloud saving' button."""
    client = _client()
    if client is None:
        return False, f"Supabase is not connected. {setup_error() or ''}".strip()
    try:
        client.table(TABLE).select("id").limit(1).execute()
        return True, f"Connected. Table '{TABLE}' is working."
    except Exception as e:
        return False, f"Connected to Supabase, but the table is not usable yet: {e}"


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
