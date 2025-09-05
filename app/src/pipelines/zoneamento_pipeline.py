from __future__ import annotations
import os
from datetime import datetime
from common.arcgis import query_to_geodataframe, save_geodata
from common.db import get_engine, ensure_postgis

def run_zoneamento(city: str, uf: str, layer_url: str, out_dir: str = "outputs"):
    gdf=query_to_geodataframe(layer_url, where="1=1", out_fields="*")
    ts=datetime.utcnow().strftime("%Y-%m-%d"); out_city=os.path.join(out_dir, city); os.makedirs(out_city, exist_ok=True)
    geojson_path=os.path.join(out_city, f"zoneamento_{ts}.geojson"); save_geodata(gdf, geojson_path)
    url=os.getenv("DATABASE_URL")
    if url and not gdf.empty:
        eng=get_engine(url); ensure_postgis(eng); gdf.to_postgis("zoneamento_municipal", con=eng, if_exists="replace", index=False)
    return {"features": int(len(gdf)), "geojson": geojson_path}
