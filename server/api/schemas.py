from pydantic import BaseModel, Field
from typing import Optional


class DomainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ContentUpdate(BaseModel):
    content: str


class DomainInfo(BaseModel):
    name: str
    source_count: int
    has_instructions: bool


class SourceInfo(BaseModel):
    name: str
    domain: str
    has_spec: bool


class InputTreeNode(BaseModel):
    domain: str
    sources: list[str]


class OKResponse(BaseModel):
    ok: bool = True


class ContentResponse(BaseModel):
    content: str


class SessionCreate(BaseModel):
    domain: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)


class FeedbackRound(BaseModel):
    round: int
    timestamp: str
    feedback_text: str
    decision: str


class SessionInfo(BaseModel):
    session_id: str
    domain: str
    source: str
    status: str
    created_at: str
    last_modified_at: str
    feedback_rounds: list[FeedbackRound] = []
    accumulated_instructions: str = ""


class ReviewSubmit(BaseModel):
    decision: str
    feedback: str = ""


class ExtractionResult(BaseModel):
    file_metadata: dict
    fields: list[dict]
    warnings: list[str]
    feedback_rounds: list[FeedbackRound] = []


class ReviewData(BaseModel):
    session_id: str
    domain: str
    source: str
    status: str
    result: ExtractionResult
    feedback_rounds: list[FeedbackRound] = []


class VersionEntry(BaseModel):
    version: int
    session_id: str
    created_at: str
    filename: str
    based_on_version: Optional[int] = None
    feedback_rounds: int = 0


class OutputManifest(BaseModel):
    domain: str
    source: str
    latest_version: int
    versions: list[VersionEntry]


class MetadataDiff(BaseModel):
    added: dict = {}
    removed: dict = {}
    changed: dict = {}


class FieldDiffItem(BaseModel):
    key: dict
    changes: dict


class FieldsDiff(BaseModel):
    added: list[dict] = []
    removed: list[dict] = []
    changed: list[FieldDiffItem] = []


class WarningsDiff(BaseModel):
    added: list[str] = []
    removed: list[str] = []


class VersionDiff(BaseModel):
    v1: int
    v2: int
    v1_session_id: str
    v2_session_id: str
    v1_created_at: str
    v2_created_at: str
    file_metadata: MetadataDiff
    fields: FieldsDiff
    warnings: WarningsDiff


class VersionChainItem(BaseModel):
    version: int
    session_id: str
    created_at: str
    feedback_rounds: int
    is_based_on_feedback: bool


class OutputWithVersion(BaseModel):
    version: int
    session_id: str
    created_at: str
    based_on_version: Optional[int] = None
    data: dict
