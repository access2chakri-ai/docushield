import io
import csv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from .db import Document
from .llm.factory import get_llm
from .models import floats_to_bytes

async def chunk_text(s: str, chunk_size: int = 900, overlap: int = 120):
    parts, i = [], 0
    while i < len(s):
        parts.append(s[i:i+chunk_size])
        i += (chunk_size - overlap)
    return parts

async def parse_bytes_to_text(filename: str, content: bytes) -> str:
    name = filename.lower()
    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".csv"):
        reader = csv.reader(io.StringIO(content.decode("utf-8", errors="ignore")))
        return "\n".join([", ".join(row) for row in reader])
    if name.endswith(".pdf"):
        # TODO: replace with real PDF parsing in a feature branch
        return content.decode("latin-1", errors="ignore")
    return content.decode("utf-8", errors="ignore")

async def ingest_file(session: AsyncSession, doc_id: str, filename: str, content: bytes):
    text = await parse_bytes_to_text(filename, content)
    chunks = await chunk_text(text)
    llm = get_llm()
    embeds = await llm.embed(chunks)
    
    rows = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeds)):
        rows.append({
            "doc_id": doc_id, 
            "chunk_id": i, 
            "content": chunk,
            "embedding": floats_to_bytes(emb), 
            "meta": {"filename": filename}
        })
    
    if rows:
        await session.execute(insert(Document), rows)
