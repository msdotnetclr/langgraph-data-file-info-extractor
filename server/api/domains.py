from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from server.api.schemas import (
    ContentResponse,
    ContentUpdate,
    DomainCreate,
    DomainInfo,
    OKResponse,
)
from src.storage import InputStore

router = APIRouter(prefix="/api/domains", tags=["Domains"])
store = InputStore()


@router.get("", response_model=list[DomainInfo])
async def list_domains():
    domains = store.list_domains()
    return [
        DomainInfo(
            name=d,
            source_count=store.source_count(d),
            has_instructions=store.has_instructions(d),
        )
        for d in domains
    ]


@router.post("", response_model=DomainInfo, status_code=201)
async def create_domain(body: DomainCreate):
    if store.domain_exists(body.name):
        raise HTTPException(status_code=409, detail="Domain already exists")
    store.create_domain(body.name)
    return DomainInfo(
        name=body.name,
        source_count=0,
        has_instructions=False,
    )


@router.delete("/{domain}", response_model=OKResponse)
async def delete_domain(domain: str):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    store.delete_domain(domain)
    return OKResponse()


@router.get("/{domain}/instructions", response_model=ContentResponse)
async def get_instructions(domain: str):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    content = store.get_instructions(domain)
    return ContentResponse(content=content)


@router.put("/{domain}/instructions", response_model=OKResponse)
async def save_instructions(domain: str, body: ContentUpdate):
    if not store.domain_exists(domain):
        raise HTTPException(status_code=404, detail="Domain not found")
    store.save_instructions(domain, body.content)
    return OKResponse()
