import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_RAW = os.getenv("DATA_ROOT", "./data")
if Path(_RAW).is_absolute():
    DATA_ROOT = Path(_RAW)
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_ROOT = _PROJECT_ROOT / _RAW

_LEGACY_FILE_RE = re.compile(r"^(.+?)_(\d{8}T\d{6}Z)\.json$")


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

    @staticmethod
    def _manifest_path(domain: str, source: str) -> Path:
        return OutputStore._source_path(domain, source) / "_manifest.json"

    def _read_manifest(self, domain: str, source: str) -> dict:
        file = self._manifest_path(domain, source)
        if not file.exists():
            return {
                "domain": domain,
                "source": source,
                "latest_version": 0,
                "versions": [],
            }
        return json.loads(file.read_text(encoding="utf-8"))

    def _write_manifest(self, domain: str, source: str, manifest: dict) -> None:
        path = self._source_path(domain, source)
        path.mkdir(parents=True, exist_ok=True)
        json_text = json.dumps(manifest, indent=2, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(
            suffix=".json", prefix="_manifest_", dir=str(path)
        )
        try:
            os.write(fd, json_text.encode("utf-8"))
        finally:
            os.close(fd)
        os.replace(tmp, str(self._manifest_path(domain, source)))

    def _ensure_migrated(self, domain: str, source: str) -> None:
        mf = self._manifest_path(domain, source)
        if mf.exists():
            return
        src_dir = self._source_path(domain, source)
        if not src_dir.exists():
            return
        legacy_files = [
            f for f in src_dir.glob("*.json")
            if _LEGACY_FILE_RE.match(f.name)
        ]
        if legacy_files:
            self._migrate_legacy_source(domain, source)

    def _migrate_legacy_source(self, domain: str, source: str) -> None:
        src_dir = self._source_path(domain, source)
        legacy_files = sorted(
            [f for f in src_dir.glob("*.json") if _LEGACY_FILE_RE.match(f.name)],
            key=lambda f: f.stat().st_mtime,
        )
        if not legacy_files:
            return

        versions = []
        for idx, file in enumerate(legacy_files, start=1):
            m = _LEGACY_FILE_RE.match(file.name)
            if not m:
                continue
            session_id = m.group(1)
            mtime = file.stat().st_mtime
            new_name = f"v{idx}_{session_id}.json"
            new_path = src_dir / new_name
            if new_path.exists() and new_path != file:
                suffix = 1
                while True:
                    alt_name = f"v{idx}_{session_id}_{suffix}.json"
                    alt_path = src_dir / alt_name
                    if not alt_path.exists():
                        new_name = alt_name
                        new_path = alt_path
                        break
                    suffix += 1
            if file != new_path:
                os.replace(str(file), str(new_path))

            versions.append({
                "version": idx,
                "session_id": session_id,
                "created_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                "filename": new_name,
                "based_on_version": idx - 1 if idx > 1 else None,
                "feedback_rounds": 0,
            })

        if versions:
            manifest = {
                "domain": domain,
                "source": source,
                "latest_version": len(versions),
                "versions": versions,
            }
            self._write_manifest(domain, source, manifest)

    @staticmethod
    def _default_manifest(domain: str, source: str) -> dict:
        return {
            "domain": domain,
            "source": source,
            "latest_version": 0,
            "versions": [],
        }

    def save_output(
        self, domain: str, source: str, session_id: str, data: dict,
        feedback_rounds: int = 0,
    ) -> tuple:
        self._ensure_migrated(domain, source)
        path = self._source_path(domain, source)
        path.mkdir(parents=True, exist_ok=True)

        manifest = self._read_manifest(domain, source)
        next_version = manifest["latest_version"] + 1
        based_on = manifest["latest_version"] if manifest["latest_version"] > 0 else None

        filename = f"v{next_version}_{session_id}.json"
        file = path / filename
        file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        now = datetime.now(timezone.utc).isoformat()
        manifest["versions"].append({
            "version": next_version,
            "session_id": session_id,
            "created_at": now,
            "filename": filename,
            "based_on_version": based_on,
            "feedback_rounds": feedback_rounds,
        })
        manifest["latest_version"] = next_version
        self._write_manifest(domain, source, manifest)

        return filename, next_version

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

    def list_outputs(self, domain: str, source: str) -> list[dict]:
        self._ensure_migrated(domain, source)
        manifest = self._read_manifest(domain, source)
        entries = []
        for v in reversed(manifest.get("versions", [])):
            file = self._source_path(domain, source) / v["filename"]
            if file.exists():
                entries.append(v)
        return entries

    def get_output(self, domain: str, source: str, filename: str) -> dict:
        file = self._source_path(domain, source) / filename
        if not file.exists():
            raise FileNotFoundError(f"Output file not found: {filename}")
        return json.loads(file.read_text(encoding="utf-8"))

    def get_manifest(self, domain: str, source: str) -> dict:
        self._ensure_migrated(domain, source)
        return self._read_manifest(domain, source)

    def get_latest_output(self, domain: str, source: str) -> Optional[dict]:
        self._ensure_migrated(domain, source)
        manifest = self._read_manifest(domain, source)
        if manifest["latest_version"] == 0:
            return None
        for v in manifest["versions"]:
            if v["version"] == manifest["latest_version"]:
                data = self.get_output(domain, source, v["filename"])
                return {
                    "version": v["version"],
                    "session_id": v["session_id"],
                    "created_at": v["created_at"],
                    "based_on_version": v.get("based_on_version"),
                    "data": data,
                }
        return None

    def get_output_by_version(
        self, domain: str, source: str, version: int
    ) -> Optional[dict]:
        self._ensure_migrated(domain, source)
        manifest = self._read_manifest(domain, source)
        for v in manifest["versions"]:
            if v["version"] == version:
                data = self.get_output(domain, source, v["filename"])
                return {
                    "version": v["version"],
                    "session_id": v["session_id"],
                    "created_at": v["created_at"],
                    "based_on_version": v.get("based_on_version"),
                    "data": data,
                }
        return None

    def diff_outputs(
        self, domain: str, source: str, v1: int, v2: int
    ) -> dict:
        out1 = self.get_output_by_version(domain, source, v1)
        out2 = self.get_output_by_version(domain, source, v2)
        if out1 is None or out2 is None:
            raise ValueError(f"Version {v1} or {v2} not found")

        d1 = out1["data"]
        d2 = out2["data"]

        return {
            "v1": v1,
            "v2": v2,
            "v1_session_id": out1["session_id"],
            "v2_session_id": out2["session_id"],
            "v1_created_at": out1["created_at"],
            "v2_created_at": out2["created_at"],
            "file_metadata": self._diff_metadata(
                d1.get("file_metadata", {}), d2.get("file_metadata", {})
            ),
            "fields": self._diff_fields(
                d1.get("fields", []), d2.get("fields", [])
            ),
            "warnings": self._diff_lists(
                d1.get("warnings", []), d2.get("warnings", [])
            ),
        }

    def get_version_chain(
        self, domain: str, source: str, version: Optional[int] = None
    ) -> list[dict]:
        self._ensure_migrated(domain, source)
        manifest = self._read_manifest(domain, source)
        target = version if version is not None else manifest["latest_version"]
        if target == 0:
            return []

        version_map = {v["version"]: v for v in manifest["versions"]}
        chain = []
        current = target
        while current is not None:
            entry = version_map.get(current)
            if entry is None:
                break
            chain.append({
                "version": entry["version"],
                "session_id": entry["session_id"],
                "created_at": entry["created_at"],
                "feedback_rounds": entry.get("feedback_rounds", 0),
                "is_based_on_feedback": entry.get("based_on_version") is not None,
            })
            current = entry.get("based_on_version")
        chain.reverse()
        return chain

    @staticmethod
    def _diff_metadata(
        old_meta: dict, new_meta: dict
    ) -> dict:
        all_keys = set(old_meta.keys()) | set(new_meta.keys())
        added = {}
        removed = {}
        changed = {}

        for key in sorted(all_keys):
            ov = old_meta.get(key)
            nv = new_meta.get(key)
            if ov is None and nv is not None:
                added[key] = nv
            elif ov is not None and nv is None:
                removed[key] = ov
            elif ov != nv:
                changed[key] = {"old": ov, "new": nv}

        return {"added": added, "removed": removed, "changed": changed}

    @staticmethod
    def _diff_fields(
        old_fields: list, new_fields: list
    ) -> dict:
        def identity(f: dict) -> tuple:
            return (
                (f.get("field_group") or "").strip().lower(),
                (f.get("field_name") or "").strip().lower(),
            )

        old_by_id: dict = {}
        for f in old_fields:
            key = identity(f)
            old_by_id.setdefault(key, []).append(f)

        new_by_id: dict = {}
        for f in new_fields:
            key = identity(f)
            new_by_id.setdefault(key, []).append(f)

        old_ids = set(old_by_id.keys())
        new_ids = set(new_by_id.keys())

        added = []
        removed = []
        changed = []

        id_sort = lambda k: (k[0], k[1])

        for id_key in sorted(new_ids - old_ids, key=id_sort):
            for f in new_by_id[id_key]:
                added.append(f)

        for id_key in sorted(old_ids - new_ids, key=id_sort):
            for f in old_by_id[id_key]:
                removed.append(f)

        for id_key in sorted(old_ids & new_ids, key=id_sort):
            old_list = old_by_id[id_key]
            new_list = new_by_id[id_key]

            for i in range(max(len(old_list), len(new_list))):
                old_f = old_list[i] if i < len(old_list) else None
                new_f = new_list[i] if i < len(new_list) else None

                if old_f is None:
                    added.append(new_f)
                elif new_f is None:
                    removed.append(old_f)
                else:
                    field_changes = {}
                    for attr in ("field_name", "data_type", "description", "field_index", "field_group"):
                        ov = old_f.get(attr)
                        nv = new_f.get(attr)
                        if ov != nv:
                            field_changes[attr] = {"old": ov, "new": nv}
                    if field_changes:
                        changed.append({
                            "key": {
                                "field_group": old_f.get("field_group", ""),
                                "field_index": old_f.get("field_index"),
                                "field_name": old_f.get("field_name", ""),
                            },
                            "new_key": {
                                "field_group": new_f.get("field_group", ""),
                                "field_index": new_f.get("field_index"),
                                "field_name": new_f.get("field_name", ""),
                            },
                            "changes": field_changes,
                        })

        return {"added": added, "removed": removed, "changed": changed}

    @staticmethod
    def _diff_lists(old_list: list, new_list: list) -> dict:
        old_set = set(old_list)
        new_set = set(new_list)
        return {
            "added": sorted(new_set - old_set),
            "removed": sorted(old_set - new_set),
        }

    def domain_has_outputs(self, domain: str) -> bool:
        path = self._domain_path(domain)
        if not path.exists():
            return False
        for source_dir in path.iterdir():
            if source_dir.is_dir():
                if self._manifest_path(domain, source_dir.name).exists():
                    return True
                if any(
                    f for f in source_dir.glob("*.json")
                    if f.name != "_manifest.json"
                ):
                    return True
        return False

    def migrate_all(self) -> dict:
        results = {"migrated_sources": 0, "skipped": 0, "errors": []}
        for domain in self.list_domains():
            for source in self.list_sources(domain):
                src_dir = self._source_path(domain, source)
                if self._manifest_path(domain, source).exists():
                    results["skipped"] += 1
                    continue
                legacy = [
                    f for f in src_dir.glob("*.json")
                    if _LEGACY_FILE_RE.match(f.name)
                ]
                if legacy:
                    try:
                        self._migrate_legacy_source(domain, source)
                        results["migrated_sources"] += 1
                    except Exception as exc:
                        results["errors"].append(f"{domain}/{source}: {exc}")
                else:
                    results["skipped"] += 1
        return results


def get_input_tree() -> list[dict]:
    store = InputStore()
    domains = store.list_domains()
    result = []
    for domain in domains:
        sources = store.list_sources(domain)
        result.append({"domain": domain, "sources": sources})
    return result
