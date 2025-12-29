import os
from typing import Optional
from pypdf import PdfReader
from PIL import Image
import pytesseract

class OCRService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extracts text from a given file (PDF or Image).
        Autodetects format based on extension.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".pdf":
                return OCRService._extract_from_pdf(file_path)
            elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
                return OCRService._extract_from_image(file_path)
            else:
                return f"Unsupported file format: {ext}"
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    @staticmethod
    def _extract_from_pdf(path: str) -> str:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            extract = page.extract_text()
            if extract:
                text += extract + "\n"
        return text

    @staticmethod
    def _extract_from_image(path: str) -> str:
        # Assumes tesseract is in PATH or configured
        # On Windows, you might need: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        image = Image.open(path)
        return pytesseract.image_to_string(image)
