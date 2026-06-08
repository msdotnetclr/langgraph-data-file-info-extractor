import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_RAW = os.getenv("DATA_ROOT", "./data")
if Path(_RAW).is_absolute():
    DATA_ROOT = Path(_RAW)
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_ROOT = _PROJECT_ROOT / _RAW


class InputStore:
    @staticmethod
    def _domain_path(name: str) -> Path:
        return DATA_ROOT / "input" / name

    @staticmethod
    def _source_path(domain: str, name: str) -> Path:
        return DATA_ROOT / "input" / domain / name

    def list_domains(self) -> list[str]:
        root = DATA_ROOT / "input"
        if not root.exists():
            return []
        return sorted(
            d.name
            for d in root.iterdir()
            if d.is_dir()
        )

    def create_domain(self, name: str) -> None:
        path = self._domain_path(name)
        path.mkdir(parents=True, exist_ok=True)
        instructions_file = path / "domain_instructions.md"
        if not instructions_file.exists():
            instructions_file.write_text("", encoding="utf-8")

    def delete_domain(self, name: str) -> None:
        path = self._domain_path(name)
        if path.exists():
            shutil.rmtree(path)

    def list_sources(self, domain: str) -> list[str]:
        path = self._domain_path(domain)
        if not path.exists():
            return []
        return sorted(
            d.name
            for d in path.iterdir()
            if d.is_dir()
        )

    def create_source(self, domain: str, name: str) -> None:
        path = self._source_path(domain, name)
        path.mkdir(parents=True, exist_ok=True)

    def delete_source(self, domain: str, name: str) -> None:
        path = self._source_path(domain, name)
        if path.exists():
            shutil.rmtree(path)

    def get_instructions(self, domain: str) -> str:
        file = self._domain_path(domain) / "domain_instructions.md"
        if not file.exists():
            return ""
        return file.read_text(encoding="utf-8")

    def save_instructions(self, domain: str, content: str) -> None:
        file = self._domain_path(domain) / "domain_instructions.md"
        file.write_text(content, encoding="utf-8")

    def get_spec(self, domain: str, source: str) -> str:
        file = self._source_path(domain, source) / "source_specs.md"
        if not file.exists():
            return ""
        return file.read_text(encoding="utf-8")

    def save_spec(self, domain: str, source: str, content: str) -> None:
        file = self._source_path(domain, source) / "source_specs.md"
        file.write_text(content, encoding="utf-8")

    def domain_exists(self, name: str) -> bool:
        return self._domain_path(name).is_dir()

    def source_exists(self, domain: str, name: str) -> bool:
        return self._source_path(domain, name).is_dir()

    def source_count(self, domain: str) -> int:
        return len(self.list_sources(domain))

    def has_instructions(self, domain: str) -> bool:
        file = self._domain_path(domain) / "domain_instructions.md"
        return file.exists() and file.read_text(encoding="utf-8").strip() != ""

    def has_spec(self, domain: str, source: str) -> bool:
        file = self._source_path(domain, source) / "source_specs.md"
        return file.exists()


class OutputStore:
    @staticmethod
    def _domain_path(domain: str) -> Path:
        return DATA_ROOT / "output" / domain

    @staticmethod
    def _source_path(domain: str, source: str) -> Path:
        return DATA_ROOT / "output" / domain / source

    def list_domains(self) -> list[str]:
        root = DATA_ROOT / "output"
        if not root.exists():
            return []
        return sorted(
            d.name
            for d in root.iterdir()
            if d.is_dir()
        )

    def list_sources(self, domain: str) -> list[str]:
        path = self._domain_path(domain)
        if not path.exists():
            return []
        return sorted(
            d.name
            for d in path.iterdir()
            if d.is_dir()
        )

    def list_outputs(self, domain: str, source: str) -> list[str]:
        path = self._source_path(domain, source)
        if not path.exists():
            return []
        files = sorted(
            path.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        return [f.name for f in files]

    def get_output(self, domain: str, source: str, filename: str) -> dict:
        file = self._source_path(domain, source) / filename
        if not file.exists():
            raise FileNotFoundError(f"Output file not found: {filename}")
        return json.loads(file.read_text(encoding="utf-8"))

    def save_output(
        self, domain: str, source: str, session_id: str, data: dict
    ) -> str:
        path = self._source_path(domain, source)
        path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{session_id}_{timestamp}.json"
        file = path / filename
        file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return filename

    def domain_has_outputs(self, domain: str) -> bool:
        path = self._domain_path(domain)
        if not path.exists():
            return False
        for source_dir in path.iterdir():
            if source_dir.is_dir() and any(source_dir.glob("*.json")):
                return True
        return False


def get_input_tree() -> list[dict]:
    store = InputStore()
    domains = store.list_domains()
    result = []
    for domain in domains:
        sources = store.list_sources(domain)
        result.append({"domain": domain, "sources": sources})
    return result
