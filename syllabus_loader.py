"""Downloads the official CSS syllabus PDF from Google Drive (public link) once."""
import requests

from config import OFFICIAL_PDF, OFFICIAL_SYLLABUS_ID


def ensure_official_syllabus():
    """Returns (ok, message). Does nothing if the file is already downloaded."""
    if OFFICIAL_PDF.exists() and OFFICIAL_PDF.stat().st_size > 10_000:
        return True, "Official CSS syllabus is loaded."
    urls = [
        f"https://drive.google.com/uc?export=download&id={OFFICIAL_SYLLABUS_ID}",
        f"https://drive.usercontent.google.com/download?id={OFFICIAL_SYLLABUS_ID}&export=download&confirm=t",
    ]
    last_error = "unknown error"
    for url in urls:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
            if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                OFFICIAL_PDF.write_bytes(resp.content)
                return True, "Official CSS syllabus downloaded."
            last_error = f"Google Drive returned status {resp.status_code} (not a PDF)."
        except Exception as e:
            last_error = str(e)
    return False, f"Could not download the syllabus: {last_error}"
