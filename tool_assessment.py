"""Tool used by the Answer Assessor to measure the student's answer objectively."""
import re

from crewai.tools import tool

_STATE = {"answer": ""}


def set_current_answer(text: str) -> None:
    """Called by the crew before the assessor starts, so the answer need not be repeated in tool calls."""
    _STATE["answer"] = text or ""


@tool("Answer Structure Analyzer")
def analyze_answer_structure(check: str = "all") -> str:
    """Measure the student's submitted answer (word count, paragraphs, sentence length, facts/dates,
    headings, conclusion cue). You do NOT need to pass the answer text; just call it with check='all'."""
    text = _STATE["answer"].strip()
    if not text:
        return "No answer available."
    words = re.findall(r"\b\w+\b", text)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    sentences = [s for s in re.split(r"[.!?]+\s", text) if s.strip()]
    avg_len = len(words) / max(1, len(sentences))
    numbers = re.findall(r"\b\d{1,4}\b", text)
    headings = [
        ln for ln in text.splitlines()
        if ln.strip() and (ln.strip().endswith(":") or ln.lstrip().startswith(("#", "-", "*")))
    ]
    conclusion_cue = any(
        cue in text.lower()[-600:]
        for cue in ("in conclusion", "to conclude", "in summary", "thus", "therefore", "hence")
    )
    return (
        f"Words: {len(words)}\n"
        f"Paragraphs: {len(paragraphs)}\n"
        f"Sentences: {len(sentences)} (average {avg_len:.1f} words each)\n"
        f"Numbers/dates mentioned: {len(numbers)}\n"
        f"Headings/bullets: {len(headings)}\n"
        f"Conclusion cue near the end: {'yes' if conclusion_cue else 'no'}\n"
        "(These counts are rough heuristics, not a final judgement.)"
    )
