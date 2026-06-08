from pydantic import BaseModel, Field


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

