from crewai import Agent

from config import get_rpm
from tool_search import web_search
from tool_syllabus import read_official_syllabus


def build_tutor_agent(llm) -> Agent:
    return Agent(
        role="CSS Study Tutor",
        goal="Explain one syllabus topic clearly, accurately and in an exam-oriented way.",
        backstory="Patient senior CSS mentor who teaches from the official syllabus and checks facts.",
        tools=[read_official_syllabus, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=get_rpm(),
    )
