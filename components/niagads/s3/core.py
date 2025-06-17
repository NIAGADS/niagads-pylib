from threading import Lock
from typing import Any

import boto3
from botocore.config import Config
from niagads.settings.core import CustomSettings
from pydantic import SecretStr


class AwsSettings(CustomSettings):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: SecretStr  # Use SecretStr for sensitive data
    AWS_REGION_NAME: str = "us-east-1"
    S3_BUCKET: str


class S3ClientManager:
    _client = None
    _lock = Lock()

    def __init__(self, settings: AwsSettings):
        self.settings = settings

    def get_client(self) -> Any:
        if not self._client:
            with self._lock:
                if not self._client:
                    self._client = boto3.client(
                        "s3",
                        aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                        region_name=self.settings.AWS_REGION_NAME,
                        config=Config(max_pool_connections=20),  # for multi-threading
                    )
        return self._client

    def get_bucket(self) -> str:
        return self.settings.S3_BUCKET

    def __call__(self) -> str:
        return self.get_client()
