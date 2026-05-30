from datetime import datetime

from pydantic import BaseModel


class SpamKeywordResponse(BaseModel):
    id: int
    keyword: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KeywordCreateRequest(BaseModel):
    keyword: str


class KeywordToggleRequest(BaseModel):
    is_active: bool
