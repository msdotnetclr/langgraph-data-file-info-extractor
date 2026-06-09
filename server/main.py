from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.domains import router as domains_router
from server.api.sources import router as sources_router
from server.api.sessions import router as sessions_router
from server.api.extract import router as extract_router
from server.api.review import router as review_router
from server.api.outputs import router as outputs_router

app = FastAPI(title="Source Data Spec Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domains_router)
app.include_router(sources_router)
app.include_router(sessions_router)
app.include_router(extract_router)
app.include_router(review_router)
app.include_router(outputs_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
