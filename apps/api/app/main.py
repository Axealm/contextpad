from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.extractor import ContextExtractor
from app.models import ExtractRequest, NoteCreate, WorkNote
from app.repository import NoteRepository

app = FastAPI(title="ContextPad API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
