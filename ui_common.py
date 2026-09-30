"""Small helpers shared by the screens."""
import re

import streamlit as st

import storage

CUSTOM_Q = "✍️ Type my own question"
CUSTOM_T = "✍️ Type my own topic"


def cloud_on(ctx) -> bool:
    return bool(ctx["user_id"] and storage.is_enabled())


def current_package(subject):
    """The saved/built package, but only if it belongs to the chosen subject."""
    ss = st.session_state
    if ss.get("package") and ss.get("package_subject") == subject:
        return ss["package"]
    return None


def question_options(pkg):
    if not pkg:
        return []
    found = re.findall(r"^[\s*#>-]*(Q\d+[\.\):]?\s.+)$", pkg.get("questions", ""), re.M)
    return [q.replace("**", "").strip() for q in found]


def show_error(e):
    st.error(f"Something went wrong: {e}")
    st.info("If you see a rate-limit (429) error, wait one minute and try again.")
