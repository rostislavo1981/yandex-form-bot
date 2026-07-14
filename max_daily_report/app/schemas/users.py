from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    max_user_id: str
    full_name: str
    role: str
    active: bool

    model_config = ConfigDict(from_attributes=True)
