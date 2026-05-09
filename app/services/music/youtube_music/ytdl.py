from __future__ import annotations

import asyncio
from pathlib import Path

import yt_dlp

from app.constants import YTDL_AUDIO_CODEC, YTDL_AUDIO_QUALITY, YTDL_FORMAT, YOUTUBE_VIDEO_BASE
from app.logger import log
from app.schemas.music import DownloadResult
from app.utils.file_storage import LocalFileStorage


class YtDlpDownloader:
    def __init__(self, file_storage: LocalFileStorage) -> None:
        self._storage = file_storage

    def _build_opts(self, video_id: str) -> dict:
        base = self._storage.storage_path / video_id
        return {
            "format": YTDL_FORMAT,
            "outtmpl": str(base) + ".%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": YTDL_AUDIO_CODEC,
                    "preferredquality": YTDL_AUDIO_QUALITY,
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }

    async def download(self, video_id: str) -> DownloadResult:
        opts = self._build_opts(video_id)
        url = YOUTUBE_VIDEO_BASE + video_id
        log.info(f"Starting download: video_id={video_id}")

        def _sync() -> dict:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=True) or {}

        info = await asyncio.to_thread(_sync)

        file_path = self._storage.storage_path / f"{video_id}.{YTDL_AUDIO_CODEC}"
        file_size = file_path.stat().st_size if file_path.exists() else 0
        raw_duration = info.get("duration")
        title = info.get("title", video_id)

        log.info(f"Download complete: video_id={video_id} title={title!r} size={file_size} bytes")

        return DownloadResult(
            video_id=video_id,
            title=title,
            file_path=str(file_path.resolve()),
            file_size=file_size,
            duration=int(raw_duration) if raw_duration is not None else None,
        )
