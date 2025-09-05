from __future__ import annotations
import os, json, pandas as pd
from datetime import datetime
from common.db import get_engine, ensure_postgis
class PlanMobETL:
    def __init__(self, city: str, uf: str, path_excel: str, out_dir: str = "outputs"):
        self.city=city; self.uf=uf; self.path_excel=path_excel
        self.out_dir=os.path.join(out_dir, city); os.makedirs(self.out_dir, exist_ok=True)
    def load(self):
        return {
            "DOM": pd.read_excel(self.path_excel, sheet_name="DOM"),
            "FAM": pd.read_excel(self.path_excel, sheet_name="FAM"),
            "IND": pd.read_excel(self.path_excel, sheet_name="IND"),
            "VIAG": pd.read_excel(self.path_excel, sheet_name="VIAG"),
        }
    def compute_indicadores(self, dfs):
        viag=dfs["VIAG"].copy(); total=float(viag["FEXP"].sum())
        def main_mode(seq: str)->str:
            if not isinstance(seq, str) or not seq: return "Desconhecido"
            return seq.split(",")[0].strip().lower()
        viag["modo_principal"]=viag["SequenciaModos"].fillna("").map(main_mode)
        modal=(viag.groupby("modo_principal")["FEXP"].sum()/total).sort_values(ascending=False)
        purpose=(viag.groupby("TipoDestino")["FEXP"].sum()/total).sort_values(ascending=False)
        return {"total_viagens_peso": total, "share_modo": modal.to_dict(), "share_motivo_destino": purpose.to_dict()}
    def export_od_por_zona(self, dfs):
        viag=dfs["VIAG"].copy()
        od=(viag.groupby(["ZonaOrigem","ZonaDestino"])["FEXP"].sum().reset_index().rename(columns={"FEXP":"peso_viagens"}))
        ts=datetime.utcnow().strftime("%Y-%m-%d"); path=os.path.join(self.out_dir, f"od_zona_{ts}.csv"); od.to_csv(path, index=False); return od
    def persist_postgres(self, dfs, indicadores):
        url=os.getenv("DATABASE_URL"); 
        if not url: return False
        eng=get_engine(url); ensure_postgis(eng)
        with eng.begin() as con:
            dfs["DOM"].to_sql("planmob_dom", con=con, if_exists="replace", index=False)
            dfs["FAM"].to_sql("planmob_fam", con=con, if_exists="replace", index=False)
            dfs["IND"].to_sql("planmob_ind", con=con, if_exists="replace", index=False)
            dfs["VIAG"].to_sql("planmob_viag", con=con, if_exists="replace", index=False)
            pd.DataFrame([indicadores]).to_sql("planmob_indicadores", con=con, if_exists="replace", index=False)
        return True
    def run(self):
        dfs=self.load(); indic=self.compute_indicadores(dfs); od=self.export_od_por_zona(dfs); persisted=self.persist_postgres(dfs, indic)
        ts=datetime.utcnow().strftime("%Y-%m-%d"); 
        with open(os.path.join(self.out_dir, f"indicadores_planmob_{ts}.json"), "w", encoding="utf-8") as f: json.dump(indic, f, ensure_ascii=False, indent=2)
        return {"indicadores": indic, "od_count": int(len(od)), "db_persisted": bool(persisted)}
