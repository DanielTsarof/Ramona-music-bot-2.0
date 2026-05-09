from __future__ import annotations

import re

import aiohttp

from app.constants import YOUTUBE_API_BASE, YOUTUBE_SEARCH_MAX_RESULTS, YOUTUBE_VIDEO_BASE
from app.logger import log
from app.schemas.music import SearchResult

_YT_URL_RE = re.compile(r"(?:youtube\.com/(?:watch\?.*v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})")


class YouTubeAPIClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def aclose(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def search(self, query: str, max_results: int = YOUTUBE_SEARCH_MAX_RESULTS) -> list[SearchResult]:
        log.debug(f"YouTube search: query={query!r} max_results={max_results}")
        params = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": str(max_results),
            "key": self._api_key,
        }
        session = self._get_session()
        async with session.get(f"{YOUTUBE_API_BASE}/search", params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()

        results: list[SearchResult] = []
        for item in data.get("items", []):
            video_id: str = item["id"]["videoId"]
            title: str = item["snippet"]["title"]
            results.append(SearchResult(video_id=video_id, title=title, url=YOUTUBE_VIDEO_BASE + video_id))

        log.debug(f"YouTube search returned {len(results)} result(s) for {query!r}")
        return results

    async def get_video_title(self, video_id: str) -> str:
        log.debug(f"Fetching video title for video_id={video_id}")
        params = {"part": "snippet", "id": video_id, "key": self._api_key}
        session = self._get_session()
        async with session.get(f"{YOUTUBE_API_BASE}/videos", params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("items", [])
        title = items[0]["snippet"]["title"] if items else video_id
        log.debug(f"Resolved title for {video_id}: {title!r}")
        return title

    async def resolve(self, query: str) -> SearchResult:
        """Return a SearchResult for a URL or a plain-text search query."""
        match = _YT_URL_RE.search(query)
        if match:
            video_id = match.group(1)
            log.info(f"Resolved URL to video_id={video_id}")
            title = await self.get_video_title(video_id)
            return SearchResult(video_id=video_id, title=title, url=YOUTUBE_VIDEO_BASE + video_id)

        results = await self.search(query, max_results=1)
        if not results:
            log.warning(f"No YouTube results for query={query!r}")
            raise ValueError(f"No YouTube results found for: {query!r}")
        log.info(f"Resolved query {query!r} to video_id={results[0].video_id} title={results[0].title!r}")
        return results[0]
