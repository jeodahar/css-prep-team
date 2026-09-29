from crewai import Agent

from config import get_rpm
from tool_assessment import analyze_answer_structure
from tool_search import web_search


def build_assessor_agent(llm) -> Agent:
    return Agent(
        role="CSS Answer Assessor",
        goal="Mark the student's answer strictly but fairly and show how to improve it.",
        backstory="Experienced FPSC-style examiner who measures, fact-checks, then gives clear feedback.",
        tools=[analyze_answer_structure, web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=get_rpm(),
    )
