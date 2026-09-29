from crewai import Agent

from config import get_rpm
from tool_documents import list_uploaded_files, read_uploaded_file, search_uploaded_files
from tool_search import web_search


def build_past_paper_agent(llm) -> Agent:
    return Agent(
        role="CSS Past Paper Analyst",
        goal="Find repeated themes and question patterns in CSS past papers.",
        backstory="Has studied many years of CSS papers and spots repeating topics and command words.",
        tools=[list_uploaded_files, read_uploaded_file, search_uploaded_files, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=get_rpm(),
    )
