from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from ..db import Audit

async def log_interaction(session: AsyncSession, mode: str, prompt: str, response: dict, contexts: list[dict]):
    stmt = insert(Audit).values(
        mode=mode, 
        prompt=prompt, 
        response=str(response), 
        contexts=contexts
    )
    await session.execute(stmt)
