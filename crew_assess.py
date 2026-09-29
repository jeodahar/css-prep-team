"""Crew 2: assesses one written answer."""
from crewai import Crew, Process, Task

from agent_assessor import build_assessor_agent


def run_assessment(llm, subject: str, question: str, answer: str, marks: int) -> str:
    assessor = build_assessor_agent(llm)

    task = Task(
        description=(
            f"Subject: CSS {subject}. Total marks: {marks}.\n"
            f"QUESTION:\n{question}\n\n"
            f"STUDENT ANSWER:\n{answer}\n\n"
            "Steps:\n"
            "1) Call 'Answer Structure Analyzer' with the student answer text.\n"
            "2) Call 'Web Search' at least once to verify one or two key facts in the answer.\n"
            "3) Mark like a strict but fair FPSC examiner using this rubric: understanding of the "
            "question 20%, content accuracy and depth 30%, analysis and arguments 20%, "
            "structure and coherence 15%, language 15%."
        ),
        expected_output=(
            "Markdown with these headings: Marks (x/total), Rubric breakdown, Strengths, "
            "Weaknesses, Missing points, Factual corrections, 5-step improvement plan, "
            "and a better opening paragraph."
        ),
        agent=assessor,
    )

    crew = Crew(
        agents=[assessor],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()
    out = getattr(task, "output", None)
    return getattr(out, "raw", None) or str(out or "")
