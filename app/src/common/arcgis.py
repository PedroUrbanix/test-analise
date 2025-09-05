from __future__ import annotations
import httpx, time, geopandas as gpd
from shapely.geometry import shape
def _paged_query(url: str, where="1=1", out_fields="*", out_sr=4326, page_size=1000, token=None):
    params={"where":where,"outFields":out_fields,"f":"geojson","outSR":out_sr,"resultRecordCount":page_size,"resultOffset":0}
    if token: params["token"]=token
    feats=[]
    with httpx.Client(timeout=60.0) as client:
        while True:
            r=client.get(url.rstrip('/')+'/query', params=params); r.raise_for_status(); data=r.json()
            fts=data.get("features", [])
            feats.extend(fts)
            if len(fts) < page_size: break
            params["resultOffset"]+=page_size; time.sleep(0.1)
    return feats
def query_to_geodataframe(layer_url: str, where="1=1", out_fields="*", out_sr=4326, token=None):
    feats=_paged_query(layer_url, where, out_fields, out_sr, token=token)
    if not feats: return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=f"EPSG:{out_sr}")
    recs=[]; 
    for f in feats:
        props=f.get("properties", f.get("attributes", {}))
        geom=f.get("geometry")
        recs.append({**props, "geometry": shape(geom) if geom else None})
    return gpd.GeoDataFrame(recs, geometry="geometry", crs=f"EPSG:{out_sr}")
def save_geodata(gdf: gpd.GeoDataFrame, path: str): gdf.to_file(path, driver="GeoJSON")
