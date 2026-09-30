from crewai import Agent

from config import get_rpm
from tool_progress import get_study_data


def build_planner_agent(llm) -> Agent:
    return Agent(
        role="CSS Study Planner",
        goal="Build a realistic day-by-day study plan that fixes the student's recorded weak areas first.",
        backstory="Experienced CSS coach who plans revision around each student's real weaknesses.",
        tools=[get_study_data],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=4,
        max_rpm=get_rpm(),
    )
