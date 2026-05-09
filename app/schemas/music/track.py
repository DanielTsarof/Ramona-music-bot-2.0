from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    video_id: str
    title: str
    url: str


class DownloadResult(BaseModel):
    video_id: str
    title: str
    file_path: str
    file_size: int
    duration: int | None


class TrackInfo(BaseModel):
    video_id: str
    title: str
    file_path: str
    webpage_url: str
    from_cache: bool
