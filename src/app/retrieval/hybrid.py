"""
Baseline hybrid: in-app cosine + naive keyword bump.
Later: replace with TiDB server-side VECTOR + FULLTEXT and fuse (RRF/weights).
"""

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import Document
from ..models import bytes_to_floats

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0: 
        return 0.0
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

async def hybrid_search(session: AsyncSession, query_vec: np.ndarray, query_text: str, k: int = 6):
    res = await session.execute(select(Document))
    docs = res.scalars().all()
    
    q_terms = [t.strip().lower() for t in query_text.split() if t.strip()]
    scored = []
    
    for d in docs:
        v = bytes_to_floats(d.embedding)
        s_vec = cosine(query_vec, v)
        s_kw = 0.05 * sum(1 for t in q_terms if t in (d.content or "").lower())
        scored.append((s_vec + s_kw, d))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [dict(doc_id=di.doc_id, chunk_id=di.chunk_id, content=di.content, meta=di.meta) 
            for _, di in scored[:k]]
