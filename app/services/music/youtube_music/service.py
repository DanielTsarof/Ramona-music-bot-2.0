from __future__ import annotations

from pathlib import Path

from app.constants import YOUTUBE_VIDEO_BASE
from app.logger import log
from app.schemas.music import TrackInfo
from app.services.music.youtube_music.api_client import YouTubeAPIClient
from app.services.music.youtube_music.ytdl import YtDlpDownloader
from app.storage.crud.track_crud import TrackRepository


class YoutubeMusicService:
    def __init__(
        self,
        api_client: YouTubeAPIClient,
        downloader: YtDlpDownloader,
        track_repo: TrackRepository,
    ) -> None:
        self._api_client = api_client
        self._downloader = downloader
        self._track_repo = track_repo

    async def get_or_download(self, query: str) -> TrackInfo:
        log.debug(f"get_or_download: query={query!r}")
        search_result = await self._api_client.resolve(query)
        track = await self._track_repo.get_by_video_id(search_result.video_id)

        if track and track.file_path and Path(track.file_path).exists():
            log.info(f"Cache hit: video_id={track.video_id} title={track.title!r}")
            await self._track_repo.increment_request_count(track.video_id)
            return TrackInfo(
                video_id=track.video_id,
                title=track.title,
                file_path=track.file_path,
                webpage_url=YOUTUBE_VIDEO_BASE + track.video_id,
                from_cache=True,
            )

        log.info(f"Cache miss: video_id={search_result.video_id} — downloading")
        download_result = await self._downloader.download(search_result.video_id)

        if track:
            log.debug(f"Updating existing DB record for video_id={track.video_id}")
            track.file_path = download_result.file_path
            track.file_size = download_result.file_size
            await self._track_repo.update(track)
            await self._track_repo.increment_request_count(track.video_id)
        else:
            log.debug(f"Creating new DB record for video_id={download_result.video_id}")
            await self._track_repo.create_track(download_result)

        return TrackInfo(
            video_id=download_result.video_id,
            title=download_result.title,
            file_path=download_result.file_path,
            webpage_url=YOUTUBE_VIDEO_BASE + download_result.video_id,
            from_cache=False,
        )
