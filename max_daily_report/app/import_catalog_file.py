from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.services.excel_service import CatalogImportApplier, CatalogImportValidator


def _read_workbook(path: Path) -> bytes:
    if path.suffix.lower() != ".xlsx":
        raise SystemExit("Требуется файл .xlsx")
    size = path.stat().st_size
    if size > settings.max_catalog_upload_bytes:
        raise SystemExit(
            f"Файл больше допустимых {settings.max_catalog_upload_bytes} байт"
        )
    return path.read_bytes()


async def _apply(path: Path) -> None:
    try:
        validator = CatalogImportValidator(_read_workbook(path))
        validation = validator.validate()
        if not validation["valid"]:
            print(json.dumps(validation, ensure_ascii=False, default=str))
            raise SystemExit(2)

        async with AsyncSessionLocal() as session:
            record = await CatalogImportApplier(session).apply(validator)
        print(
            json.dumps(
                {
                    "id": record.id,
                    "status": record.status,
                    "preview": record.summary,
                    "warnings": validation["warnings"],
                },
                ensure_ascii=False,
                default=str,
            )
        )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Проверить и применить Excel со справочниками"
    )
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    asyncio.run(_apply(args.workbook))


if __name__ == "__main__":
    main()
