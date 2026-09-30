"""Pure logic for weak areas and progress (no Streamlit, no AI). Easy to test."""
import re
from collections import Counter

# key: (label, max points). The assessor scores each on this 100-point rubric.
CRITERIA = {
    "understanding": ("Understanding the question", 20),
    "content": ("Content accuracy and depth", 30),
    "analysis": ("Analysis and arguments", 20),
    "structure": ("Structure and coherence", 15),
    "language": ("Language and expression", 15),
}
WEAK_BELOW = 0.6  # a criterion below 60% counts as a weak area

_DATA_RE = re.compile(r"^\W*DATA:\s*(.+)$", re.I | re.M)


def _num(text):
    m = re.search(r"\d+(?:\.\d+)?", str(text))
    return float(m.group()) if m else None


def parse_assessment(report: str, total=None):
    """Splits the assessor's report into (clean_report, data).
    data = {"marks": float|None, "criteria": {key: points}, "weak_topics": [str]}"""
    report = report or ""
    data = {"marks": None, "criteria": {}, "weak_topics": []}
    clean = report
    m = _DATA_RE.search(report)
    if m:
        clean = (report[: m.start()] + report[m.end():]).strip()
        for part in m.group(1).split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip().lower().strip("*` ")
            value = value.strip().strip("*` ")
            if key == "marks":
                data["marks"] = _num(value)
            elif key in CRITERIA:
                n = _num(value)
                if n is not None:
                    data["criteria"][key] = min(max(n, 0.0), float(CRITERIA[key][1]))
            elif key == "weak_topics":
                topics = [t.strip(" *`") for t in re.split(r"[|,]", value) if t.strip(" *`")]
                data["weak_topics"] = [t for t in topics if t.lower() not in ("none", "n/a")][:5]
    if total:
        if data["marks"] is None:
            found = re.search(r"(\d+(?:\.\d+)?)\s*/\s*%d\b" % int(total), clean)
            if found:
                data["marks"] = float(found.group(1))
        if data["marks"] is None and len(data["criteria"]) == len(CRITERIA):
            data["marks"] = round(sum(data["criteria"].values()) / 100 * total, 1)
        if data["marks"] is not None:
            data["marks"] = min(max(data["marks"], 0.0), float(total))
    return clean, data


def item_percent(item):
    marks, total = item.get("marks"), item.get("total")
    if marks is None or not total:
        return None
    return round(100.0 * marks / total, 1)


def _mean(values):
    return sum(values) / len(values) if values else None


def summarize(history, subject=None):
    """Statistics over saved assessments (optionally for one subject)."""
    items = [h for h in history if not subject or h.get("subject") == subject]
    scored = [(h, item_percent(h)) for h in items]
    scored = [(h, p) for h, p in scored if p is not None]
    percents = [p for _, p in scored]

    by_subject = {}
    for h, p in scored:
        by_subject.setdefault(h.get("subject", "?"), []).append(p)

    criteria = {}
    for key, (label, mx) in CRITERIA.items():
        vals = [h["criteria"][key] / mx * 100 for h in items if key in (h.get("criteria") or {})]
        criteria[key] = {
            "label": label,
            "avg": _mean(vals),
            "n": len(vals),
            "weak_count": sum(1 for v in vals if v < WEAK_BELOW * 100),
        }

    topic_counter, first_seen = Counter(), {}
    for h in items:
        for t in h.get("weak_topics") or []:
            k = t.strip().lower()
            if k:
                topic_counter[k] += 1
                first_seen.setdefault(k, t.strip())

    return {
        "count": len(items),
        "scored": len(scored),
        "avg": _mean(percents),
        "latest": percents[-1] if percents else None,
        "best": max(percents) if percents else None,
        "trend": [(h.get("time", ""), p) for h, p in scored],
        "subjects": {s: _mean(v) for s, v in by_subject.items()},
        "criteria": criteria,
        "topics": [(first_seen[k], c) for k, c in topic_counter.most_common(10)],
    }


def topic_names(topics_md: str, limit: int = 15):
    """Pulls topic names out of the Syllabus Analyst's numbered list (or table)."""
    names = []
    for line in (topics_md or "").splitlines():
        s = line.strip()
        name = None
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or re.match(r"^[\s:\-]*$", "".join(cells)):
                continue
            if cells[0].isdigit() and len(cells) > 1:
                name = cells[1]
            elif cells[0].lower().strip("*") in ("topic", "#", "no", "no.", "sr", "sr."):
                continue
            else:
                name = cells[0]
        else:
            m = re.match(r"^\d+[\.\)]\s+(.*)", s)
            if m:
                name = m.group(1)
        if not name:
            continue
        name = re.sub(r"[*_`]", "", name)
        name = re.split(r"\s+[\u2013\u2014-]\s+|:\s|\s\|\s|\s\(", name)[0].strip()
        if 3 <= len(name) <= 90 and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def study_context_text(history, subjects, topics_by_subject, limit=1800):
    """Compact text for the Study Planner agent: recorded weak areas + topics per subject."""
    parts = []
    for subj in subjects:
        s = summarize(history, subj)
        lines = [f"SUBJECT: {subj}"]
        if s["scored"]:
            lines.append(
                f"Assessments: {s['scored']}, average {s['avg']:.0f}%, latest {s['latest']:.0f}%."
            )
        else:
            lines.append("No assessments yet, so no recorded weak areas.")
        weak = [
            (v["avg"], v["label"], v["weak_count"])
            for v in s["criteria"].values()
            if v["avg"] is not None and v["avg"] < 70
        ]
        weak.sort()
        if weak:
            lines.append(
                "Weak skills (lowest first): "
                + "; ".join(f"{lab} {avg:.0f}% (weak in {n}x)" for avg, lab, n in weak)
            )
        if s["topics"]:
            lines.append("Weak topics (most repeated first): " + "; ".join(f"{t} x{c}" for t, c in s["topics"][:8]))
        topics = topics_by_subject.get(subj)
        if topics:
            lines.append("Syllabus topics: " + "; ".join(topics[:10]))
        parts.append("\n".join(lines))
    return "\n\n".join(parts)[:limit]
