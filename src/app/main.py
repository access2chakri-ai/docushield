from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import ORJSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker
from .settings import settings
from .db import Base, get_engine
from .schemas import QueryRequest
from .ingest import ingest_file
from .agents.planner import plan
from .agents.retriever import retrieve
from .agents.action import run_action
from .agents.audit import log_interaction

app = FastAPI(title="DocuShield")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.Session = async_sessionmaker(engine, expire_on_commit=False)

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/readyz")
async def readyz():
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return """
<html>
<head>
    <meta charset='utf-8'/>
    <title>DocuShield</title>
    <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
    <style>
        body{font-family:system-ui;margin:24px} 
        .col{display:flex;gap:24px}
        .panel{flex:1;border:1px solid #ddd;padding:16px;border-radius:10px}
        .chips span{display:inline-block;background:#eef;padding:4px 8px;margin:4px;border-radius:8px}
    </style>
</head>
<body>
    <h2>DocuShield • Hackathon Base</h2>
    <div class="col">
        <div class="panel">
            <h3>Upload</h3>
            <form id="up" enctype="multipart/form-data">
                <input name="doc_id" placeholder="doc-001" value="doc-001" />
                <input type="file" name="file" />
                <button>Ingest</button>
            </form>
            <div id="upres"></div>
            <hr/>
            <h3>Query</h3>
            <select id="mode">
                <option value="qa">Q&A</option>
                <option value="summary">Summary</option>
                <option value="dashboard">Dashboard</option>
            </select>
            <input id="prompt" size="50" placeholder="Ask something..."/>
            <button id="go">Run</button>
        </div>
        <div class="panel">
            <h3>Result</h3>
            <pre id="out"></pre>
            <div id="vis"></div>
            <div class="chips" id="cites"></div>
        </div>
    </div>
    <script>
        const up = document.getElementById('up');
        up.addEventListener('submit', async (e)=>{
            e.preventDefault();
            const fd = new FormData(up);
            const r = await fetch('/ingest', {method:'POST', body:fd});
            const j = await r.json();
            document.getElementById('upres').textContent = JSON.stringify(j);
        });
        
        document.getElementById('go').onclick = async ()=>{
            const mode = document.getElementById('mode').value;
            const prompt = document.getElementById('prompt').value;
            const r = await fetch('/query', {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body:JSON.stringify({mode, prompt})
            });
            const j = await r.json();
            document.getElementById('vis').innerHTML = '';
            document.getElementById('cites').innerHTML='';
            if(j.spec){ 
                vegaEmbed('#vis', j.spec, {actions:false}); 
            }
            document.getElementById('out').textContent = JSON.stringify(j, null, 2);
            if(j.citations){ 
                j.citations.forEach(c=>{ 
                    const s=document.createElement('span'); 
                    s.textContent=(c.doc_id||'?')+':'+(c.chunk_id??'?'); 
                    s.title=c.content?.slice(0,200)||''; 
                    document.getElementById('cites').appendChild(s); 
                }); 
            }
        }
    </script>
</body>
</html>
"""

@app.post("/ingest")
async def ingest(doc_id: str = Form(...), file: UploadFile = File(...)):
    async with app.state.Session() as session, session.begin():
        content = await file.read()
        await ingest_file(session, doc_id, file.filename, content)
        return {"status": "ok", "doc_id": doc_id}

@app.post("/query")
async def query(req: QueryRequest):
    async with app.state.Session() as session, session.begin():
        mode = plan(req.mode, req.prompt)
        contexts = await retrieve(session, req.prompt)
        result = await run_action(mode, req.prompt, contexts)
        await log_interaction(session, mode, req.prompt, result, contexts)
        return ORJSONResponse(result)
