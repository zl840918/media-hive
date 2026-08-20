"""TMDB 客户端：搜索与详情，失败时抛 TmdbError。"""
import httpx

from app.config import get_settings


class TmdbError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class TmdbClient:
    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.tmdb_api_key
        self.base_url = settings.tmdb_base_url

    def _get(self, path: str, params: dict | None = None) -> dict:
        if not self.api_key:
            raise TmdbError("TMDB_API_KEY 未配置", 500)
        # TMDB v3 明文 key：必须用 query 参数 api_key=（Bearer 仅支持 v4 token）
        query = dict(params or {})
        query["api_key"] = self.api_key
        try:
            resp = httpx.get(
                f"{self.base_url}{path}",
                params=query,
                timeout=15,
            )
        except httpx.HTTPError as e:
            raise TmdbError(f"TMDB 请求失败: {e}") from e
        if resp.status_code == 404:
            raise TmdbError("TMDB 中未找到该条目", 404)
        if resp.status_code == 401:
            raise TmdbError("TMDB API Key 无效", 502)
        resp.raise_for_status()
        return resp.json()

    def search(self, media_type: str, query: str, year: int | None = None, limit: int = 8) -> list[dict]:
        """搜索 movie 或 tv，返回归一化结果列表。"""
        params = {"query": query, "include_adult": "false", "language": "zh-CN"}
        if year:
            params["year" if media_type == "movie" else "first_air_date_year"] = str(year)
        data = self._get(f"/search/{media_type}", params)
        results = []
        for item in data.get("results", [])[:limit]:
            results.append(
                {
                    "tmdb_id": item["id"],
                    "media_type": media_type,
                    "title": item.get("title") or item.get("name") or "",
                    "original_title": item.get("original_title") or item.get("original_name") or "",
                    "overview": item.get("overview") or "",
                    "year": _extract_year(item, media_type),
                    "poster_path": item.get("poster_path") or "",
                    "backdrop_path": item.get("backdrop_path") or "",
                }
            )
        return results

    def detail(self, media_type: str, tmdb_id: int) -> dict:
        """获取详情并归一化。"""
        item = self._get(f"/{media_type}/{tmdb_id}", {"language": "zh-CN"})
        return {
            "tmdb_id": item["id"],
            "media_type": media_type,
            "title": item.get("title") or item.get("name") or "",
            "original_title": item.get("original_title") or item.get("original_name") or "",
            "overview": item.get("overview") or "",
            "year": _extract_year(item, media_type),
            "poster_path": item.get("poster_path") or "",
            "backdrop_path": item.get("backdrop_path") or "",
        }


def _extract_year(item: dict, media_type: str) -> int | None:
    raw = item.get("release_date") or item.get("first_air_date") or ""
    if len(raw) >= 4 and raw[:4].isdigit():
        return int(raw[:4])
    return None
