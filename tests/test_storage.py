import json
import os
import shutil

import pytest

from src.storage import InputStore, OutputStore, get_input_tree, DATA_ROOT

TEST_INPUT = DATA_ROOT / "input"
TEST_OUTPUT = DATA_ROOT / "output"


@pytest.fixture(autouse=True)
def clean_data():
    for path in (TEST_INPUT, TEST_OUTPUT):
        if path.exists():
            shutil.rmtree(path)
    yield
    for path in (TEST_INPUT, TEST_OUTPUT):
        if path.exists():
            shutil.rmtree(path)


class TestInputStore:
    def test_list_domains_empty(self):
        store = InputStore()
        assert store.list_domains() == []

    def test_create_and_list_domains(self):
        store = InputStore()
        store.create_domain("test-d")
        store.create_domain("alpha")
        domains = store.list_domains()
        assert domains == ["alpha", "test-d"]

    def test_domain_exists(self):
        store = InputStore()
        store.create_domain("test-d")
        assert store.domain_exists("test-d")
        assert not store.domain_exists("nonexistent")

    def test_create_source(self):
        store = InputStore()
        store.create_domain("test-d")
        store.create_source("test-d", "src1")
        assert store.source_exists("test-d", "src1")
        assert store.list_sources("test-d") == ["src1"]

    def test_instructions_read_write(self):
        store = InputStore()
        store.create_domain("test-d")
        assert store.get_instructions("test-d") == ""
        store.save_instructions("test-d", "# Hello\nRules here")
        assert "Hello" in store.get_instructions("test-d")
        assert store.has_instructions("test-d")
        assert not store.has_instructions("nonexistent")

    def test_spec_read_write(self):
        store = InputStore()
        store.create_domain("test-d")
        store.create_source("test-d", "src1")
        assert store.get_spec("test-d", "src1") == ""
        store.save_spec("test-d", "src1", "# Specification")
        assert "Specification" in store.get_spec("test-d", "src1")
        assert store.has_spec("test-d", "src1")

    def test_delete_source(self):
        store = InputStore()
        store.create_domain("test-d")
        store.create_source("test-d", "src1")
        assert store.source_exists("test-d", "src1")
        store.delete_source("test-d", "src1")
        assert not store.source_exists("test-d", "src1")

    def test_delete_domain(self):
        store = InputStore()
        store.create_domain("test-d")
        assert store.domain_exists("test-d")
        store.delete_domain("test-d")
        assert not store.domain_exists("test-d")

    def test_get_input_tree(self):
        store = InputStore()
        store.create_domain("alpha")
        store.create_source("alpha", "s1")
        store.create_source("alpha", "s2")
        store.create_domain("beta")
        store.create_source("beta", "s3")

        tree = get_input_tree()
        assert len(tree) == 2
        assert tree[0]["domain"] == "alpha"
        assert tree[0]["sources"] == ["s1", "s2"]
        assert tree[1]["domain"] == "beta"
        assert tree[1]["sources"] == ["s3"]


