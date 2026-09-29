"""Crew 1: builds the preparation package one small step at a time (fits Groq free limits)."""
import time

from agent_notes import build_notes_agent
from agent_past_paper import build_past_paper_agent
from agent_question import build_question_agent
from agent_syllabus import build_syllabus_agent
from config import truncate
from crew_common import run_stage

COOLDOWN_SECONDS = 20


def _cooldown(progress):
    progress(f"Short pause ({COOLDOWN_SECONDS}s) to respect Groq's per-minute limit...")
    time.sleep(COOLDOWN_SECONDS)


def run_preparation(llm, subject, focus, num_questions, marks, partial, progress=None) -> dict:
    """`partial` keeps finished steps, so a retry continues where it stopped."""
    progress = progress or (lambda msg: None)
    focus_text = focus.strip() or "the whole subject"

    if "topics" not in partial:
        progress("Step 1/4: Syllabus Analyst is working...")
        partial["topics"] = run_stage(
            build_syllabus_agent(llm),
            (
                f"Subject: CSS {subject}. Focus: {focus_text}.\n"
                "Use at most 2 tool calls in total.\n"
                "1) Call 'List Uploaded Files' with kind='syllabus'. If a file exists, read part 1 "
                "with 'Read Uploaded File'.\n"
                f"2) If no file exists, call 'Web Search' once for 'CSS {subject} syllabus FPSC'.\n"
                "Then list the syllabus topics and rank each High, Medium or Low priority."
            ),
            "Numbered list of at most 12 topics, one short line each with priority. Under 300 words.",
            progress,
            "Syllabus Analyst",
        )
        _cooldown(progress)

    if "past_papers" not in partial:
        progress("Step 2/4: Past Paper Analyst is working...")
        partial["past_papers"] = run_stage(
            build_past_paper_agent(llm),
            (
                f"Subject: CSS {subject}. Focus: {focus_text}.\n"
                "Use at most 2 tool calls in total.\n"
                "1) Call 'List Uploaded Files' with kind='paper'. If files exist, read part 1 of the "
                "first one with 'Read Uploaded File', or use 'Search Uploaded Files' for one top topic.\n"
                f"2) If none exist, call 'Web Search' once for 'CSS {subject} past papers questions'.\n"
                f"Topics so far:\n{truncate(partial['topics'], 1500)}"
            ),
            "Under 250 words: repeated themes, question styles and command words, 5 predicted hot topics.",
            progress,
            "Past Paper Analyst",
        )
        _cooldown(progress)

    if "notes" not in partial:
        progress("Step 3/4: Notes Writer is working...")
        partial["notes"] = run_stage(
            build_notes_agent(llm),
            (
                f"Write exam notes for CSS {subject}. Choose {focus_text} if it is a specific topic; "
                "otherwise choose the 3 highest-priority topics below.\n"
                "Call 'Web Search' at most 2 times (one query can cover 2-3 topics) to verify facts. "
                "For each topic give: key points, important dates/facts, arguments for and against, "
                "and 1-2 source links. Max 120 words per topic.\n"
                f"Topics:\n{truncate(partial['topics'], 1200)}\n"
                f"Past paper trends:\n{truncate(partial['past_papers'], 1000)}"
            ),
            "Markdown notes, one short section per topic, with source links.",
            progress,
            "Notes Writer",
        )
        _cooldown(progress)

    if "questions" not in partial:
        progress("Step 4/4: Question Setter is working...")
        partial["questions"] = run_stage(
            build_question_agent(llm),
            (
                f"Set {num_questions} CSS-style practice questions for {subject}, {marks} marks each, "
                "using the material below. Mix command words (discuss, critically examine, evaluate). "
                "You may call 'Search Uploaded Files' once to match past paper style.\n"
                "FORMAT RULE: start every question on its own line as 'Q1. ...', 'Q2. ...' and so on, "
                "then a 'Hint:' line with 2-3 key points.\n"
                f"Topics:\n{truncate(partial['topics'], 900)}\n"
                f"Past paper trends:\n{truncate(partial['past_papers'], 800)}\n"
                f"Notes:\n{truncate(partial['notes'], 1200)}"
            ),
            "A numbered question paper (Q1..Qn) with a short hint under each question.",
            progress,
            "Question Setter",
        )

    return dict(partial)
