from crewai import Agent

from tool_documents import list_uploaded_files, read_uploaded_file, search_uploaded_files
from tool_search import web_search


def build_past_paper_agent(llm) -> Agent:
    return Agent(
        role="CSS Past Paper Analyst",
        goal="Find repeated questions, topic frequency and question patterns in CSS past papers.",
        backstory=(
            "You have studied many years of CSS papers. You spot which topics repeat, "
            "which command words examiners prefer (discuss, critically examine, evaluate) "
            "and which topics are likely to appear next."
        ),
        tools=[list_uploaded_files, read_uploaded_file, search_uploaded_files, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )
