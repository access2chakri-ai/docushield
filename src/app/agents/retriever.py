import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from ..retrieval.hybrid import hybrid_search
from ..llm.factory import get_llm
from ..settings import settings

async def retrieve(session: AsyncSession, prompt: str):
    llm = get_llm()
    qvec = np.array((await llm.embed([prompt]))[0], dtype=np.float32)
    return await hybrid_search(session, qvec, prompt, k=settings.TOP_K)
