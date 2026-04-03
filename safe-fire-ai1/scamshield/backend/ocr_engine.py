"""
OCR Engine — extracts text from WhatsApp/Telegram screenshots.
Falls back gracefully if Tesseract is not installed.
"""
import base64
import io
import re

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_image(image_base64: str) -> dict:
    """Decode base64 image and run OCR."""
    if not OCR_AVAILABLE:
        return {"text": "", "error": "OCR not available — install Tesseract"}

    try:
        img_bytes = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # Upscale small images for better OCR accuracy
        w, h = img.size
        if w < 800:
            scale = 800 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        text = pytesseract.image_to_string(img, lang="eng")
        text = re.sub(r'\s+', ' ', text).strip()
        return {"text": text, "error": None}

    except Exception as e:
        return {"text": "", "error": str(e)}
