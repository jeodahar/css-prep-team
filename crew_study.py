"""Small crews for Study mode, Question analysis and the Study plan."""
from agent_analyst import build_analyst_agent
from agent_planner import build_planner_agent
from agent_tutor import build_tutor_agent
from crew_common import run_stage


def run_explanation(llm, subject, topic, level, progress=None) -> str:
    return run_stage(
        build_tutor_agent(llm),
        (
            f"Subject: CSS {subject}. Topic: {topic}. Level: {level}.\n"
            "Use at most 2 tool calls in total.\n"
            f"1) Call 'Read Official Syllabus' with subject='{subject}' only to see where this topic fits.\n"
            "2) Call 'Web Search' once to verify key facts, dates or definitions.\n"
            "Then teach the topic."
        ),
        (
            "Markdown under 450 words with these headings: In simple words, Key points, "
            "Background (dates, people, events), Arguments for and against (if relevant), "
            "How CSS examiners ask about it, Common mistakes, Memory tips, 3 self-check questions. "
            "End with 1-2 source links."
        ),
        progress,
        "Study Tutor",
    )


def run_question_analysis(llm, subject, question, progress=None) -> str:
    return run_stage(
        build_analyst_agent(llm),
        (
            f"Subject: CSS {subject}.\nQUESTION: {question}\n"
            "Use at most 2 tool calls in total.\n"
            "1) Call 'Question Word Analyzer' with the question text.\n"
            f"2) Call 'Read Official Syllabus' with subject='{subject}' to link the question to a syllabus topic.\n"
            "Then break down what the question really asks."
        ),
        (
            "Markdown under 400 words with headings: What it really asks (one sentence), "
            "Command words and what they demand, Hidden parts, Scope and keywords, Syllabus link, "
            "Suggested outline (introduction, 3-4 body points, conclusion, with a word split), "
            "Common traps, Time and word guide."
        ),
        progress,
        "Question Analyst",
    )


def run_study_plan(llm, subjects, days, hours, progress=None) -> str:
    names = ", ".join(subjects)
    return run_stage(
        build_planner_agent(llm),
        (
            f"Create a {days}-day study plan for CSS subjects: {names}. "
            f"The student can study about {hours} hours per day.\n"
            "Use exactly 1 tool call: 'Get Study Data' (recorded weak areas, scores, topics).\n"
            "Rules: schedule the weakest skills and weak topics first and revisit them later; "
            "split time across the subjects; add a short revision day every 5-6 days and a final "
            "day of full timed answer practice. Each day: 'Day N', 2-3 study blocks with hours, "
            "and one timed writing task naming the question type to practise. "
            "If there are more than 14 days, group them into weeks with a one-line daily focus."
        ),
        "Markdown plan under 600 words: first 3 lines of priorities, then the day-by-day plan.",
        progress,
        "Study Planner",
    )
