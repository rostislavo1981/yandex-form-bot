from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_manager
from app.services.excel_service import (
    CatalogImportApplier,
    CatalogImportValidator,
    build_template,
    export_catalogs,
)

router = APIRouter(
    prefix="/api/catalogs",
    tags=["catalogs"],
    dependencies=[Depends(require_manager)],
)


@router.get("/template.xlsx")
async def download_template() -> StreamingResponse:
    """Download an empty catalog import template workbook."""
    buffer = build_template()
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template.xlsx"},
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


@router.post("/import/apply")
async def apply_catalog_import(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Validate and apply uploaded catalog workbook in one transaction."""
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется файл .xlsx",
        )
    content = await file.read()
    validator = CatalogImportValidator(content)
    validation = validator.validate()
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation,
        )
    applier = CatalogImportApplier(session)
    try:
        import_record = await applier.apply(validator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc)},
        ) from exc
    return {
        "id": import_record.id,
        "status": import_record.status,
        "preview": import_record.summary,
        "errors": import_record.errors,
    }


@router.post("/import/{import_id}/apply")
async def apply_existing_catalog_import(
    import_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Apply a previously validated import by id.

    Not implemented in I05; kept for future staged validation flow.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=" staged apply по import_id будет реализован позже",
    )


@router.get("/export.xlsx")
async def export_catalogs_endpoint(
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export current active catalogs to an .xlsx workbook."""
    buffer = await export_catalogs(session)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=catalogs.xlsx"},
    )
