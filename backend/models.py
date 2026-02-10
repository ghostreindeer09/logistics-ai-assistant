"""
Pydantic models for request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Request Models ──────────────────────────────────────────────────

class AskRequest(BaseModel):
    document_id: str = Field(..., description="ID of the uploaded document")
    question: str = Field(..., description="Natural language question about the document")


class ExtractRequest(BaseModel):
    document_id: str = Field(..., description="ID of the uploaded document")


# ── Response Models ─────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    num_chunks: int
    message: str


class SourceChunk(BaseModel):
    text: str
    chunk_index: int
    similarity_score: float


class AskResponse(BaseModel):
    answer: str
    confidence_score: float
    sources: List[SourceChunk]
    guardrail_triggered: bool
    guardrail_message: Optional[str] = None


class ShipmentData(BaseModel):
    shipment_id: Optional[str] = None
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    pickup_datetime: Optional[str] = None
    delivery_datetime: Optional[str] = None
    equipment_type: Optional[str] = None
    mode: Optional[str] = None
    rate: Optional[str] = None
    currency: Optional[str] = None
    weight: Optional[str] = None
    carrier_name: Optional[str] = None


class ExtractResponse(BaseModel):
    document_id: str
    shipment_data: ShipmentData
    confidence_score: float
    extraction_notes: List[str]
