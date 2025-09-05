from __future__ import annotations
import os
from datetime import datetime
from common.ibge import download_setores_censitarios
from common.db import get_engine, ensure_postgis
def run_ibge_setores(city: str, uf: str, ibge_cod_municipio: str, out_dir: str = "outputs"):
    gdf=download_setores_censitarios(uf, ibge_cod_municipio)
    ts=datetime.utcnow().strftime("%Y-%m-%d"); out_city=os.path.join(out_dir, city); os.makedirs(out_city, exist_ok=True)
    out_geojson=os.path.join(out_city, f"ibge_setores_{ts}.geojson"); gdf.to_file(out_geojson, driver="GeoJSON")
    url=os.getenv("DATABASE_URL")
    if url and not gdf.empty:
        eng=get_engine(url); ensure_postgis(eng); gdf.to_postgis("ibge_setores_2022", con=eng, if_exists="replace", index=False)
    return {"features": int(len(gdf)), "geojson": out_geojson}
