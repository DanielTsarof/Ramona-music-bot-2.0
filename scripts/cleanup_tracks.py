#!/usr/bin/env python3
import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg


async def cleanup(db_url: str, max_tracks: int, max_age_days: int) -> None:
    conn = await asyncpg.connect(db_url)
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM tracks WHERE file_path IS NOT NULL")
        if total <= max_tracks:
            print(f"Cached tracks: {total} (≤ {max_tracks}). Nothing to do.")
            return

        to_delete = total - max_tracks
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
        rows = await conn.fetch(
            "SELECT id, file_path FROM tracks"
            " WHERE file_path IS NOT NULL AND last_requested_at < $1"
            " ORDER BY request_count ASC, last_requested_at ASC"
            " LIMIT $2",
            cutoff,
            to_delete,
        )

        if not rows:
            print("No outdated tracks to delete (all within max_age).")
            return

        deleted = failed = 0
        for row in rows:
            path = Path(row["file_path"])
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                print(f"Warning: could not delete {path}: {exc}", file=sys.stderr)
                failed += 1
                continue
            await conn.execute(
                "UPDATE tracks SET file_path = NULL, file_size = 0 WHERE id = $1",
                row["id"],
            )
            deleted += 1

        print(f"Done: {deleted} file(s) deleted, {failed} skipped.")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge stale cached tracks down to max_tracks.")
    parser.add_argument("--db-url", required=True, help="asyncpg postgres URL")
    parser.add_argument(
        "--max-tracks",
        type=int,
        required=True,
        help="target number of cached tracks to keep",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        required=True,
        help="only delete tracks not played in this many days",
    )
    args = parser.parse_args()
    asyncio.run(cleanup(args.db_url, args.max_tracks, args.max_age))


if __name__ == "__main__":
    main()
