#!/usr/bin/env python3
"""Admin CLI for the AMANAH GEN knowledge registry.

Ingestion creates a PENDING record. Only an explicit human approval enables retrieval.
The event table records ingestion, approval, and withdrawal actions. It is an
application audit trail, not tamper-proof or a replacement for central audit logging.
"""
import argparse
import hashlib
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB = Path("/data/knowledge.db")


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
            publisher TEXT NOT NULL, version TEXT NOT NULL,
            language TEXT NOT NULL CHECK(language IN ('en','ar')),
            content_sha256 TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','approved','withdrawn')),
            created_at TEXT NOT NULL, approved_at TEXT, approved_by TEXT
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
            ordinal INTEGER NOT NULL, content TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_id UNINDEXED, document_id UNINDEXED, content,
            tokenize='unicode61'
        );
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
        CREATE TABLE IF NOT EXISTS document_events (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('registered','approved','withdrawn')),
            actor TEXT NOT NULL, occurred_at TEXT NOT NULL, note TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_document_events_doc ON document_events(document_id, occurred_at);
    """)
    return db


def event(db, doc_id, action, actor, note=""):
    db.execute(
        "INSERT INTO document_events(id,document_id,action,actor,occurred_at,note) VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), doc_id, action, actor, now(), note),
    )


def make_chunks(text, size=1100):
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    paragraphs = [p for p in paragraphs if p]
    chunks, current = [], ""
    for paragraph in paragraphs:
        while len(paragraph) > size:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(paragraph[:size])
            paragraph = paragraph[size:]
        candidate = (current + "\n\n" + paragraph).strip() if current else paragraph
        if len(candidate) > size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def ingest(args):
    path = Path(args.file)
    if path.suffix.lower() not in {".md", ".txt"}:
        raise SystemExit("Only .md and .txt files are supported.")
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise SystemExit("File not found or exceeds the 1 MB ingestion limit.")
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8").strip()
    except UnicodeDecodeError:
        raise SystemExit("Document must be valid UTF-8.")
    if len(content) < 80:
        raise SystemExit("Document is too short; provide a substantive source.")
    digest = hashlib.sha256(raw).hexdigest()
    chunks = make_chunks(content)
    if not chunks:
        raise SystemExit("No indexable text found.")
    doc_id = str(uuid.uuid4())
    with connect() as db:
        existing = db.execute(
            "SELECT id,status FROM documents WHERE content_sha256=?", (digest,)
        ).fetchone()
        if existing:
            raise SystemExit(f"Identical content already registered: {existing[0]} ({existing[1]})")
        db.execute("""
            INSERT INTO documents
            (id,title,source,publisher,version,language,content_sha256,status,created_at)
            VALUES (?,?,?,?,?,?,?,'pending',?)
        """, (doc_id,args.title,args.source,args.publisher,args.version,args.language,digest,now()))
        for ordinal, chunk in enumerate(chunks, 1):
            chunk_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO chunks(id,document_id,ordinal,content) VALUES (?,?,?,?)",
                (chunk_id,doc_id,ordinal,chunk),
            )
            db.execute(
                "INSERT INTO chunks_fts(chunk_id,document_id,content) VALUES (?,?,?)",
                (chunk_id,doc_id,chunk),
            )
        event(db, doc_id, "registered", args.registered_by, "Created as pending; not retrievable.")
        db.commit()
    print(f"Document registered as PENDING: {doc_id}")
    print(f"Chunks: {len(chunks)}")
    print("It cannot be retrieved until an authorised reviewer approves it.")


def approve(args):
    with connect() as db:
        row = db.execute("SELECT status FROM documents WHERE id=?", (args.id,)).fetchone()
        if not row:
            raise SystemExit("Document not found.")
        if row[0] != "pending":
            raise SystemExit(f"Only pending documents can be approved (current status: {row[0]}).")
        db.execute(
            "UPDATE documents SET status='approved', approved_at=?, approved_by=? WHERE id=?",
            (now(),args.approved_by,args.id),
        )
        event(db, args.id, "approved", args.approved_by, args.note)
        db.commit()
    print(f"Approved: {args.id} by {args.approved_by}")


def withdraw(args):
    with connect() as db:
        cur = db.execute(
            "UPDATE documents SET status='withdrawn' WHERE id=? AND status='approved'",
            (args.id,),
        )
        if cur.rowcount != 1:
            raise SystemExit("Approved document not found; no change made.")
        event(db, args.id, "withdrawn", args.withdrawn_by, args.note)
        db.commit()
    print(f"Withdrawn from retrieval: {args.id}")


def listing(_args):
    with connect() as db:
        rows = db.execute("""
            SELECT id,title,version,language,status,approved_by,created_at
            FROM documents ORDER BY created_at DESC
        """).fetchall()
    if not rows:
        print("No knowledge documents registered.")
    for row in rows:
        print(" | ".join(str(value or "") for value in row))


def history(args):
    with connect() as db:
        rows = db.execute("""
            SELECT action,actor,occurred_at,note FROM document_events
            WHERE document_id=? ORDER BY occurred_at
        """, (args.id,)).fetchall()
    if not rows:
        print("No events found for this document.")
    for row in rows:
        print(" | ".join(row))


def main():
    parser = argparse.ArgumentParser(description="AMANAH GEN knowledge registry administration")
    sub = parser.add_subparsers(required=True)
    add = sub.add_parser("ingest", help="register UTF-8 Markdown/text as pending")
    for flag in ("title","source","publisher","version","registered-by"):
        add.add_argument("--"+flag, required=True)
    add.add_argument("--language", choices=("en","ar"), required=True)
    add.add_argument("--file", required=True)
    add.set_defaults(func=ingest)
    ok = sub.add_parser("approve", help="approve a pending document after human review")
    ok.add_argument("--id", required=True)
    ok.add_argument("--approved-by", required=True)
    ok.add_argument("--note", default="")
    ok.set_defaults(func=approve)
    off = sub.add_parser("withdraw", help="remove an approved document from retrieval")
    off.add_argument("--id", required=True)
    off.add_argument("--withdrawn-by", required=True)
    off.add_argument("--note", default="")
    off.set_defaults(func=withdraw)
    ls = sub.add_parser("list", help="list registered document metadata")
    ls.set_defaults(func=listing)
    hist = sub.add_parser("history", help="show registry events for a document")
    hist.add_argument("--id", required=True)
    hist.set_defaults(func=history)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
