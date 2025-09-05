from __future__ import annotations
import httpx, pandas as pd, geopandas as gpd
def estabelecimentos_por_municipio(ibge_mun7: str, limit: int = 1000, offset: int = 0) -> pd.DataFrame:
    url="https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
    params={"municipio":ibge_mun7,"limit":limit,"offset":offset}
    with httpx.Client(timeout=60.0) as client:
        r=client.get(url, params=params); r.raise_for_status(); js=r.json()
    rows=js if isinstance(js, list) else js.get("items", [])
    return pd.DataFrame(rows)
def geocode_estabelecimentos(df: pd.DataFrame) -> gpd.GeoDataFrame:
    lat_col=next((c for c in df.columns if c.lower() in ("lat","latitude")), None)
    lon_col=next((c for c in df.columns if c.lower() in ("lon","long","longitude")), None)
    if lat_col and lon_col:
        return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")
    return gpd.GeoDataFrame(df, geometry=None, crs="EPSG:4326")
