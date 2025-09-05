from __future__ import annotations
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from agents.orchestrator import Orchestrator
from common.tools import Tools
app = FastAPI(title="flows-ia API", version="0.1.0")
@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
class RunRequest(BaseModel):
    city: str
    uf: str
    planmob_excel: str | None = None
@app.post("/run")
def run(req: RunRequest):
    async def _run():
        tools = Tools()
        orch = Orchestrator(tools)
        return await orch.run_city(req.city, req.uf, planmob_excel=req.planmob_excel)
    return asyncio.run(_run())
