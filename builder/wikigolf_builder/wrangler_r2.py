"""Read/write R2 objects through the `wrangler` CLI, using the owner's `wrangler login`.

This lets `show` and `approve` run with no R2 S3 keys — handy before the enwiki launch, when the
owner just wants to review and approve from their machine. Only get/put are needed (the index and
hole JSON); listing/copy/delete stay on the boto3 backend (`upload.R2`), used by CI and admin.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from .config import REPO_ROOT

BUCKET = "wiki-golf"


class WranglerR2:
    def __init__(self, bucket: str = BUCKET, remote: bool = True) -> None:
        self.bucket = bucket
        self.remote = remote
        self.puts = 0
        # Prefer a wrangler on PATH; otherwise the repo's workspace binary via npx.
        self.base = ["wrangler"] if shutil.which("wrangler") else ["npx", "--yes", "wrangler"]

    def _object_args(self, verb: str, key: str, extra: list[str]) -> list[str]:
        args = [*self.base, "r2", "object", verb, f"{self.bucket}/{key}", *extra]
        if self.remote:
            args.append("--remote")
        return args

    def _run(self, args: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=REPO_ROOT, input=stdin, capture_output=True, check=False)

    def get_json(self, key: str):
        proc = self._run(self._object_args("get", key, ["--pipe"]))
        if proc.returncode != 0:
            err = proc.stderr.decode(errors="replace")
            if any(s in err.lower() for s in ("not found", "does not exist", "404", "no such key")):
                return None
            raise RuntimeError(f"wrangler r2 object get {key} failed:\n{err.strip()}")
        return json.loads(proc.stdout)

    def put_json(self, key: str, data) -> None:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        fd, tmp = tempfile.mkstemp(suffix=".json")
        try:
            os.write(fd, body)
            os.close(fd)
            extra = ["--file", tmp, "--content-type", "application/json"]
            proc = self._run(self._object_args("put", key, extra))
            if proc.returncode != 0:
                raise RuntimeError(
                    f"wrangler r2 object put {key} failed:\n{proc.stderr.decode(errors='replace').strip()}"
                )
            self.puts += 1
        finally:
            os.unlink(tmp)
