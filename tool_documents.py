"""Tools that let agents read the student's uploaded syllabus / past papers."""
from pathlib import Path

from crewai.tools import tool

from config import MAX_TOOL_CHARS, UPLOAD_DIR, truncate

_CACHE = {}


def _extract_text(path: Path) -> str:
    key = f"{path}:{path.stat().st_mtime}"
    if key in _CACHE:
        return _CACHE[key]
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader  # imported here so a missing package cannot crash startup

        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    _CACHE[key] = text
    return text


@tool("List Uploaded Files")
def list_uploaded_files(kind: str = "all") -> str:
    """List files the student uploaded. kind must be 'syllabus', 'paper' (past papers) or 'all'."""
    files = sorted(p.name for p in UPLOAD_DIR.iterdir() if p.is_file())
    if kind in ("syllabus", "paper"):
        files = [f for f in files if f.startswith(kind + "__")]
    if not files:
        return "No uploaded files found. Use the Web Search tool instead."
    return "\n".join(files)


@tool("Read Uploaded File")
def read_uploaded_file(filename: str, part: int = 1) -> str:
    """Read text from an uploaded file. Long files are split in parts; use part=1, 2, 3..."""
    path = UPLOAD_DIR / Path(filename).name
    if not path.exists():
        return f"File not found: {filename}. Call List Uploaded Files first."
    try:
        text = _extract_text(path).strip()
    except Exception as e:
        return f"Could not read {filename}: {e}"
    if not text:
        return "No readable text found (the PDF may be a scanned image)."
    total = max(1, -(-len(text) // MAX_TOOL_CHARS))
    part = max(1, min(int(part), total))
    chunk = text[(part - 1) * MAX_TOOL_CHARS : part * MAX_TOOL_CHARS]
    return f"[{path.name} - part {part} of {total}]\n{chunk}"


@tool("Search Uploaded Files")
def search_uploaded_files(keyword: str) -> str:
    """Find lines containing a keyword across all uploaded files. Good for counting how often a topic appears."""
    hits = []
    for path in sorted(UPLOAD_DIR.iterdir()):
        if not path.is_file():
            continue
        try:
            text = _extract_text(path)
        except Exception:
            continue
        for line in text.splitlines():
            if keyword.lower() in line.lower() and line.strip():
                hits.append(f"[{path.name}] {line.strip()}")
    if not hits:
        return f"No lines contain '{keyword}'."
    return truncate(f"{len(hits)} matching lines (showing first ones):\n" + "\n".join(hits[:40]))
