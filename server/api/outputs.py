from fastapi import APIRouter, HTTPException, Query

from src.storage import OutputStore

router = APIRouter(prefix="/api/outputs", tags=["Outputs"])
store = OutputStore()


def _source_summary(domain: str, source: str) -> dict:
    manifest = store.get_manifest(domain, source)
    versions = manifest.get("versions", [])
    return {
        "name": source,
        "latest_version": manifest.get("latest_version", 0),
        "total_versions": len(versions),
    }


@router.get("")
async def list_output_tree():
    tree = []
    for domain in store.list_domains():
        sources = []
        for source in store.list_sources(domain):
            sources.append(_source_summary(domain, source))
        tree.append({"domain": domain, "sources": sources})
    return tree


@router.get("/{domain}/{source}")
async def list_version_entries(domain: str, source: str):
    entries = store.list_outputs(domain, source)
    return {
        "domain": domain,
        "source": source,
        "latest_version": max((v["version"] for v in entries), default=0),
        "versions": entries,
    }


@router.get("/{domain}/{source}/latest")
async def get_latest_output(domain: str, source: str):
    result = store.get_latest_output(domain, source)
    if result is None:
        raise HTTPException(
            status_code=404, detail="No output found for this source"
        )
    return result


@router.get("/{domain}/{source}/versions/{version}")
async def get_output_by_version(domain: str, source: str, version: int):
    result = store.get_output_by_version(domain, source, version)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Version {version} not found"
        )
    return result


@router.get("/{domain}/{source}/diff")
async def diff_outputs(
    domain: str,
    source: str,
    v1: int = Query(..., description="First version number"),
    v2: int = Query(..., description="Second version number"),
):
    try:
        return store.diff_outputs(domain, source, v1, v2)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{domain}/{source}/chain")
async def get_version_chain(
    domain: str,
    source: str,
    version: int | None = Query(None, description="Version number (defaults to latest)"),
):
    chain = store.get_version_chain(domain, source, version)
    if not chain:
        raise HTTPException(
            status_code=404, detail="No version chain found for this source"
        )
    return {"domain": domain, "source": source, "chain": chain}


@router.get("/{domain}/{source}/manifest")
async def get_manifest(domain: str, source: str):
    return store.get_manifest(domain, source)


@router.get("/{domain}/{source}/{filename}")
async def get_output_file(domain: str, source: str, filename: str):
    try:
        data = store.get_output(domain, source, filename)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Output file not found")
