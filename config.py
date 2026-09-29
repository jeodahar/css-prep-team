"""Central settings: LLM, folders, subject list and small helpers."""
import os
from pathlib import Path

import streamlit as st
from crewai import LLM

MODEL_NAME = "groq/openai/gpt-oss-120b"  # "groq/" prefix tells CrewAI/LiteLLM to use Groq
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Groq free tier has small per-minute token limits, so every tool result is capped.
MAX_TOOL_CHARS = 4000

CSS_SUBJECTS = [
    "Essay",
    "Precis & Composition",
    "General Science & Ability (GSA)",
    "Pakistan Affairs",
    "Current Affairs",
    "Islamic Studies",
    "Political Science I",
    "Political Science II",
    "Gender Studies",
    "Criminology",
    "History of Indo-Pak",
    "Sindhi",
    "Other",
]


def truncate(text: str, limit: int = MAX_TOOL_CHARS) -> str:
    """Cut long text so it does not overload the model."""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def get_api_key():
    """Read GROQ_API_KEY from Streamlit secrets, or from environment variables."""
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY")


def get_llm() -> LLM:
    key = get_api_key()
    if not key:
        raise ValueError(
            "GROQ_API_KEY is missing. Add it in Streamlit: App settings > Secrets."
        )
    os.environ["GROQ_API_KEY"] = key
    return LLM(model=MODEL_NAME, api_key=key, temperature=0.3)