class TestOutputStore:
    def test_save_and_list_outputs(self):
        store = OutputStore()
        filename, version = store.save_output(
            "test-d", "src1", "abc123",
            {"file_metadata": {}, "fields": []},
        )
        assert filename.startswith("v")
        assert filename.endswith(".json")
        assert version == 1
        outputs = store.list_outputs("test-d", "src1")
        assert len(outputs) == 1
        assert outputs[0]["version"] == 1
        assert outputs[0]["filename"] == filename

    def test_get_output(self):
        store = OutputStore()
        filename, version = store.save_output(
            "test-d", "src1", "abc",
            {"file_metadata": {"encoding": "UTF-8"}, "fields": [{"name": "ID"}]},
        )
        assert version == 1
        data = store.get_output("test-d", "src1", filename)
        assert data["file_metadata"]["encoding"] == "UTF-8"
        assert data["fields"][0]["name"] == "ID"

    def test_list_outputs_empty(self):
        store = OutputStore()
        assert store.list_outputs("nope", "nope") == []

    def test_list_domains(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "abc", {})
        assert store.list_domains() == ["test-d"]

    def test_list_sources(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "abc", {})
        store.save_output("test-d", "src2", "def", {})
        assert store.list_sources("test-d") == ["src1", "src2"]

    def test_save_output_creates_manifest(self):
        store = OutputStore()
        filename, version = store.save_output(
            "test-d", "src1", "sess1",
            {"file_metadata": {}, "fields": [], "warnings": []},
        )
        assert version == 1
        assert filename == "v1_sess1.json"
        manifest = store.get_manifest("test-d", "src1")
        assert manifest["domain"] == "test-d"
        assert manifest["source"] == "src1"
        assert manifest["latest_version"] == 1
        assert len(manifest["versions"]) == 1
        v = manifest["versions"][0]
        assert v["version"] == 1
        assert v["session_id"] == "sess1"
        assert v["based_on_version"] is None

    def test_save_output_increments_version(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        store.save_output("test-d", "src1", "sess-b", {"fields": []})
        manifest = store.get_manifest("test-d", "src1")
        assert manifest["latest_version"] == 2
        assert len(manifest["versions"]) == 2
        assert manifest["versions"][0]["version"] == 1
        assert manifest["versions"][0]["based_on_version"] is None
        assert manifest["versions"][1]["version"] == 2
        assert manifest["versions"][1]["based_on_version"] == 1

    def test_save_output_with_feedback_rounds(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []}, feedback_rounds=3)
        manifest = store.get_manifest("test-d", "src1")
        assert manifest["versions"][0]["feedback_rounds"] == 3

    def test_get_latest_output(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": [{"name": "A"}]})
        store.save_output("test-d", "src1", "sess-b", {"fields": [{"name": "B"}]})

        latest = store.get_latest_output("test-d", "src1")
        assert latest is not None
        assert latest["version"] == 2
        assert latest["session_id"] == "sess-b"
        assert latest["data"]["fields"][0]["name"] == "B"

    def test_get_latest_output_empty_source(self):
        store = OutputStore()
        assert store.get_latest_output("nope", "nope") is None

    def test_get_output_by_version(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": [{"name": "A"}]})
        store.save_output("test-d", "src1", "sess-b", {"fields": [{"name": "B"}]})

        out1 = store.get_output_by_version("test-d", "src1", 1)
        assert out1 is not None
        assert out1["version"] == 1
        assert out1["session_id"] == "sess-a"

        out2 = store.get_output_by_version("test-d", "src1", 2)
        assert out2 is not None
        assert out2["version"] == 2

        assert store.get_output_by_version("test-d", "src1", 99) is None

    def test_diff_outputs(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {
            "file_metadata": {"encoding": "UTF-8"},
            "fields": [{"field_group": "header", "field_index": 0, "field_name": "id", "data_type": "integer", "description": "ID"}],
            "warnings": ["warning-a"],
        })
        store.save_output("test-d", "src1", "sess-b", {
            "file_metadata": {"encoding": "ASCII"},
            "fields": [{"field_group": "header", "field_index": 0, "field_name": "id", "data_type": "string", "description": "ID field"}],
            "warnings": ["warning-b"],
        })

        diff = store.diff_outputs("test-d", "src1", 1, 2)
        assert diff["v1"] == 1
        assert diff["v2"] == 2

        assert "encoding" in diff["file_metadata"]["changed"]
        assert diff["file_metadata"]["changed"]["encoding"]["old"] == "UTF-8"
        assert diff["file_metadata"]["changed"]["encoding"]["new"] == "ASCII"

        assert len(diff["fields"]["changed"]) > 0

        assert diff["warnings"]["added"] == ["warning-b"]
        assert diff["warnings"]["removed"] == ["warning-a"]

    def test_diff_outputs_added_fields(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {
            "file_metadata": {},
            "fields": [{"field_group": "header", "field_index": 0, "field_name": "col1", "data_type": "string", "description": ""}],
            "warnings": [],
        })
        store.save_output("test-d", "src1", "sess-b", {
            "file_metadata": {},
            "fields": [
                {"field_group": "header", "field_index": 0, "field_name": "col1", "data_type": "string", "description": ""},
                {"field_group": "content", "field_index": 1, "field_name": "col2", "data_type": "integer", "description": ""},
            ],
            "warnings": [],
        })

        diff = store.diff_outputs("test-d", "src1", 1, 2)
        assert len(diff["fields"]["added"]) == 1
        assert diff["fields"]["added"][0]["field_name"] == "col2"
        assert len(diff["fields"]["removed"]) == 0

    def test_diff_outputs_removed_fields(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {
            "file_metadata": {},
            "fields": [
                {"field_group": "header", "field_index": 0, "field_name": "col1", "data_type": "string", "description": ""},
                {"field_group": "content", "field_index": 1, "field_name": "col2", "data_type": "integer", "description": ""},
            ],
            "warnings": [],
        })
        store.save_output("test-d", "src1", "sess-b", {
            "file_metadata": {},
            "fields": [
                {"field_group": "header", "field_index": 0, "field_name": "col1", "data_type": "string", "description": ""},
            ],
            "warnings": [],
        })

        diff = store.diff_outputs("test-d", "src1", 1, 2)
        assert len(diff["fields"]["removed"]) == 1
        assert diff["fields"]["removed"][0]["field_name"] == "col2"

    def test_diff_outputs_missing_version(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        with pytest.raises(ValueError):
            store.diff_outputs("test-d", "src1", 1, 2)

    def test_version_chain(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        store.save_output("test-d", "src1", "sess-b", {"fields": []}, feedback_rounds=2)
        store.save_output("test-d", "src1", "sess-c", {"fields": []})

        chain = store.get_version_chain("test-d", "src1")
        assert len(chain) == 3
        assert chain[0]["version"] == 1
        assert not chain[0]["is_based_on_feedback"]
        assert chain[1]["version"] == 2
        assert chain[1]["is_based_on_feedback"]
        assert chain[1]["feedback_rounds"] == 2
        assert chain[2]["version"] == 3
        assert chain[2]["is_based_on_feedback"]

    def test_version_chain_specific_version(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        store.save_output("test-d", "src1", "sess-b", {"fields": []})
        store.save_output("test-d", "src1", "sess-c", {"fields": []})

        chain = store.get_version_chain("test-d", "src1", version=2)
        assert len(chain) == 2
        assert chain[0]["version"] == 1
        assert chain[1]["version"] == 2

    def test_version_chain_empty_source(self):
        store = OutputStore()
        assert store.get_version_chain("nope", "nope") == []

    def test_get_manifest(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        m = store.get_manifest("test-d", "src1")
        assert m["domain"] == "test-d"
        assert m["source"] == "src1"
        assert m["latest_version"] == 1
        assert len(m["versions"]) == 1

    def test_manifest_read_write_roundtrip(self):
        store = OutputStore()
        store.save_output("test-d", "s1", "abc", {"fields": []})
        store.save_output("test-d", "s1", "def", {"fields": []})

        m = store.get_manifest("test-d", "s1")
        assert m["latest_version"] == 2
        assert len(m["versions"]) == 2

        m2 = store.get_manifest("test-d", "s1")
        assert m2["latest_version"] == 2

    def test_migrate_legacy_format(self):
        store = OutputStore()
        src_dir = store._source_path("test-d", "src1")
        src_dir.mkdir(parents=True, exist_ok=True)

        legacy_file = src_dir / "abc123_20260601T120000Z.json"
        legacy_file.write_text(
            json.dumps({"file_metadata": {"encoding": "UTF-8"}, "fields": []}),
            encoding="utf-8",
        )
        os.utime(str(legacy_file), (1000000, 1000000))

        store._migrate_legacy_source("test-d", "src1")
        assert not legacy_file.exists()
        assert (src_dir / "v1_abc123.json").exists()
        assert (src_dir / "_manifest.json").exists()

        manifest = store.get_manifest("test-d", "src1")
        assert manifest["latest_version"] == 1
        assert manifest["versions"][0]["session_id"] == "abc123"
        assert manifest["versions"][0]["filename"] == "v1_abc123.json"

    def test_migrate_legacy_multiple_files(self):
        store = OutputStore()
        src_dir = store._source_path("test-d", "src1")
        src_dir.mkdir(parents=True, exist_ok=True)

        f1 = src_dir / "abc_20260601T120000Z.json"
        f1.write_text(json.dumps({"fields": [{"name": "A"}]}), encoding="utf-8")
        os.utime(str(f1), (1000000, 1000000))

        f2 = src_dir / "def_20260602T120000Z.json"
        f2.write_text(json.dumps({"fields": [{"name": "B"}]}), encoding="utf-8")
        os.utime(str(f2), (2000000, 2000000))

        f3 = src_dir / "ghi_20260603T120000Z.json"
        f3.write_text(json.dumps({"fields": [{"name": "C"}]}), encoding="utf-8")
        os.utime(str(f3), (3000000, 3000000))

        store._migrate_legacy_source("test-d", "src1")

        assert (src_dir / "v1_abc.json").exists()
        assert (src_dir / "v2_def.json").exists()
        assert (src_dir / "v3_ghi.json").exists()
        assert (src_dir / "_manifest.json").exists()

        manifest = store.get_manifest("test-d", "src1")
        assert manifest["latest_version"] == 3
        assert manifest["versions"][0]["based_on_version"] is None
        assert manifest["versions"][1]["based_on_version"] == 1
        assert manifest["versions"][2]["based_on_version"] == 2

    def test_migrate_all(self):
        store = OutputStore()
        src_dir = store._source_path("test-d", "src1")
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "abc_20260601T120000Z.json").write_text(json.dumps({}), encoding="utf-8")

        results = store.migrate_all()
        assert results["migrated_sources"] >= 1

    def test_domain_has_outputs_with_manifest(self):
        store = OutputStore()
        assert not store.domain_has_outputs("test-d")
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        assert store.domain_has_outputs("test-d")
        assert not store.domain_has_outputs("nonexistent")

    def test_list_outputs_sorted_newest_first(self):
        store = OutputStore()
        store.save_output("test-d", "src1", "sess-a", {"fields": []})
        store.save_output("test-d", "src1", "sess-b", {"fields": []})
        outputs = store.list_outputs("test-d", "src1")
        assert outputs[0]["version"] == 2
        assert outputs[1]["version"] == 1
