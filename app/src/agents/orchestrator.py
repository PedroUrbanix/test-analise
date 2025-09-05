from __future__ import annotations
from common.utils import log
from pipelines.mobilidade_planmob_pipeline import PlanMobETL
from pipelines.zoneamento_pipeline import run_zoneamento
from pipelines.ibge_setores_pipeline import run_ibge_setores
from pipelines.saude_pipeline import run_saude_cnes
import yaml, os
class Orchestrator:
    def __init__(self, tools): self.t = tools
    async def run_city(self, municipio: str, uf: str, planmob_excel: str | None = None):
        log(f"Iniciando {municipio}-{uf}")
        cfg_path = f"config/cities/{municipio.lower()}.yaml"
        if not os.path.exists(cfg_path): cfg_path = "config/cities/_template_city.yaml"
        cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))
        outputs = {}
        if planmob_excel and os.path.exists(planmob_excel):
            etl = PlanMobETL(municipio, uf, planmob_excel)
            outputs["planmob"] = etl.run()
        layer = cfg.get("arcgis_zoneamento_layer")
        if layer and "http" in layer:
            outputs["zoneamento"] = run_zoneamento(municipio, uf, layer)
        ibge_code = cfg.get("ibge_cod_municipio")
        if ibge_code:
            outputs["ibge_setores"] = run_ibge_setores(municipio, uf, ibge_code)
            outputs["saude_cnes"] = run_saude_cnes(municipio, uf, ibge_code)
        return outputs
