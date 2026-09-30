"""Gives the Study Planner the student's recorded weak areas and topic lists."""
from crewai.tools import tool

_STATE = {"context": ""}


def set_study_context(text: str) -> None:
    _STATE["context"] = text or ""


@tool("Get Study Data")
def get_study_data(scope: str = "all") -> str:
    """Return the student's recorded weak areas (skills and topics), recent scores and syllabus topics
    for the chosen subjects. Call it once with scope='all'."""
    return _STATE["context"] or "No recorded data yet. Plan evenly across the subjects."
