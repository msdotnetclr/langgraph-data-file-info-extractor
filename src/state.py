from typing import Annotated, TypedDict, List, Dict, Tuple, Any
import operator


class AgentState(TypedDict):
    specification_file: str

    chunk_ranges: List[Tuple[int, int]]

    current_chunk_index: int

    partial_fields: List[Dict[str, Any]]

    extracted_data: Annotated[List[Dict[str, Any]], operator.add]

    file_metadata: Dict[str, Any]

    fields: List[Dict[str, Any]]

    domain_instructions: str

    warnings: Annotated[List[str], operator.add]
