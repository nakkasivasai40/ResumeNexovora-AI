import os
import re
import zipfile
import xml.etree.ElementTree as ET

def extract_text_from_file(filepath):
    """
    Extracts text cleanly from PDF, DOCX, or TXT files.
    Includes built-in fallbacks so it never crashes even if optional packages are missing.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if ext == ".docx":
        try:
            import docx
            doc = docx.Document(filepath)
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells if cell.text.strip()))
            return "\n".join(parts)
        except Exception:
            try:
                with zipfile.ZipFile(filepath) as z:
                    xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                texts = [elem.text for elem in tree.iter() if elem.text]
                return " ".join(texts)
            except Exception:
                return ""

    if ext == ".pdf":
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception:
            pass

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if text.strip():
                return text
        except Exception:
            pass

        try:
            with open(filepath, "rb") as f:
                raw = f.read().decode("latin-1", errors="ignore")
            readable = re.findall(r"[A-Za-z0-9@.,:;+\-/()\s]{6,}", raw)
            return " ".join(readable[:500])
        except Exception:
            return ""

    return ""
