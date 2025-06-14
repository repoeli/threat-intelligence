## `backend/app/services/virustotal_service.py`
# ─────────────────────────────────────────────────────────────────────
from typing import Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
import asyncio, os

from backend.app.clients.virustotal_client import (
    VirusTotalClient,
    RateLimitError,
    APIError,
)# noqa: E402

# single shared client & thread‑pool
_vt = VirusTotalClient(os.getenv("VIRUSTOTAL_API_KEY"))
_pool = ThreadPoolExecutor(max_workers=8)

async def vt_call(name: str, *, path_params: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None, json: Any = None,
                  files: Any = None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _pool,
        lambda: _vt.call_endpoint(name, path_params=path_params, params=params, json=json, files=files),
    )

# re‑export errors for convenience
RateLimitError = RateLimitError  # type: ignore
APIError       = APIError       # type: ignore
