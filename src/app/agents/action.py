from ..llm.factory import get_llm

async def run_action(mode: str, prompt: str, contexts: list[dict]) -> dict:
    llm = get_llm()
    
    if mode == "qa":
        txt = "\n\n".join(c.get("content", "") for c in contexts)
        answer = await llm.chat("Answer with citations", f"Q: {prompt}\nCONTEXT:\n{txt}")
        return {"answer": answer, "citations": contexts}
    
    if mode == "summary":
        txt = "\n\n".join(c.get("content", "") for c in contexts)
        summary = await llm.chat("Summarize", f"Summarize:\n{txt}")
        return {"summary": summary}
    
    if mode == "dashboard":
        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "data": {"values": [{"x": 1, "y": 2}, {"x": 2, "y": 3}]},
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
                "y": {"field": "y", "type": "quantitative"}
            }
        }
        return {"spec": spec}
    
    return {"answer": "Unsupported mode"}
