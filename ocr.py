"""Reads text from a photo of a handwritten answer.
First choice: a Groq vision model. Fallback: Tesseract OCR (weaker on handwriting)."""
import base64
import io
import re
import time

from config import get_api_key, get_vision_model

PROMPT = (
    "This is a photo of a handwritten exam answer. Transcribe it exactly as written, in reading order. "
    "Keep the original spelling, wording and paragraph breaks. Do not correct, improve or summarise anything. "
    "Write [illegible] for any word you cannot read. Output ONLY the transcription."
)


def _prepare(image_bytes: bytes, max_side: int = 1400):
    """Fix rotation, shrink and compress the photo. Returns (jpeg_bytes, PIL image)."""
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue(), img


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def _short(e: Exception) -> str:
    return str(e).replace("\n", " ")[:200]


def _is_rate_limit(e: Exception) -> bool:
    msg = str(e).lower()
    return "rate_limit" in msg or "429" in msg or "ratelimit" in type(e).__name__.lower()


def _vision_ocr(jpeg_bytes: bytes, progress) -> str:
    import litellm

    b64 = base64.b64encode(jpeg_bytes).decode()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }
    ]
    model = "groq/" + get_vision_model()
    last = RuntimeError("Vision OCR did not run")
    # First try without "thinking" (faster, fewer tokens); if the model rejects that setting, retry plainly.
    for extra in ({"reasoning_effort": "none"}, {}):
        for attempt in (1, 2):
            try:
                resp = litellm.completion(
                    model=model, messages=messages, api_key=get_api_key(),
                    max_tokens=1500, temperature=0.1, **extra,
                )
                return _strip_think(resp.choices[0].message.content or "")
            except Exception as e:
                last = e
                if _is_rate_limit(e) and attempt == 1:
                    progress("Groq speed limit reached. Waiting 65 seconds, then trying again...")
                    time.sleep(65)
                    continue
                break
    raise last


def _tesseract(img) -> str:
    import pytesseract

    return pytesseract.image_to_string(img)


def extract_text(image_bytes: bytes, progress=None):
    """Returns (text, method, note)."""
    progress = progress or (lambda msg: None)
    try:
        jpeg, img = _prepare(image_bytes)
    except Exception as e:
        return "", "none", f"Could not open the image: {_short(e)}"

    note = ""
    try:
        text = _vision_ocr(jpeg, progress).strip()
        if text:
            return text, f"AI vision ({get_vision_model()})", ""
        note = "The AI vision model returned nothing, so Tesseract was used."
    except Exception as e:
        note = f"AI vision failed ({_short(e)}), so Tesseract was used."

    try:
        return _tesseract(img).strip(), "Tesseract (rough on handwriting)", note
    except Exception as e:
        return "", "none", f"{note} Tesseract also failed: {_short(e)}"
