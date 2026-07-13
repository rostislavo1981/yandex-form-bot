from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CatalogItem(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class CatalogItemWithSymbol(BaseModel):
    id: int
    code: str
    name: str
    symbol: str

    model_config = ConfigDict(from_attributes=True)


class CatalogListResponse(BaseModel):
    items: list[CatalogItem]
    total: int


class UnitListResponse(BaseModel):
    items: list[CatalogItemWithSymbol]
    total: int
