import hmac
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "/data/knowledge.db"))
ACCESS_TOKEN = os.getenv("KNOWLEDGE_RETRIEVAL_TOKEN", "").strip()
MAX_QUERY_CHARS = max(2, int(os.getenv("KNOWLEDGE_MAX_QUERY_CHARS", "1000")))
MAX_RESULTS = max(1, min(5, int(os.getenv("KNOWLEDGE_MAX_RESULTS", "5"))))

app = FastAPI(title="AMANAH GEN Knowledge API", version="0.1.1")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def initialise() -> None:
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                publisher TEXT NOT NULL,
                version TEXT NOT NULL,
                language TEXT NOT NULL CHECK(language IN ('en','ar')),
                content_sha256 TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','approved','withdrawn')),
                created_at TEXT NOT NULL,
                approved_at TEXT,
                approved_by TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id),
                ordinal INTEGER NOT NULL,
                content TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED, document_id UNINDEXED, content,
                tokenize='unicode61'
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
        db.commit()


@app.on_event("startup")
async def startup() -> None:
    initialise()


class SearchRequest(BaseModel):
    question: str = Field(min_length=2, max_length=MAX_QUERY_CHARS)
    language: str = Field(default="any", pattern="^(any|en|ar)$")
    limit: int = Field(default=5, ge=1, le=5)


def require_internal_token(x_knowledge_token: str | None = Header(default=None)) -> None:
    if not ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail="Knowledge retrieval is not configured")
    if not x_knowledge_token or not hmac.compare_digest(x_knowledge_token, ACCESS_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid internal service credential")


def fts_query(question: str) -> str:
    terms = re.findall(r"[\w\u0600-\u06FF]{2,}", question, flags=re.UNICODE)
    # Quote every token so user input cannot alter the FTS5 query grammar.
    unique = list(dict.fromkeys(terms))[:12]
    return " OR ".join('"' + term.replace('"', '""') + '"*' for term in unique)


@app.get("/health")
async def health():
    with connect() as db:
        approved = db.execute(
            "SELECT COUNT(*) FROM documents WHERE status='approved'"
        ).fetchone()[0]
    return {
        "status": "ok",
        "service": "amanah-knowledge-api",
        "retrieval_configured": bool(ACCESS_TOKEN),
        "approved_documents": approved,
    }


@app.post("/internal/search", dependencies=[Depends(require_internal_token)])
async def search(payload: SearchRequest):
    query = fts_query(payload.question.strip())
    if not query:
        return {"results": []}
    limit = min(payload.limit, MAX_RESULTS)
    with connect() as db:
        rows = db.execute("""
            SELECT c.id AS chunk_id, c.content,
                   d.id AS document_id, d.title, d.source, d.publisher,
                   d.version, d.language
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE chunks_fts MATCH ? AND d.status='approved'
              AND (?='any' OR d.language=?)
            ORDER BY bm25(chunks_fts)
            LIMIT ?
        """, (query, payload.language, payload.language, limit)).fetchall()
    return {
        "results": [
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "title": row["title"],
                "source": row["source"],
                "publisher": row["publisher"],
                "version": row["version"],
                "language": row["language"],
                "content": row["content"],
            }
            for row in rows
        ]
    }
