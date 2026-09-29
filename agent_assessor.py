from crewai import Agent

from tool_assessment import analyze_answer_structure
from tool_search import web_search


def build_assessor_agent(llm) -> Agent:
    return Agent(
        role="CSS Answer Assessor",
        goal="Mark the student's answer strictly but fairly and show exactly how to improve it.",
        backstory=(
            "You are an experienced FPSC-style examiner. You measure the answer with the "
            "structure tool, verify key facts with web search, then give marks, feedback "
            "and a clear improvement plan."
        ),
        tools=[analyze_answer_structure, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=6,
    )
