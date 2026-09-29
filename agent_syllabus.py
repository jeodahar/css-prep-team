from crewai import Agent

from config import get_rpm
from tool_documents import list_uploaded_files, read_uploaded_file
from tool_search import web_search


def build_syllabus_agent(llm) -> Agent:
    return Agent(
        role="CSS Syllabus Analyst",
        goal="Turn the CSS syllabus into a short, prioritised topic list.",
        backstory="Expert FPSC/CSS coach who summarises syllabi clearly and briefly.",
        tools=[list_uploaded_files, read_uploaded_file, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=get_rpm(),
    )
