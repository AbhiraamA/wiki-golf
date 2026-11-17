"""HTTP to Wikimedia: one connection, a proper User-Agent, and backoff on 429 and 5xx."""

from __future__ import annotations

import io
import time

import requests
from requests.adapters import HTTPAdapter

from .config import USER_AGENT

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_TRIES = 8


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    # A single pooled connection per host: dumps are fetched one file at a time.
    adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1)
    s.mount("https://", adapter)
    return s


def _sleep_for(resp: requests.Response | None, attempt: int) -> float:
    if resp is not None:
        retry_after = resp.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return min(float(retry_after), 300.0)
    return min(2.0**attempt, 120.0)


def get(session: requests.Session, url: str, *, stream: bool = False, headers=None):
    """GET with retries on 429/5xx and connection errors. Raises for other 4xx."""
    for attempt in range(MAX_TRIES):
        resp = None
        try:
            resp = session.get(url, stream=stream, timeout=(15, 120), headers=headers)
            if resp.status_code not in RETRY_STATUS:
                resp.raise_for_status()
                return resp
            resp.close()
        except (requests.ConnectionError, requests.Timeout):
            pass
        if attempt == MAX_TRIES - 1:
            break
        time.sleep(_sleep_for(resp, attempt))
    raise RuntimeError(f"GET {url} failed after {MAX_TRIES} tries")


class ResumableStream(io.RawIOBase):
    """Read-only byte stream over HTTP that resumes with a Range request if the connection drops."""

    def __init__(self, session: requests.Session, url: str) -> None:
        self.session = session
        self.url = url
        self.pos = 0
        self.resumes = 0
        self._resp = get(session, url, stream=True)

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        while True:
            try:
                n = self._resp.raw.readinto(b)
                self.pos += n
                return n
            except (requests.ConnectionError, requests.Timeout, OSError) as err:
                self.resumes += 1
                if self.resumes > MAX_TRIES:
                    raise RuntimeError(f"Download of {self.url} kept failing") from err
                self._resp.close()
                time.sleep(_sleep_for(None, self.resumes))
                self._resp = get(
                    self.session, self.url, stream=True, headers={"Range": f"bytes={self.pos}-"}
                )
                if self._resp.status_code != 206:
                    raise RuntimeError(f"Server ignored Range for {self.url}") from err

    def close(self) -> None:
        self._resp.close()
        super().close()
