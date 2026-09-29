"""Central settings: LLM, folders, subject list and small helpers."""
import os
import sys
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


# ---------------------------------------------------------------------------
# Groq compatibility patch
# Some CrewAI versions add a private "cache_breakpoint" key to messages (meant for
# Anthropic). Groq rejects it with: property 'cache_breakpoint' is unsupported.
# This patch (1) stops CrewAI adding it and (2) strips it from any request that
# still contains it. It is safe to leave in even after CrewAI fixes the bug.
# ---------------------------------------------------------------------------
_MARKER = "cache_breakpoint"


def _strip_marker(messages):
    if not isinstance(messages, list):
        return messages
    return [
        {k: v for k, v in m.items() if k != _MARKER} if isinstance(m, dict) else m
        for m in messages
    ]


def _apply_groq_patch():
    def _identity(msg, *args, **kwargs):
        return msg

    # 1) Stop CrewAI from adding the marker.
    try:
        import crewai.llms.cache as cache_module

        cache_module.mark_cache_breakpoint = _identity
    except Exception:
        pass
    for name in ("crewai.agents.crew_agent_executor", "crewai.experimental.agent_executor"):
        try:
            __import__(name)
        except Exception:
            pass
    for name, module in list(sys.modules.items()):
        if name.startswith("crewai") and module is not None and hasattr(module, "mark_cache_breakpoint"):
            try:
                setattr(module, "mark_cache_breakpoint", _identity)
            except Exception:
                pass

    # 2) Safety net: remove the marker right before the request goes to LiteLLM.
    try:
        import litellm

        if not getattr(litellm.completion, "_css_patched", False):
            original_completion = litellm.completion

            def completion(*args, **kwargs):
                if "messages" in kwargs:
                    kwargs["messages"] = _strip_marker(kwargs["messages"])
                elif len(args) > 1:
                    args = (args[0], _strip_marker(args[1])) + tuple(args[2:])
                return original_completion(*args, **kwargs)

            completion._css_patched = True
            litellm.completion = completion

        if not getattr(litellm.acompletion, "_css_patched", False):
            original_acompletion = litellm.acompletion

            async def acompletion(*args, **kwargs):
                if "messages" in kwargs:
                    kwargs["messages"] = _strip_marker(kwargs["messages"])
                return await original_acompletion(*args, **kwargs)

            acompletion._css_patched = True
            litellm.acompletion = acompletion
    except Exception:
        pass


_apply_groq_patch()


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
    _apply_groq_patch()  # make sure the patch is active before any request
    return LLM(model=MODEL_NAME, api_key=key, temperature=0.3)
