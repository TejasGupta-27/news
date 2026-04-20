"""Utilities for processing files and extracting text."""

import io
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document


def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract text from various file formats.
    
    Supported formats: .txt, .pdf, .docx
    
    Args:
        file_content: Raw file bytes
        filename: Original filename to determine format
        
    Returns:
        Extracted text
        
    Raises:
        ValueError: If file format is not supported
        Exception: If extraction fails
    """
    file_ext = Path(filename).suffix.lower()
    
    if file_ext == ".txt":
        return file_content.decode("utf-8", errors="ignore").strip()
    
    elif file_ext == ".pdf":
        try:
            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {e}")
    
    elif file_ext == ".docx":
        try:
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
            return text.strip()
        except Exception as e:
            raise ValueError(f"Failed to extract text from DOCX: {e}")
    
    else:
        raise ValueError(
            f"Unsupported file format: {file_ext}. "
            "Supported formats: .txt, .pdf, .docx"
        )


def is_supported_file_format(filename: str) -> bool:
    """Check if file format is supported."""
    return Path(filename).suffix.lower() in {".txt", ".pdf", ".docx"}
