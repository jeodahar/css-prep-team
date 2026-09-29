from crewai import Agent

from tools.document_tools import list_uploaded_files, read_uploaded_file
from tools.search_tools import fetch_webpage, web_search


def build_syllabus_agent(llm) -> Agent:
    return Agent(
        role="CSS Syllabus Analyst",
        goal="Break the CSS subject syllabus into clear topics and rank them by importance.",
        backstory=(
            "You are an expert FPSC/CSS coach. You know how the CSS syllabus is organised "
            "and you turn long syllabus text into a short, prioritised topic list."
        ),
        tools=[list_uploaded_files, read_uploaded_file, web_search, fetch_webpage],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )
