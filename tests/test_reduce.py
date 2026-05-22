from src.nodes import reduce_results


class TestReduceResults:
    def test_empty_input(self):
        state = {
            "extracted_data": [],
            "partial_fields": [],
        }
        result = reduce_results(state)
        assert result["file_metadata"] == {
            "file_format": None,
            "encoding": None,
            "delimiter": None,
            "naming_convention": None,
        }
        assert result["fields"] == []

    def test_merges_file_metadata_across_chunks(self):
        state = {
            "extracted_data": [
                {"file_metadata": {"file_format": "CSV", "encoding": None, "delimiter": None, "naming_convention": None}},
                {"file_metadata": {"file_format": None, "encoding": "UTF-8", "delimiter": "Comma", "naming_convention": None}},
            ],
            "partial_fields": [],
        }
        result = reduce_results(state)
        assert result["file_metadata"]["file_format"] == "CSV"
        assert result["file_metadata"]["encoding"] == "UTF-8"
        assert result["file_metadata"]["delimiter"] == "Comma"

    def test_sorts_header_before_content(self):
        state = {
            "extracted_data": [],
            "partial_fields": [
                {"field_group": "content", "field_name": "Name", "field_index": 0},
                {"field_group": "header", "field_name": "RecordType", "field_index": 0},
                {"field_group": "header", "field_name": "Date", "field_index": 1},
                {"field_group": "content", "field_name": "Age", "field_index": 1},
            ],
        }
        result = reduce_results(state)
        groups = [f["field_group"] for f in result["fields"]]
        assert groups == ["header", "header", "content", "content"]

    def test_sorts_by_index_within_group(self):
        state = {
            "extracted_data": [],
            "partial_fields": [
                {"field_group": "content", "field_name": "C", "field_index": 2},
                {"field_group": "content", "field_name": "A", "field_index": 0},
                {"field_group": "content", "field_name": "B", "field_index": 1},
            ],
        }
        result = reduce_results(state)
        names = [f["field_name"] for f in result["fields"]]
        assert names == ["A", "B", "C"]

    def test_none_index_at_end(self):
        state = {
            "extracted_data": [],
            "partial_fields": [
                {"field_group": "content", "field_name": "B", "field_index": 1},
                {"field_group": "content", "field_name": "A", "field_index": 0},
                {"field_group": "content", "field_name": "Unknown", "field_index": None},
            ],
        }
        result = reduce_results(state)
        names = [f["field_name"] for f in result["fields"]]
        assert names == ["A", "B", "Unknown"]

    def test_normalizes_group_names(self):
        state = {
            "extracted_data": [],
            "partial_fields": [
                {"field_group": "Header Record", "field_name": "Type", "field_index": 0},
                {"field_group": "Content Area", "field_name": "Name", "field_index": 0},
            ],
        }
        result = reduce_results(state)
        groups = [f["field_group"] for f in result["fields"]]
        assert groups == ["header", "content"]

    def test_other_group_at_end(self):
        state = {
            "extracted_data": [],
            "partial_fields": [
                {"field_group": "header", "field_name": "Type", "field_index": 0},
                {"field_group": "trailer", "field_name": "Checksum", "field_index": 0},
                {"field_group": "content", "field_name": "Name", "field_index": 0},
            ],
        }
        result = reduce_results(state)
        groups = [f["field_group"] for f in result["fields"]]
        assert groups == ["header", "content", "trailer"]
