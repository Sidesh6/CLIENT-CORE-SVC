"""
Pydantic schemas for Client CRM entity.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ClientProfileBase(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None


class ClientProfileCreate(ClientProfileBase):
    confidence_score: float = 1.0
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClientProfileResponse(ClientProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    confidence_score: float
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ClientProfileListResponse(BaseModel):
    items: list[ClientProfileResponse]
    total: int
    page: int
    page_size: int
