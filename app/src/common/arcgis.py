from __future__ import annotations
import httpx, geopandas as gpd
from shapely.geometry import shape
import backoff


@backoff.on_exception(
    backoff.expo,
    (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError),
    max_time=60,
)
def _get_json(client: httpx.Client, url: str, params: dict) -> dict:
    r = client.get(url, params=params)
    r.raise_for_status()
    return r.json()


def _paged_query(
    url: str,
    where: str = "1=1",
    out_fields: str = "*",
    out_sr: int = 4326,
    page_size: int = 1000,
    token=None,
):
    params = {
        "where": where,
        "outFields": out_fields,
        "f": "geojson",
        "outSR": out_sr,
        "resultRecordCount": page_size,
        "resultOffset": 0,
    }
    if token:
        params["token"] = token
    feats = []
    with httpx.Client(timeout=60.0) as client:
        while True:
            data = _get_json(client, url.rstrip("/") + "/query", params)
            fts = data.get("features", [])
            feats.extend(fts)
            # Para quando a p├ígina vier completa e sem exceededTransferLimit
            if len(fts) < page_size and not data.get("exceededTransferLimit"):
                break
            params["resultOffset"] += page_size
    return feats


def query_to_geodataframe(
    layer_url: str, where: str = "1=1", out_fields: str = "*", out_sr: int = 4326, token=None
):
    feats = _paged_query(layer_url, where, out_fields, out_sr, token=token)
    if not feats:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=f"EPSG:{out_sr}")
    recs = []
    for f in feats:
        props = f.get("properties", f.get("attributes", {}))
        geom = f.get("geometry")
        recs.append({**props, "geometry": shape(geom) if geom else None})
    return gpd.GeoDataFrame(recs, geometry="geometry", crs=f"EPSG:{out_sr}")


def save_geodata(gdf: gpd.GeoDataFrame, path: str):
    gdf.to_file(path, driver="GeoJSON")
