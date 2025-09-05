from __future__ import annotations
import httpx, geopandas as gpd, shapely.geometry as sg
import backoff

OVERPASS = "https://overpass-api.de/api/interpreter"


@backoff.on_exception(
    backoff.expo,
    (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError),
    max_time=60,
)
def _post_json(client: httpx.Client, url: str, data: dict) -> dict:
    r = client.post(url, data=data)
    r.raise_for_status()
    return r.json()


def viario_por_limite_municipal(nome_municipio: str, uf: str) -> gpd.GeoDataFrame:
    q = f'''
    [out:json][timeout:180];
    area[name="{nome_municipio}"]["boundary"="administrative"]["admin_level"="8"]["is_in:state_code"="{uf}"];
    way(area)[highway~"^(motorway|trunk|primary|secondary|tertiary)$"];
    out geom;
    '''
    with httpx.Client(timeout=180.0) as client:
        data = _post_json(client, OVERPASS, {"data": q})
    feats = []
    for el in data.get("elements", []):
        if el.get("type") == "way" and "geometry" in el:
            coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
            feats.append({"geometry": sg.LineString(coords), **el.get("tags", {})})
    return gpd.GeoDataFrame(feats, geometry="geometry", crs="EPSG:4326")
