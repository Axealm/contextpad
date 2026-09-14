from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.extractor import ContextExtractor
from app.models import ExtractRequest, NoteCreate, WorkNote
from app.repository import NoteRepository
from app.gmail import router as gmail_router, service as gmail_service

app = FastAPI(title="ContextPad API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", gmail_service.settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
app.include_router(gmail_router)


@app.middleware("http")
async def sensitive_response_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response

extractor = ContextExtractor()
repository = NoteRepository()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/extract")
def extract(payload: ExtractRequest):
    return extractor.extract(payload.memo, payload.email)


@app.post("/api/v1/notes", response_model=WorkNote)
def create_note(payload: NoteCreate):
    context = extractor.extract(payload.memo, payload.email)
    return repository.create(payload, context)


@app.get("/api/v1/notes", response_model=list[WorkNote])
def list_notes(query: str | None = None):
    return repository.list(query)


@app.get("/api/v1/notes/{note_id}", response_model=WorkNote)
def get_note(note_id: str):
    note = repository.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@app.post("/api/v1/notes/{note_id}/review", response_model=WorkNote)
def mark_reviewed(note_id: str):
    note = repository.mark_reviewed(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="note not found")
    return note


@app.put("/api/v1/notes/{note_id}", response_model=WorkNote)
def update_note(note_id: str, payload: NoteCreate):
    if repository.get(note_id) is None:
        raise HTTPException(status_code=404, detail="note not found")
    context = extractor.extract(payload.memo, payload.email)
    return repository.update(note_id, payload, context)
