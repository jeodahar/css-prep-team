"""Deterministic helper for the Question Analyst: explains command words and estimates time/words."""
import re

from crewai.tools import tool

# Longer phrases first so "critically examine" is found before "examine".
COMMANDS = [
    ("critically examine", "Weigh strengths and weaknesses using evidence, then give your own judgement."),
    ("critically analyse", "Break the issue into parts and judge each part, with evidence for and against."),
    ("critically analyze", "Break the issue into parts and judge each part, with evidence for and against."),
    ("critically evaluate", "Judge the value or success of something, weighing both sides, and conclude."),
    ("critically discuss", "Present and question the different views, then take a reasoned position."),
    ("to what extent", "Give a balanced answer that says how far the statement is true, and why."),
    ("with reference to", "Anchor the whole answer in the named case, period or text."),
    ("evaluate", "Judge value or success using criteria and evidence; end with a verdict."),
    ("assess", "Weigh importance or effect with evidence and give a reasoned conclusion."),
    ("appraise", "Estimate the worth or quality, stating strengths and weaknesses."),
    ("analyse", "Split the topic into parts and explain how the parts relate and why."),
    ("analyze", "Split the topic into parts and explain how the parts relate and why."),
    ("examine", "Investigate closely: facts, causes, effects and different views."),
    ("discuss", "Give a balanced, detailed account with arguments for and against, then conclude."),
    ("comment", "Give your informed opinion, supported by facts and reasons."),
    ("explain", "Make it clear: give reasons, causes and how it works."),
    ("elucidate", "Make it clear with reasons and examples."),
    ("illustrate", "Support the point with concrete examples and cases."),
    ("compare", "Show similarities and differences, point by point, then conclude."),
    ("contrast", "Focus on the differences and why they matter."),
    ("differentiate", "Clearly separate the two ideas and show the differences."),
    ("describe", "Give a clear, detailed account without much argument."),
    ("outline", "Give the main points briefly and in order."),
    ("define", "State the exact meaning, then add scope and examples."),
    ("justify", "Defend the statement with strong reasons and evidence."),
    ("highlight", "Pick out and stress the most important points."),
    ("elaborate", "Expand the idea with detail, reasons and examples."),
    ("argue", "Build a clear case for one position, with evidence, and answer objections."),
    ("trace", "Follow the development step by step in time order."),
    ("review", "Survey the topic, judging strengths and weaknesses."),
]


@tool("Question Word Analyzer")
def analyze_question_words(question: str) -> str:
    """Finds the command words in a CSS question and explains what each demands.
    Also reports possible sub-parts, years mentioned, and a rough time/word guide from the marks."""
    q = (question or "").strip()
    low = q.lower()
    used, found = [], []
    for word, meaning in COMMANDS:
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", low):
            if not any(m.start() < e and m.end() > s for s, e in used):
                used.append((m.start(), m.end()))
                found.append(f"- {word}: {meaning}")
                break
    lines = ["Command words found:"] + (found or ["- none clearly found; treat it as 'discuss'."])

    parts = 1 + low.count("?") - (1 if low.rstrip().endswith("?") else 0) + low.count(";")
    if " and " in low:
        parts = max(parts, 2)
    lines.append(f"Possible separate parts to answer: {max(parts, 1)} (check 'and', ';' and '?').")

    ref = re.search(r"with reference to (.+?)(?:[.?]|$)", low)
    if ref:
        lines.append(f"Must be anchored in: {ref.group(1).strip()}")
    years = sorted(set(re.findall(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", q)))
    if years:
        lines.append("Years/dates in the question: " + ", ".join(years))

    m = re.search(r"(\d{1,3})\s*marks?", low) or re.search(r"\((\d{1,3})\)\s*$", q)
    if m:
        marks = int(m.group(1))
        lines.append(
            f"Marks: {marks}. Rough guide: about {round(marks * 1.8)} minutes and {marks * 40} words "
            "(guide only; adjust to your handwriting speed)."
        )
    return "\n".join(lines)
