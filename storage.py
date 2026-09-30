"""Saves and loads user data (preparation packages and assessment reports) in Supabase.

If Supabase secrets are missing, is_enabled() is False and the app works session-only.
"""
from urllib.parse import urlparse

import streamlit as st

TABLE = "css_data"


def _clean_url(url) -> str:
    """Keep only https://<project>.supabase.co (removes /rest/v1, trailing / and stray quotes)."""
    url = str(url).strip().strip("\"'").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url


def _clean_key(key) -> str:
    return str(key).strip().strip("\"'").strip()


@st.cache_resource
def _create(url: str, key: str):
    """Only successful connections are cached, so fixing Secrets works without a reboot."""
    from supabase import create_client

    return create_client(url, key)


def _connect():
    try:
        url = _clean_url(st.secrets["SUPABASE_URL"])
        key = _clean_key(st.secrets["SUPABASE_KEY"])
        return _create(url, key), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _client():
    return _connect()[0]


def setup_error():
    """Why cloud saving is off (or None)."""
    return _connect()[1]


def _explain(prefix: str, e: Exception) -> str:
    msg = str(e)
    if "row-level security" in msg or "42501" in msg:
        return (
            f"{prefix}: Supabase blocked the write because SUPABASE_KEY is a public key. "
            "Put the secret key (starts with sb_secret_) in Streamlit Secrets as SUPABASE_KEY."
        )
    return f"{prefix}: {msg}"


def is_enabled() -> bool:
    return _client() is not None


def check_connection():
    """Returns (ok, message). Tries a real write, so a wrong key is caught."""
    client = _client()
    if client is None:
        return False, f"Supabase is not connected. {setup_error() or ''}".strip()
    try:
        client.table(TABLE).insert(
            {"user_id": "_test", "kind": "_test", "subject": "_test", "content": {"ok": True}}
        ).execute()
        client.table(TABLE).delete().eq("user_id", "_test").eq("kind", "_test").execute()
        return True, f"Connected. Reading and saving to table '{TABLE}' both work."
    except Exception as e:
        return False, _explain("Connected to Supabase, but saving does not work yet", e)


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
        return _explain("Could not save the package", e)


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
        return _explain("Could not save the report", e)


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


def save_replace(user_id: str, kind: str, subject: str, content: dict):
    """Save one item, replacing any earlier item with the same user, kind and subject key.
    Returns an error text or None."""
    client = _client()
    if client is None:
        return "Cloud saving is not set up."
    try:
        client.table(TABLE).delete().eq("user_id", user_id).eq("kind", kind).eq(
            "subject", subject
        ).execute()
        client.table(TABLE).insert(
            {"user_id": user_id, "kind": kind, "subject": subject, "content": content}
        ).execute()
        return None
    except Exception as e:
        return _explain("Could not save", e)
