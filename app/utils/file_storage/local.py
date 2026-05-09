from __future__ import annotations

from pathlib import Path


class LocalFileStorage:
    def __init__(self, storage_path: str | Path) -> None:
        self.storage_path = Path(storage_path).resolve()
        self.ensure_dir()

    def ensure_dir(self) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_path(self, video_id: str, ext: str) -> Path:
        return self.storage_path / f"{video_id}.{ext.lstrip('.')}"

    def exists(self, video_id: str, ext: str) -> bool:
        return self.get_path(video_id, ext).exists()

    def delete(self, video_id: str, ext: str) -> None:
        self.get_path(video_id, ext).unlink(missing_ok=True)
