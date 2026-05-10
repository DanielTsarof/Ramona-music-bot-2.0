from __future__ import annotations

from app.schemas.music import DownloadResult
from app.storage.crud.base_crud import AsyncBaseRepository
from app.storage.models import Track
from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession


class TrackRepository(AsyncBaseRepository[Track]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Track)

    async def get_by_video_id(self, video_id: str) -> Track | None:
        return await self.first(where={"video_id": video_id})

    async def create_track(self, result: DownloadResult) -> Track:
        track = Track(
            video_id=result.video_id,
            title=result.title,
            duration=result.duration,
            file_path=result.file_path,
            file_size=result.file_size,
        )
        return await self.create(track)

    async def increment_request_count(self, video_id: str) -> None:
        stmt = (
            sa_update(Track)
            .where(Track.video_id == video_id)
            .values(request_count=Track.request_count + 1, last_requested_at=func.now())
            .execution_options(synchronize_session=False)
        )
        await self.session.execute(stmt)
        await self.session.commit()
