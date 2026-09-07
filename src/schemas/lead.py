"""
Pydantic schemas for Lead entity.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class LeadBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    source: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=1000)
    budget: Optional[float] = None
    currency: str = "USD"
    skills: list[str] = Field(default_factory=list)
    category: Optional[str] = None
    finder_score: Optional[float] = None
    intelligence_score: Optional[float] = None


class LeadCreate(LeadBase):
    external_id: Optional[str] = None
    client_id: Optional[str] = None
    status: str = "discovered"
    raw_data: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    skills: Optional[list[str]] = None
    finder_score: Optional[float] = None
    intelligence_score: Optional[float] = None
    status: Optional[str] = None
    client_id: Optional[str] = None


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: Optional[str] = None
    status: str
    content_hash: str
    client_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
