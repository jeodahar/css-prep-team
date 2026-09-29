"""Finds and reads one subject's section inside the official CSS syllabus PDF."""
import re

from crewai.tools import tool

from config import DOC_CHUNK_CHARS, OFFICIAL_PDF

# Words that may appear in the syllabus for each subject (used to locate its section).
ALIASES = {
    "essay": ["essay"],
    "precis & composition": ["precis and composition", "precis", "english (precis"],
    "general science & ability (gsa)": ["general science and ability", "general science"],
    "pakistan affairs": ["pakistan affairs"],
    "current affairs": ["current affairs"],
    "islamic studies": ["islamic studies"],
    "political science i": ["political science"],
    "political science ii": ["political science"],
    "gender studies": ["gender studies"],
    "criminology": ["criminology"],
    "history of indo-pak": ["history of indo-pak", "history of indo pak", "indo-pak"],
    "sindhi": ["sindhi"],
}
KEYWORDS = ("marks", "paper", "syllabus", "objective", "introduction", "outline", "topics", "part")

_STATE = {"hint": ""}
_CACHE = {}


def set_syllabus_hint(text: str) -> None:
    """Optional heading typed by the student if the automatic search picks the wrong place."""
    _STATE["hint"] = (text or "").strip()


def _pattern(alias: str):
    parts = [r"(?:and|&)" if tok.lower() == "and" else re.escape(tok) for tok in alias.split()]
    return re.compile(r"[\s\-\u2013]+".join(parts), re.I)


def _load_text() -> str:
    if not OFFICIAL_PDF.exists():
        return ""
    key = str(OFFICIAL_PDF.stat().st_mtime)
    if key in _CACHE:
        return _CACHE[key]
    from pypdf import PdfReader  # imported here so a missing package cannot crash startup

    reader = PdfReader(str(OFFICIAL_PDF))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    _CACHE.clear()
    _CACHE[key] = text
    return text


def _find_start(subject: str):
    text = _load_text()
    if not text:
        return None, None
    name = subject.lower().strip()
    aliases = [_STATE["hint"]] if _STATE["hint"] else ALIASES.get(name, [name])
    patterns = [_pattern(a) for a in aliases]
    others = [_pattern(a) for k, v in ALIASES.items() if k != name for a in v if a not in aliases]
    best = None
    for pat in patterns:
        for m in pat.finditer(text):
            ls = text.rfind("\n", 0, m.start()) + 1
            le = text.find("\n", m.end())
            le = len(text) if le == -1 else le
            line = text[ls:le].strip()
            window = text[ls : ls + 1500].lower()
            score = 0
            if len(line) <= 90:
                score += 3
            if line.isupper():
                score += 2
            score += min(4, sum(1 for k in KEYWORDS if k in window))
            nearby = text[ls : ls + 400]
            score -= min(6, 2 * sum(1 for op in others if op.search(nearby)))
            cand = (score, ls)
            if best is None or cand >= best:  # on a tie, prefer the later place (skips the contents page)
                best = cand
    return text, (best[1] if best else None)


def read_section(subject: str, part: int = 1) -> str:
    text, start = _find_start(subject)
    if text is None:
        return "The official syllabus is not available. Use Web Search instead."
    if start is None:
        return f"Section for '{subject}' not found in the official syllabus. Use Web Search instead."
    part = max(1, min(int(part), 4))
    begin = start + (part - 1) * DOC_CHUNK_CHARS
    chunk = text[begin : begin + DOC_CHUNK_CHARS].strip()
    if not chunk:
        return "No more text after this point."
    return f"[Official CSS syllabus - {subject}, part {part}]\n{chunk}"


def preview_section(subject: str) -> str:
    """Used by the app to show what the agents will read."""
    return read_section(subject, 1)


@tool("Read Official Syllabus")
def read_official_syllabus(subject: str, part: int = 1) -> str:
    """Read the section of the official FPSC CSS syllabus for one subject (for example 'Pakistan Affairs').
    Use part=2 or 3 only if the previous part was cut off."""
    return read_section(subject, part)
