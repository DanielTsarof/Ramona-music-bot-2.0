#!/usr/bin/env python3
import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg


async def cleanup(db_url: str, max_tracks: int) -> None:
    conn = await asyncpg.connect(db_url)
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM tracks WHERE file_path IS NOT NULL")
        if total <= max_tracks:
            print(f"Cached tracks: {total} (≤ {max_tracks}). Nothing to do.")
            return

        to_delete = total - max_tracks
        rows = await conn.fetch(
            "SELECT id, file_path FROM tracks"
            " WHERE file_path IS NOT NULL"
            " ORDER BY request_count ASC, last_requested_at ASC"
            " LIMIT $1",
            to_delete,
        )

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
    parser = argparse.ArgumentParser(description="Trim cached tracks to max_tracks, least-played first.")
    parser.add_argument("--db-url", required=True, help="asyncpg postgres URL")
    parser.add_argument(
        "--max-tracks",
        type=int,
        required=True,
        help="target number of cached tracks to keep",
    )
    args = parser.parse_args()
    asyncio.run(cleanup(args.db_url, args.max_tracks))


if __name__ == "__main__":
    main()
