from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorBody


class ApiSuccessResponse(BaseModel):
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)

