"""Upload to R2 through its S3-compatible API. Never deletes; never overwrites a hole."""

from __future__ import annotations

import json
import os
from pathlib import Path

BUCKET = "wiki-golf"
CONTENT_TYPES = {".json": "application/json", ".bin": "application/octet-stream"}


class R2:
    def __init__(self, bucket: str = BUCKET) -> None:
        import boto3
        from botocore.config import Config

        missing = [
            k
            for k in ("CLOUDFLARE_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
            if not os.environ.get(k)
        ]
        if missing:
            raise SystemExit(f"Missing environment variables for R2: {', '.join(missing)}")
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{os.environ['CLOUDFLARE_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
            config=Config(retries={"max_attempts": 8, "mode": "standard"}),
        )
        self.puts = 0

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as err:
            if err.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def get_json(self, key: str):
        from botocore.exceptions import ClientError

        try:
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as err:
            if err.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return json.loads(body)

    def put_file(self, key: str, path: Path) -> None:
        ctype = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self.client.upload_file(str(path), self.bucket, key, ExtraArgs={"ContentType": ctype})
        self.puts += 1

    def put_json(self, key: str, data) -> None:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=body, ContentType="application/json"
        )
        self.puts += 1


def key_for(path: Path, out: Path) -> str:
    return path.relative_to(out).as_posix()
