from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.extractor import ContextExtractor
from app.models import ExtractRequest, NoteBackup, NoteCreate, RestoreResult, WorkNote
from app.repository import BackupConflict, NoteRepository, StorageError, database_path
from app.gmail import router as gmail_router, service as gmail_service

router = APIRouter()
BACKUP_LIMIT = 5 * 1024 * 1024


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


@router.delete("/api/v1/notes/{note_id}", status_code=204)
def delete_note(note_id: str, repository: Repository):
    if not repository.delete(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return Response(status_code=204)


@router.get("/api/v1/backups", response_model=NoteBackup)
def export_backup(repository: Repository):
    notes = repository.list()
    if len(notes) > 1000:
        raise HTTPException(status_code=413, detail="backup_too_large")
    backup = NoteBackup(schema_version=1, exported_at=datetime.now(timezone.utc), notes=notes)
    content = backup.model_dump_json().encode("utf-8")
    if len(content) > BACKUP_LIMIT:
        raise HTTPException(status_code=413, detail="backup_too_large")
    return Response(content, media_type="application/json", headers={
        "Content-Disposition": 'attachment; filename="contextpad-backup.json"',
    })


@router.post("/api/v1/backups/restore", response_model=RestoreResult, openapi_extra={
    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/NoteBackup"}}}},
})
async def restore_backup(request: Request, repository: Repository):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(status_code=415, detail="json_required")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > BACKUP_LIMIT:
            raise HTTPException(status_code=413, detail="backup_too_large")
        content.extend(chunk)
    try:
        backup = NoteBackup.model_validate_json(content)
    except ValidationError:
        raise HTTPException(status_code=422, detail="invalid_backup") from None
    # SQLite can wait on a lock; keep that wait off the event loop.
    try:
        return await run_in_threadpool(repository.restore, backup.notes)
    except BackupConflict:
        raise HTTPException(status_code=409, detail="backup_conflict") from None


def create_app(path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Tests can supply an isolated repository without touching the user's DB.
        if not hasattr(application.state, "repository"):
            application.state.repository = NoteRepository(path if path is not None else database_path())
        application.state.repository.initialize()
        yield

    application = FastAPI(title="ContextPad API", version="0.3.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", gmail_service.settings.web_origin],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @application.middleware("http")
    async def sensitive_response_headers(request: Request, call_next):
        origin = request.headers.get("origin")
        allowed = {"http://localhost:5173", "http://127.0.0.1:5173", gmail_service.settings.web_origin}
        cross_site_write = request.method in {"POST", "PUT", "DELETE", "PATCH"} and (
            (origin is not None and origin not in allowed)
            or (origin is None and request.headers.get("sec-fetch-site") == "cross-site")
        )
        if cross_site_write and request.url.path.startswith("/api/v1/"):
            response = JSONResponse(status_code=403, content={"detail": "origin_not_allowed"})
        else:
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
