from typing import Annotated, TypedDict, List, Dict, Tuple, Any, Optional
import operator


class AgentState(TypedDict, total=False):
    spec_file: str

    spec_file_size: int

    chunk_ranges: List[Tuple[int, int]]

    current_chunk_index: int

    partial_fields: List[Dict[str, Any]]

    extracted_data: Annotated[List[Dict[str, Any]], operator.add]

    file_metadata: Dict[str, Any]

    fields: List[Dict[str, Any]]

    domain_instructions: str

    warnings: Annotated[List[str], operator.add]

    session_id: str

    domain: str

    source: str

    review_decision: str

    human_feedback: str

    feedback_rounds: Annotated[List[Dict[str, Any]], operator.add]

    approved: bool

    status: str
