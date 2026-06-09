from fastapi import APIRouter, HTTPException, Query

from server.api.schemas import (
    ContentResponse,
    ContentUpdate,
    InputTreeNode,
    OKResponse,
    SourceCreate,
    SourceInfo,
)
from src.storage import InputStore, get_input_tree

router = APIRouter(tags=["Sources"])
store = InputStore()


@router.get("/api/domains/{domain}/sources", response_model=list[SourceInfo])
async def list_sources(domain: str):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    sources = store.list_sources(domain)
    return [
        SourceInfo(name=s, domain=domain, has_spec=store.has_spec(domain, s))
        for s in sources
    ]


@router.post(
    "/api/domains/{domain}/sources",
    response_model=SourceInfo,
    status_code=201,
)
async def create_source(domain: str, body: SourceCreate):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    if store.source_exists(domain, body.name):
        raise HTTPException(status_code=409, detail="Source already exists")
    store.create_source(domain, body.name)
    return SourceInfo(name=body.name, domain=domain, has_spec=False)


@router.delete("/api/domains/{domain}/sources/{source}", response_model=OKResponse)
async def delete_source(domain: str, source: str):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    if not store.source_exists(domain, source):
        raise HTTPException(status_code=404, detail="Source not found")
    store.delete_source(domain, source)
    return OKResponse()


@router.post("/api/domains/{domain}/sources/{source}/upload-spec", response_model=OKResponse)
async def upload_spec(
    domain: str,
    source: str,
    body: ContentUpdate,
    strip_empty_lines: bool = Query(True),
):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    if not store.source_exists(domain, source):
        raise HTTPException(status_code=404, detail="Source not found")
    content = body.content
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    if strip_empty_lines:
        content = "\n".join(line for line in content.split("\n") if line.strip())
    store.save_spec(domain, source, content)
    return OKResponse()


@router.get("/api/domains/{domain}/sources/{source}/spec", response_model=ContentResponse)
async def get_spec(domain: str, source: str):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    if not store.source_exists(domain, source):
        raise HTTPException(status_code=404, detail="Source not found")
    content = store.get_spec(domain, source)
    return ContentResponse(content=content)


@router.get("/api/input-tree", response_model=list[InputTreeNode])
async def input_tree():
    tree = get_input_tree()
    return [InputTreeNode(**node) for node in tree]
