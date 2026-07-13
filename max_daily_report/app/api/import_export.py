from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services.excel_service import CatalogImportValidator

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


@router.get("/template.xlsx")
async def download_template() -> dict:
    """Return a download URL placeholder; actual file served by static handler."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Скачивание шаблона будет реализовано в I05",
    )


@router.post("/import/validate")
async def validate_catalog_import(
    file: UploadFile = File(...),
) -> dict:
    """Validate uploaded catalog workbook without applying changes."""
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется файл .xlsx",
        )
    content = await file.read()
    validator = CatalogImportValidator(content)
    return validator.validate()
