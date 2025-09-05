from __future__ import annotations
import os, httpx
class BraveSearchProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not self.api_key: raise RuntimeError("Defina BRAVE_API_KEY")
        self.base = "https://api.search.brave.com/res/v1"
    def web(self, q: str, count: int = 10, freshness: str | None = None):
        headers={"X-Subscription-Token": self.api_key}
        params={"q":q,"count":count}; 
        if freshness: params["freshness"]=freshness
        with httpx.Client(timeout=30.0) as client:
            r=client.get(f"{self.base}/web/search", headers=headers, params=params); r.raise_for_status()
            js=r.json()
            return [{"title":it.get("title"),"url":it.get("url"),"description":it.get("description")} for it in js.get("web",{}).get("results",[])]
