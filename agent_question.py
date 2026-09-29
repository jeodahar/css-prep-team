from crewai import Agent

from config import get_rpm
from tool_documents import search_uploaded_files
from tool_search import web_search


def build_question_agent(llm) -> Agent:
    return Agent(
        role="CSS Examiner (Question Setter)",
        goal="Set realistic CSS-style practice questions that match past paper patterns.",
        backstory="Former paper setter who writes questions in FPSC style and difficulty.",
        tools=[search_uploaded_files, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        max_rpm=get_rpm(),
    )
