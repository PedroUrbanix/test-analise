from __future__ import annotations
import httpx, geopandas as gpd, shapely.geometry as sg
OVERPASS="https://overpass-api.de/api/interpreter"
def viario_por_limite_municipal(nome_municipio: str, uf: str) -> gpd.GeoDataFrame:
    q=f'''
    [out:json][timeout:180];
    area[name="{nome_municipio}"]["boundary"="administrative"]["admin_level"="8"]["is_in:state_code"="{uf}"];
    way(area)[highway~"^(motorway|trunk|primary|secondary|tertiary)$"];
    out geom;
    '''
    with httpx.Client(timeout=180.0) as client:
        r=client.post(OVERPASS, data={"data":q}); r.raise_for_status(); data=r.json()
    feats=[]
    for el in data.get("elements", []):
        if el.get("type")=="way" and "geometry" in el:
            coords=[(pt["lon"], pt["lat"]) for pt in el["geometry"]]
            feats.append({"geometry": sg.LineString(coords), **el.get("tags", {})})
    return gpd.GeoDataFrame(feats, geometry="geometry", crs="EPSG:4326")
