from __future__ import annotations
import asyncio, typer
from agents.orchestrator import Orchestrator
from common.tools import Tools
app = typer.Typer()
@app.command()
def run(city: str, uf: str, planmob_excel: str = typer.Option(None, help="Caminho para o Excel PlanMob")):
    async def _run():
        tools = Tools()
        orch = Orchestrator(tools)
        return await orch.run_city(city, uf, planmob_excel=planmob_excel)
    print(asyncio.run(_run()))
if __name__ == "__main__":
    app()
