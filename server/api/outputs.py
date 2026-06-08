from fastapi import APIRouter, HTTPException

from server.api.schemas import OKResponse
from src.storage import OutputStore, get_input_tree

router = APIRouter(prefix="/api/outputs", tags=["Outputs"])
store = OutputStore()


@router.get("")
async def list_output_tree():
    tree = []
    for domain in store.list_domains():
        sources = []
        for source in store.list_sources(domain):
            files = store.list_outputs(domain, source)
            sources.append({"name": source, "outputs": files})
        tree.append({"domain": domain, "sources": sources})
    return tree


@router.get("/{domain}/{source}")
async def list_output_files(domain: str, source: str):
    files = store.list_outputs(domain, source)
    return {"domain": domain, "source": source, "outputs": files}


@router.get("/{domain}/{source}/{filename}")
async def get_output_file(domain: str, source: str, filename: str):
    try:
        data = store.get_output(domain, source, filename)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Output file not found")
