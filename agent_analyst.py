from crewai import Agent

from config import get_rpm
from tool_question import analyze_question_words
from tool_syllabus import read_official_syllabus


def build_analyst_agent(llm) -> Agent:
    return Agent(
        role="CSS Question Analyst",
        goal="Show exactly what a CSS question is asking and how to structure a strong answer.",
        backstory="Former FPSC examiner who can read between the lines of any exam question.",
        tools=[analyze_question_words, read_official_syllabus],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=get_rpm(),
    )
