"""Crew 1: builds the preparation package (topics, past paper trends, notes, questions)."""
from crewai import Crew, Process, Task

from agents.notes_agent import build_notes_agent
from agents.past_paper_agent import build_past_paper_agent
from agents.question_agent import build_question_agent
from agents.syllabus_agent import build_syllabus_agent


def _raw(task: Task) -> str:
    out = getattr(task, "output", None)
    return getattr(out, "raw", None) or str(out or "")


def run_preparation(llm, subject: str, focus: str, num_questions: int, marks: int) -> dict:
    syllabus_agent = build_syllabus_agent(llm)
    paper_agent = build_past_paper_agent(llm)
    notes_agent = build_notes_agent(llm)
    question_agent = build_question_agent(llm)

    focus_text = focus.strip() or "the whole subject"

    t_syllabus = Task(
        description=(
            f"Subject: CSS {subject}. Focus: {focus_text}.\n"
            "1) Call 'List Uploaded Files' with kind='syllabus'.\n"
            "2) If a syllabus file exists, read it with 'Read Uploaded File' (at most 3 parts).\n"
            f"3) If none exists, use 'Web Search' for 'CSS {subject} syllabus FPSC' and read the best page.\n"
            "Break the syllabus into topics and rank each as High, Medium or Low priority."
        ),
        expected_output=(
            "A numbered list of 10-15 topics. Each line: topic name, one-line scope, priority."
        ),
        agent=syllabus_agent,
    )

    t_papers = Task(
        description=(
            f"Subject: CSS {subject}. Focus: {focus_text}.\n"
            "1) Call 'List Uploaded Files' with kind='paper'.\n"
            "2) If past papers exist, read them ('Read Uploaded File', at most 3 parts) and use "
            "'Search Uploaded Files' for the top topics to see how often they appear.\n"
            f"3) If none exist, use 'Web Search' for 'CSS {subject} past papers questions'.\n"
            "Find repeated questions, topic frequency, and the command words examiners use."
        ),
        expected_output=(
            "Short report: repeated questions/themes, topic frequency, question patterns, "
            "and 5 predicted hot topics."
        ),
        agent=paper_agent,
        context=[t_syllabus],
    )

    t_notes = Task(
        description=(
            f"Write exam-oriented notes for CSS {subject}. Pick {focus_text} if it is a specific topic; "
            "otherwise pick the 3 highest-priority topics from the syllabus and past paper analysis.\n"
            "For each topic use 'Web Search' at least once to verify facts. Include: key points, "
            "important dates/facts, arguments for and against, and 2 source links. "
            "Keep each topic under 250 words."
        ),
        expected_output="Markdown notes, one section per topic, with source links.",
        agent=notes_agent,
        context=[t_syllabus, t_papers],
    )

    t_questions = Task(
        description=(
            f"Set {num_questions} CSS-style practice questions for {subject}, {marks} marks each, "
            "based on the topic list, past paper trends and notes. Mix question types "
            "(discuss, critically examine, evaluate). You may call 'Search Uploaded Files' to match "
            "the past paper style.\n"
            "FORMAT RULE: start every question on its own line as 'Q1. ...', 'Q2. ...' and so on, "
            "then add a 'Hint:' line with 2-3 key points to cover."
        ),
        expected_output="A numbered question paper (Q1..Qn) with a short hint under each question.",
        agent=question_agent,
        context=[t_syllabus, t_papers, t_notes],
    )

    crew = Crew(
        agents=[syllabus_agent, paper_agent, notes_agent, question_agent],
        tasks=[t_syllabus, t_papers, t_notes, t_questions],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()

    return {
        "topics": _raw(t_syllabus),
        "past_papers": _raw(t_papers),
        "notes": _raw(t_notes),
        "questions": _raw(t_questions),
    }
