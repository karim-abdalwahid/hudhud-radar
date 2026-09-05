"""
Utility helpers for Knowledge Base and File Ingestion Security.
Enforces strict Path Traversal prevention and filename sanitization.
"""
from pathlib import Path
import re


def sanitize_safe_filename(name: str, force_md: bool = True) -> str:
    """
    Prevents Path Traversal attacks and normalizes document filenames.
    - Strips directory components and path separators (../, ..\\, etc.)
    - Removes unsafe characters, keeping alphanumeric, underscores, hyphens, and Arabic characters.
    - Ensures valid .md extension if force_md is True.
    """
    # Extract only the base name (prevents ../ and ..\)
    base_name = Path(name).name
    stem = Path(base_name).stem

    # Clean characters: allow only letters, numbers, underscores, hyphens, Arabic Unicode
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-\u0600-\u06FF]', '_', stem)
    clean_stem = clean_stem.strip('_') or "document"

    if force_md:
        return f"{clean_stem}.md"
    return clean_stem
