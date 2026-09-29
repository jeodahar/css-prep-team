"""Shared helper: runs one agent as one small crew, and waits/retries when Groq's limit is hit."""
import time

from crewai import Crew, Process, Task

MAX_TRIES = 3
WAIT_SECONDS = 65


def _raw(task: Task) -> str:
    out = getattr(task, "output", None)
    return getattr(out, "raw", None) or str(out or "")


def run_stage(agent, description, expected_output, progress=None, label="Agent") -> str:
    progress = progress or (lambda msg: None)
    for attempt in range(1, MAX_TRIES + 1):
        task = Task(description=description, expected_output=expected_output, agent=agent)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        try:
            crew.kickoff()
            return _raw(task)
        except Exception as e:
            msg = str(e)
            if "Request too large" in msg:
                raise RuntimeError(
                    "One request is bigger than Groq's free per-minute limit (8,000 tokens). "
                    "Try a shorter answer/focus topic, or upgrade Groq to the Developer plan."
                ) from e
            is_rate = "rate_limit" in msg.lower() or "429" in msg or "RateLimit" in type(e).__name__
            if is_rate and attempt < MAX_TRIES:
                progress(f"{label}: Groq speed limit reached. Waiting {WAIT_SECONDS}s (try {attempt}/{MAX_TRIES})...")
                time.sleep(WAIT_SECONDS)
                continue
            raise
    return ""
