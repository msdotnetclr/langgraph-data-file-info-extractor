from src.nodes import (
    split_text_into_chunks,
    _make_key,
    _find_match,
    _merge_fields,
    _pick_best_version,
    _value_is_better,
    _field_is_complete,
    _build_context_from_previous,
)


class TestSplitTextIntoChunks:
    def test_basic_splitting(self):
        text = "\n".join(str(i) for i in range(100))
        chunks = split_text_into_chunks(text, lines_per_chunk=30, overlap_lines=5)
        assert len(chunks) == 4
        assert all(isinstance(c, str) for c in chunks)

    def test_single_chunk(self):
        text = "line1\nline2\nline3"
        chunks = split_text_into_chunks(text, lines_per_chunk=100, overlap_lines=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_overlap(self):
        text = "\n".join(str(i) for i in range(20))
        chunks = split_text_into_chunks(text, lines_per_chunk=10, overlap_lines=3)
        lines0 = chunks[0].split("\n")
        lines1 = chunks[1].split("\n")
        assert lines0[-3:] == lines1[:3]

    def test_empty_input(self):
        chunks = split_text_into_chunks("", lines_per_chunk=10, overlap_lines=3)
        assert chunks == [""]

    def test_crlf_normalization(self):
        text = "line1\r\nline2\r\nline3"
        chunks = split_text_into_chunks(text, lines_per_chunk=10, overlap_lines=3)
        assert "\r\n" not in chunks[0]
        assert "line1\nline2\nline3" in chunks[0]

    def test_exact_boundary(self):
        text = "\n".join(str(i) for i in range(15))
        chunks = split_text_into_chunks(text, lines_per_chunk=5, overlap_lines=0)
        assert len(chunks) == 3
        for c in chunks:
            assert len(c.split("\n")) == 5


class TestMakeKey:
    def test_key_with_index_is_group_plus_index(self):
        f = {"field_group": "header", "field_name": "RecordType", "field_index": 2}
        key = _make_key(f)
        assert key == ("header", 2)

    def test_key_without_index_is_group_plus_name(self):
        f = {"field_group": "header", "field_name": "RecordType"}
        key = _make_key(f)
        assert key == ("header", "recordtype")

    def test_different_index_different_key(self):
        f1 = {"field_group": "content", "field_name": "Amount", "field_index": 0}
        f2 = {"field_group": "content", "field_name": "Amount", "field_index": 5}
        assert _make_key(f1) != _make_key(f2)

    def test_name_case_insensitive_when_no_index(self):
        f1 = {"field_group": "header", "field_name": "RECORDTYPE"}
        f2 = {"field_group": "header", "field_name": "recordtype"}
        assert _make_key(f1) == _make_key(f2)

    def test_name_case_irrelevant_when_index_present(self):
        f1 = {"field_group": "header", "field_name": "RECORDTYPE", "field_index": 0}
        f2 = {"field_group": "header", "field_name": "recordtype", "field_index": 0}
        assert _make_key(f1) == _make_key(f2)

    def test_name_stripped(self):
        f = {"field_group": "header", "field_name": "  RecordType  "}
        key = _make_key(f)
        assert key[1] == "recordtype"


class TestFindMatch:
    def test_exact_key_match(self):
        merged = [
            {"field_group": "header", "field_name": "RecordType", "field_index": 0},
            {"field_group": "header", "field_name": "Date", "field_index": 1},
        ]
        new = {"field_group": "header", "field_name": "RecordType", "field_index": 0}
        idx = _find_match(merged, new, _make_key(new))
        assert idx == 0

    def test_different_index_no_match(self):
        merged = [
            {"field_group": "header", "field_name": "RecordType", "field_index": 0},
        ]
        new = {"field_group": "header", "field_name": "RecordType", "field_index": 5}
        idx = _find_match(merged, new, _make_key(new))
        assert idx is None

    def test_no_match(self):
        merged = [
            {"field_group": "header", "field_name": "RecordType"},
        ]
        new = {"field_group": "header", "field_name": "Date"}
        idx = _find_match(merged, new, _make_key(new))
        assert idx is None

    def test_different_group_same_name_no_match(self):
        merged = [
            {"field_group": "header", "field_name": "ID"},
        ]
        new = {"field_group": "content", "field_name": "ID"}
        idx = _find_match(merged, new, _make_key(new))
        assert idx is None


class TestMergeFields:
    def test_no_duplicates(self):
        existing = [{"field_group": "header", "field_name": "A", "field_index": 0}]
        new = [{"field_group": "header", "field_name": "B", "field_index": 1}]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 2
        assert warnings == []

    def test_duplicate_merged_same_index(self):
        existing = [{"field_group": "header", "field_name": "A", "field_index": 0, "data_type": "string"}]
        new = [{"field_group": "header", "field_name": "A", "field_index": 0, "description": "hello"}]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 1
        assert result[0]["description"] == "hello"
        assert warnings == []

    def test_different_index_keeps_both(self):
        existing = [{"field_group": "content", "field_name": "Amount", "field_index": 5, "data_type": "integer"}]
        new = [{"field_group": "content", "field_name": "Amount", "field_index": 3, "description": "Total amount"}]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 2

    def test_overlap_with_same_indices_dedup(self):
        existing = [
            {"field_group": "content", "field_name": "FirstName", "field_index": 0, "data_type": "string", "description": "First name"},
            {"field_group": "content", "field_name": "LastName", "field_index": 1, "data_type": "string", "description": "Last name"},
            {"field_group": "content", "field_name": "PartialField", "field_index": 2, "data_type": "string", "description": "Partia"},
        ]
        new_from_overlap = [
            {"field_group": "content", "field_name": "FirstName", "field_index": 0, "data_type": "string", "description": "First name"},
            {"field_group": "content", "field_name": "LastName", "field_index": 1, "data_type": "string", "description": "Last name"},
            {"field_group": "content", "field_name": "PartialField", "field_index": 2, "data_type": "string", "description": "Partial field description goes here"},
        ]
        result, warnings = _merge_fields(existing, new_from_overlap)
        assert len(result) == 3
        assert result[2]["description"] == "Partial field description goes here"
        assert warnings == []

    def test_name_conflict_same_group_different_index_renames_and_warns(self):
        existing = [
            {"field_group": "content", "field_name": "FILLER", "field_index": 2, "data_type": "string", "description": "Padding field 1"},
        ]
        new = [
            {"field_group": "content", "field_name": "FILLER", "field_index": 3, "data_type": "string", "description": "Padding field 2"},
        ]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 2
        assert result[0]["field_name"] == "FILLER"
        assert result[1]["field_name"] == "FILLER(2)"
        assert len(warnings) == 1
        assert "Duplicate field name 'FILLER'" in warnings[0]
        assert "renamed to 'FILLER(2)'" in warnings[0]

    def test_name_conflict_multiple_renames_increments(self):
        existing = [
            {"field_group": "content", "field_name": "FILLER", "field_index": 2},
            {"field_group": "content", "field_name": "FILLER(2)", "field_index": 3},
            {"field_group": "content", "field_name": "FILLER(3)", "field_index": 4},
        ]
        new = [
            {"field_group": "content", "field_name": "FILLER", "field_index": 5},
        ]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 4
        assert result[3]["field_name"] == "FILLER(4)"

    def test_name_conflict_different_group_no_conflict(self):
        existing = [
            {"field_group": "header", "field_name": "ID", "field_index": 0},
        ]
        new = [
            {"field_group": "content", "field_name": "ID", "field_index": 0},
        ]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 2
        assert result[0]["field_name"] == "ID"
        assert result[1]["field_name"] == "ID"
        assert warnings == []

    def test_name_conflict_with_none_index_fallback_key(self):
        existing = [
            {"field_group": "content", "field_name": "Extra"},
        ]
        new = [
            {"field_group": "content", "field_name": "Extra", "field_index": 0},
        ]
        result, warnings = _merge_fields(existing, new)
        assert len(result) == 2
        assert warnings != []


class TestPickBestVersion:
    def test_keeps_existing_description_when_longer(self):
        a = {"description": "This is a very long and detailed description of the field"}
        b = {"description": "Short desc"}
        result = _pick_best_version(a, b)
        assert result["description"] == a["description"]

    def test_takes_new_description_when_longer(self):
        a = {"description": "Short"}
        b = {"description": "This is much longer and more detailed"}
        result = _pick_best_version(a, b)
        assert result["description"] == b["description"]

    def test_keeps_existing_index_when_new_is_none(self):
        a = {"field_index": 5}
        b = {"field_index": None}
        result = _pick_best_version(a, b)
        assert result["field_index"] == 5

    def test_takes_new_index_when_existing_is_none(self):
        a = {"field_index": None}
        b = {"field_index": 3}
        result = _pick_best_version(a, b)
        assert result["field_index"] == 3

    def test_keeps_existing_name_when_both_have_value(self):
        a = {"field_name": "OriginalName"}
        b = {"field_name": "NewName"}
        result = _pick_best_version(a, b)
        assert result["field_name"] == "OriginalName"

    def test_keeps_existing_name_when_new_is_empty(self):
        a = {"field_name": "ValidName"}
        b = {"field_name": ""}
        result = _pick_best_version(a, b)
        assert result["field_name"] == "ValidName"

    def test_takes_new_name_when_existing_is_empty(self):
        a = {"field_name": ""}
        b = {"field_name": "ValidName"}
        result = _pick_best_version(a, b)
        assert result["field_name"] == "ValidName"

    def test_preserves_conflict_suffix(self):
        a = {"field_name": "FILLER(2)"}
        b = {"field_name": "FILLER"}
        result = _pick_best_version(a, b)
        assert result["field_name"] == "FILLER(2)"

    def test_takes_new_data_type_when_existing_is_empty(self):
        a = {"data_type": ""}
        b = {"data_type": "string (50)"}
        result = _pick_best_version(a, b)
        assert result["data_type"] == "string (50)"


class TestValueIsBetter:
    def test_none_not_better(self):
        assert _value_is_better(None, "existing") is False

    def test_empty_string_not_better(self):
        assert _value_is_better("  ", "existing") is False

    def test_incoming_better_than_none(self):
        assert _value_is_better("new", None) is True

    def test_incoming_better_than_empty(self):
        assert _value_is_better("new", "") is True

    def test_longer_better_than_shorter(self):
        assert _value_is_better("long_fmt", "short") is True

    def test_shorter_not_better_than_longer(self):
        assert _value_is_better("short", "long_fmt") is False


class TestFieldIsComplete:
    def test_complete_field(self):
        f = {"field_name": "ID", "data_type": "integer", "description": "Identifier", "field_index": 0}
        assert _field_is_complete(f) is True

    def test_missing_name(self):
        f = {"data_type": "integer", "description": "Desc", "field_index": 0}
        assert _field_is_complete(f) is False

    def test_missing_type(self):
        f = {"field_name": "ID", "description": "Desc", "field_index": 0}
        assert _field_is_complete(f) is False

    def test_missing_description(self):
        f = {"field_name": "ID", "data_type": "integer", "field_index": 0}
        assert _field_is_complete(f) is False

    def test_index_none(self):
        f = {"field_name": "ID", "data_type": "integer", "description": "Desc", "field_index": None}
        assert _field_is_complete(f) is False


class TestBuildContextFromPrevious:
    def test_empty_fields(self):
        result = _build_context_from_previous([])
        assert "No fields have been extracted yet" in result

    def test_includes_last_field_info(self):
        fields = [
            {"field_group": "header", "field_name": "RecordType", "field_index": 0, "data_type": "string (2)", "description": "Record type indicator"},
        ]
        result = _build_context_from_previous(fields)
        assert "1 fields have been extracted" in result
        assert "RecordType" in result

    def test_marks_incomplete(self):
        fields = [
            {"field_group": "content", "field_name": "Name", "field_index": 0, "data_type": "string", "description": "Full name"},
            {"field_group": "content", "field_name": "Age", "field_index": 1},
        ]
        result = _build_context_from_previous(fields)
        assert "[INCOMPLETE" in result
        assert "WARNING" in result

    def test_shows_last_10_fields(self):
        fields = [
            {"field_group": "content", "field_name": f"F{i}", "field_index": i, "data_type": "string", "description": f"Field {i}"}
            for i in range(15)
        ]
        result = _build_context_from_previous(fields)
        assert "Last 10 extracted fields" in result
        assert "F5" in result
        assert "F14" in result
        assert "F0" not in result
