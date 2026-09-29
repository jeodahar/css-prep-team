from crewai import Agent

from config import get_rpm
from tool_search import web_search


def build_notes_agent(llm) -> Agent:
    return Agent(
        role="CSS Topic Notes Writer",
        goal="Write short, accurate, exam-oriented notes and check facts with web search.",
        backstory="Senior CSS mentor who writes concise notes with key facts and source links.",
        tools=[web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=get_rpm(),
    )
