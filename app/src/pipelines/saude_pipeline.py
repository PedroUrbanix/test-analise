from __future__ import annotations
import os, pandas as pd
from datetime import datetime
from common.cnes import estabelecimentos_por_municipio, geocode_estabelecimentos
from common.db import get_engine, ensure_postgis
def run_saude_cnes(city: str, uf: str, ibge_cod_municipio: str, out_dir: str = "outputs"):
    frames=[]; offset=0
    while True:
        df=estabelecimentos_por_municipio(ibge_cod_municipio, limit=1000, offset=offset)
        if df is None or df.empty: break
        frames.append(df)
        if len(df) < 1000: break
        offset+=1000
    all_df=pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    gdf=geocode_estabelecimentos(all_df)
    ts=datetime.utcnow().strftime("%Y-%m-%d"); out_city=os.path.join(out_dir, city); os.makedirs(out_city, exist_ok=True)
    out_csv=os.path.join(out_city, f"cnes_estabelecimentos_{ts}.csv"); all_df.to_csv(out_csv, index=False)
    out_geojson=None
    if gdf is not None and "geometry" in gdf.columns and gdf.geometry.notnull().any():
        out_geojson=os.path.join(out_city, f"cnes_estabelecimentos_{ts}.geojson"); gdf.to_file(out_geojson, driver="GeoJSON")
    url=os.getenv("DATABASE_URL")
    if url and not all_df.empty:
        eng=get_engine(url); ensure_postgis(eng); all_df.to_sql("cnes_estabelecimentos", con=eng, if_exists="replace", index=False)
        if out_geojson: gdf.to_postgis("cnes_estabelecimentos_geo", con=eng, if_exists="replace", index=False)
    return {"rows": int(len(all_df)), "csv": out_csv, "geojson": out_geojson}
