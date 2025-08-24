"""
Minimal pluggable LLM facade with mock defaults (replace during feature work)
"""

import numpy as np

class LLM:
    def __init__(self, provider: str = "mock"):
        self.provider = provider
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Replace with real embeddings (keep 768-dim for TiDB VECTOR(768))
        return [np.random.rand(768).astype(float).tolist() for _ in texts]
    
    async def chat(self, system: str, user: str) -> str:
        # Replace with real chat API
        return f"[{self.provider.upper()}] {user}"

def get_llm(provider: str = "mock") -> LLM:
    return LLM(provider)
