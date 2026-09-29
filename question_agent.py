from crewai import Agent

from tools.document_tools import list_uploaded_files, search_uploaded_files
from tools.search_tools import web_search


def build_question_agent(llm) -> Agent:
    return Agent(
        role="CSS Examiner (Question Setter)",
        goal="Set realistic CSS-style practice questions that match past paper patterns.",
        backstory=(
            "You are a former paper setter. You write questions in the same style and "
            "difficulty as the FPSC, using the topic analysis and past paper trends."
        ),
        tools=[list_uploaded_files, search_uploaded_files, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=6,
    )
