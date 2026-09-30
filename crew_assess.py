"""Crew 2: assesses one written answer."""
from agent_assessor import build_assessor_agent
from crew_common import run_stage
from tool_assessment import set_current_answer

MAX_ANSWER_CHARS = 7000


def run_assessment(llm, subject, question, answer, marks, progress=None, from_photo=False) -> str:
    note = ""
    if len(answer) > MAX_ANSWER_CHARS:
        answer = answer[:MAX_ANSWER_CHARS]
        note = "\n(The answer was cut to fit the free Groq limit; mention this in your report.)"
    if from_photo:
        note += "\n(This answer was read from a handwritten photo by OCR. Ignore small spelling slips caused by OCR.)"
    set_current_answer(answer)

    return run_stage(
        build_assessor_agent(llm),
        (
            f"Subject: CSS {subject}. Total marks: {marks}.\n"
            f"QUESTION:\n{question}\n\n"
            f"STUDENT ANSWER:\n{answer}{note}\n\n"
            "Steps (use at most 2 tool calls):\n"
            "1) Call 'Answer Structure Analyzer' with check='all' (it already has the answer).\n"
            "2) Call 'Web Search' once to verify one or two key facts.\n"
            "3) Mark like a strict but fair FPSC examiner: understanding of the question 20%, content "
            "accuracy and depth 30%, analysis and arguments 20%, structure 15%, language 15%.\n"
            "4) Finish with ONE last line in exactly this format (numbers only): "
            f"DATA: marks=<0-{marks}>; understanding=<0-20>; content=<0-30>; analysis=<0-20>; "
            "structure=<0-15>; language=<0-15>; weak_topics=<up to 3 syllabus topics the student "
            "missed or got wrong, separated by |>"
        ),
        (
            "Markdown, under 450 words, with headings: Marks (x/total), Rubric breakdown, Strengths, "
            "Weaknesses, Missing points, Factual corrections, 5-step improvement plan, better opening "
            "paragraph. The very last line must be the DATA line."
        ),
        progress,
        "Assessor",
    )
