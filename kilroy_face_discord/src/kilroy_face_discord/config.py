import os
from typing import Any, Dict

from pydantic import BaseModel


class FaceConfig(BaseModel):
    token: str
    channel_id: int
    post_type: str
    processors_params: Dict[str, Dict[str, Any]] = {}
    default_scoring_type: str
    scorers_params: Dict[str, Dict[str, Any]] = {}
    default_scraping_type: str
    scrapers_params: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def build(cls, **kwargs) -> "FaceConfig":
        return cls(
            token=kwargs.get(
                "token",
                os.getenv("KILROY_FACE_DISCORD_TOKEN"),
            ),
            channel_id=kwargs.get(
                "channel_id",
                os.getenv("KILROY_FACE_DISCORD_CHANNEL_ID"),
            ),
            post_type=kwargs.get(
                "post_type",
                os.getenv(
                    "KILROY_FACE_DISCORD_POST_TYPE",
                    "text-or-image",
                ),
            ),
            default_scoring_type=kwargs.get(
                "scoring_type",
                os.getenv(
                    "KILROY_FACE_DISCORD_DEFAULT_SCORING_TYPE",
                    "reactions",
                ),
            ),
            default_scraping_type=kwargs.get(
                "scraping_type",
                os.getenv(
                    "KILROY_FACE_DISCORD_DEFAULT_SCRAPING_TYPE",
                    "basic",
                ),
            ),
        )


class ServerConfig(BaseModel):
    host: str
    port: int

    @classmethod
    def build(cls, **kwargs) -> "ServerConfig":
        return cls(
            host=kwargs.get(
                "host",
                os.getenv(
                    "KILROY_FACE_DISCORD_HOST",
                    "localhost",
                ),
            ),
            port=kwargs.get(
                "port",
                os.getenv(
                    "KILROY_FACE_DISCORD_PORT",
                    10000,
                ),
            ),
        )
