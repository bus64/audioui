#File:  src/performances/async_blob_manager.py © 2025 projectemergence. All rights reserved.
# File:  src/performances/async_blob_manager.py
import json
import asyncio
import aiohttp
from async_hyper_manager import AsyncHyperManager

JSONBLOB_BASE = "https://jsonblob.com/api/jsonBlob"

class AsyncBlobManager:
    """Async version of BlobManager, using aiohttp & AsyncHyperManager for pooling."""

    def __init__(self, blob_id: str | None = "1294281086207909888"):
        self.blob_id = blob_id
        self.base = f"{JSONBLOB_BASE}/{blob_id}" if blob_id else JSONBLOB_BASE
        self._session: aiohttp.ClientSession | None = None
        self._mgr = AsyncHyperManager(max_threads=10, max_processes=2)

    async def _session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def create_blob(self, data: dict) -> str | None:
        session = await self._session()
        async with session.post(JSONBLOB_BASE, json=data) as resp:
            if resp.status == 201:
                loc = resp.headers.get("Location", "")
                self.blob_id = loc.rsplit("/", 1)[-1]
                self.base = f"{JSONBLOB_BASE}/{self.blob_id}"
                return self.blob_id
            return None

    async def get_blob(self) -> dict | None:
        if not self.blob_id:
            return None
        session = await self._session()
        async with session.get(self.base) as resp:
            return await resp.json() if resp.status == 200 else None

    async def update_blob(self, data: dict) -> bool:
        if not self.blob_id:
            return False
        session = await self._session()
        async with session.put(self.base, json=data) as resp:
            return resp.status == 200

    async def delete_blob(self) -> bool:
        if not self.blob_id:
            return False
        session = await self._session()
        async with session.delete(self.base) as resp:
            ok = resp.status == 200
            if ok:
                self.blob_id = None
                self.base = JSONBLOB_BASE
            return ok

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        await self._mgr.shutdown()
