from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.extractor import ContextExtractor
from app.models import ExtractRequest, NoteCreate, WorkNote
from app.repository import NoteRepository, StorageError, database_path
from app.gmail import router as gmail_router, service as gmail_service

router = APIRouter()


def get_repository(request: Request) -> NoteRepository:
    return request.app.state.repository


Repository = Annotated[NoteRepository, Depends(get_repository)]

extractor = ContextExtractor()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/extract")
def extract(payload: ExtractRequest):
    return extractor.extract(payload.memo, payload.email)


@router.post("/api/v1/notes", response_model=WorkNote)
def create_note(payload: NoteCreate, repository: Repository):
    context = extractor.extract(payload.memo, payload.email)
    return repository.create(payload, context)


@router.get("/api/v1/notes", response_model=list[WorkNote])
def list_notes(repository: Repository, query: str | None = None):
    return repository.list(query)


@router.get("/api/v1/notes/{note_id}", response_model=WorkNote)
def get_note(note_id: str, repository: Repository):
    note = repository.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@router.post("/api/v1/notes/{note_id}/review", response_model=WorkNote)
def mark_reviewed(note_id: str, repository: Repository):
    note = repository.mark_reviewed(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@router.put("/api/v1/notes/{note_id}", response_model=WorkNote)
def update_note(note_id: str, payload: NoteCreate, repository: Repository):
    context = extractor.extract(payload.memo, payload.email)
    note = repository.update(note_id, payload, context)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


def create_app(path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Tests can supply an isolated repository without touching the user's DB.
        if not hasattr(application.state, "repository"):
            application.state.repository = NoteRepository(path if path is not None else database_path())
        application.state.repository.initialize()
        yield

    application = FastAPI(title="ContextPad API", version="0.2.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", gmail_service.settings.web_origin],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @application.middleware("http")
    async def sensitive_response_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(StorageError)
    async def storage_error(request: Request, exc: StorageError):
        return JSONResponse(status_code=503, content={"detail": "storage_unavailable"})

    application.include_router(router)
    application.include_router(gmail_router)
    return application


app = create_app()
