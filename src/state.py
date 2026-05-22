from typing import Annotated, TypedDict, List, Dict, Any
import operator


class AgentState(TypedDict):
    raw_specification: str

    chunks: List[str]

    current_chunk_index: int

    partial_fields: List[Dict[str, Any]]

    extracted_data: Annotated[List[Dict[str, Any]], operator.add]

    file_metadata: Dict[str, Any]

    fields: List[Dict[str, Any]]
