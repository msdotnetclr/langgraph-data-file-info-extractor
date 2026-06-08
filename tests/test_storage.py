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
        filename = store.save_output(
            "test-d", "src1", "abc123",
            {"file_metadata": {}, "fields": []},
        )
        assert filename.endswith(".json")
        outputs = store.list_outputs("test-d", "src1")
        assert len(outputs) == 1
        assert outputs[0] == filename

    def test_get_output(self):
        store = OutputStore()
        filename = store.save_output(
            "test-d", "src1", "abc",
            {"file_metadata": {"encoding": "UTF-8"}, "fields": [{"name": "ID"}]},
        )
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
