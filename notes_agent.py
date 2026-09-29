from crewai import Agent

from tools.search_tools import fetch_webpage, web_search


def build_notes_agent(llm) -> Agent:
    return Agent(
        role="CSS Topic Notes Writer",
        goal="Write short, accurate, exam-oriented notes for the most important topics.",
        backstory=(
            "You are a senior CSS mentor. You write concise notes with key facts, dates, "
            "arguments for and against, and reliable references. You always check facts "
            "with the web tools before writing."
        ),
        tools=[web_search, fetch_webpage],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )
