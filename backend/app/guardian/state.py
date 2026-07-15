from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class InvestigationState(str, Enum):
    PENDING = "pending"
    GATHERING = "gathering"
    ANALYZING = "analyzing"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


InvestigationStatus = InvestigationState

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class InvestigationTrigger(BaseModel):
    type: str
    source: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Evidence(BaseModel):
    source: str
    summary: str
    data: Any
    gathered_at: datetime = Field(default_factory=datetime.utcnow)
    relavance: str = "unknown"


class RootCause(BaseModel):
    summary: str
    confidence: float
    category: str
    affected_resources: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class Remediation(BaseModel):
    action: str
    type: str
    command: str | None = None
    risk_level: str = "low"
    requires_approval: bool = True
    approved: bool = False
    executed: bool = False
    result: str | None = None



class GuardianState(BaseModel):

    investigation_id: str = ""
    status: InvestigationState = InvestigationState.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None

    trigger: InvestigationTrigger | None = None

    namespace: str | None = None
    resource_kind: str | None = None
    resource_name: str | None = None

    evidence: list[Evidence] = Field(default_factory=list)

    severity: Severity = Severity.INFO
    root_causes: list[RootCause] = Field(default_factory=list)
    summary: str = ""

    remediations: list[Remediation] = Field(default_factory=list)

    error: str | None = None
    nodes_visited: list[str] = Field(default_factory=list)