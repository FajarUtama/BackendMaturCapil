from pydantic import BaseModel, Field


class ComplaintCreateJson(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    category_id: str
    priority: str = "Sedang"
    latitude: float
    longitude: float
    address: str = Field(min_length=5, max_length=500)
    photos: list[str] | None = None


class ComplaintStatusUpdate(BaseModel):
    status: str
    note: str | None = None


class ComplaintCloseRequest(BaseModel):
    resolution_note: str = Field(min_length=5)
    evidence_after_photos: list[str] | None = None


class ChatCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
