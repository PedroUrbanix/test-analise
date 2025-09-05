from __future__ import annotations
import io
import os
import re
import zipfile
from typing import Iterable

import geopandas as gpd
import httpx

# Base oficial 2022 (pode variar). Permite override por IBGE_BASE_URL.
DEFAULT_BASE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/"
    "censo_2022/setores/shp"
)


def _candidate_dirs(base: str, uf: str) -> list[str]:
    base = base.rstrip("/")
    uf = uf.upper()
    # Tenta com e sem o sufixo BR, pois o IBGE alterna entre /shp/BR e /shp
    dirs = [f"{base}/BR/{uf}", f"{base}/{uf}"]
    # Remove duplicatas preservando ordem
    seen, out = set(), []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _try_get(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        r = client.get(url)
        r.raise_for_status()
        return r
    except Exception:
        return None


def _find_zip_in_listing(html: str, cod_mun7: str) -> str | None:
    # procura por hrefs que contenham o cod_mun7 e terminem com .zip
    # ex.: 4103701.zip
    pattern = re.compile(r'href=["\']([^"\']*?%s[^"\']*?\.zip)["\']' % re.escape(cod_mun7), re.I)
    m = pattern.search(html)
    return m.group(1) if m else None


def _download_zip_bytes(client: httpx.Client, url: str) -> bytes:
    r = client.get(url)
    r.raise_for_status()
    return r.content


def _pick_first_shp(z: zipfile.ZipFile) -> str:
    shp = [n for n in z.namelist() if n.lower().endswith(".shp")]
    if not shp:
        raise RuntimeError("Arquivo ZIP do IBGE não contém .shp")
    return shp[0]


def download_setores_censitarios(uf: str, cod_mun7: str) -> gpd.GeoDataFrame:
    base = os.getenv("IBGE_BASE_URL", DEFAULT_BASE)
    tried: list[str] = []

    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        # 1) Tenta URL direta nas combinações conhecidas
        for d in _candidate_dirs(base, uf):
            direct = f"{d}/{cod_mun7}.zip"
            tried.append(direct)
            resp = _try_get(client, direct)
            if resp is not None:
                data = resp.content
                break
        else:
            # 2) Faz listing do diretório e procura o ZIP pelo padrão cod_mun7*.zip
            data = None
            for d in _candidate_dirs(base, uf):
                listing = _try_get(client, d)
                if listing is None:
                    tried.append(d)
                    continue
                href = _find_zip_in_listing(listing.text, cod_mun7)
                if href:
                    # Normaliza URL relativa/absoluta
                    if not href.lower().startswith("http"):
                        href = f"{d.rstrip('/')}/{href.lstrip('/')}"
                    tried.append(href)
                    data = _download_zip_bytes(client, href)
                    break

        if data is None:
            raise RuntimeError(
                "Não foi possível localizar o ZIP dos setores no IBGE. Tentativas: "
                + ", ".join(tried)
            )

        z = zipfile.ZipFile(io.BytesIO(data))
        shp_path = _pick_first_shp(z)

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            z.extractall(td)
            full = os.path.join(td, shp_path)
            gdf = gpd.read_file(full)
            if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
            return gdf
