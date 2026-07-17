"""Helpers compartidos entre módulos."""

from pathlib import Path

from fastapi import HTTPException, status

from app.models.user import User

ALLOWED_EXTENSIONS = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".txt", ".csv",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".mp4", ".webm", ".avi",
    ".zip", ".rar",
})


def student_display_name(user: User) -> str:
    parts = [user.name, user.first_last_name, user.second_last_name or ""]
    return " ".join(x for x in parts if x).strip().upper()


def validate_file_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if not ext or ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Extensiones aceptadas: {allowed}",
        )
    return ext
