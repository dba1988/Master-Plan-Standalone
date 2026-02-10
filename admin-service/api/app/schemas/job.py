"""Job schemas for API request/response."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Available job types."""
    TILE_GENERATION = "tile_generation"
    SVG_IMPORT = "svg_import"
    PUBLISH = "publish"


class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogEntry(BaseModel):
    """Job log entry."""
    timestamp: str
    level: str
    message: str


class JobResponse(BaseModel):
    """Job response schema."""
    id: UUID
    job_type: str
    status: str
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[LogEntry] = []
    project_id: UUID
    version_id: Optional[UUID] = None
    created_by: UUID
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobSummary(BaseModel):
    """Minimal job info for lists."""
    id: UUID
    job_type: str
    status: str
    progress: int
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobCreateResponse(BaseModel):
    """Response when starting a job."""
    job_id: UUID
    status: str = "queued"
    message: str = "Job started"
