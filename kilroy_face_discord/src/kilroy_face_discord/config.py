import os

from pydantic import BaseModel

from kilroy_face_discord.types import PostType, ScoringType, ScrapingType


class FaceConfig(BaseModel):
    token: str
    channel_id: int
    post_type: PostType
    scoring_type: ScoringType
    scraping_type: ScrapingType

    @classmethod
    def build(cls, **kwargs) -> "FaceConfig":
        return cls(
            token=kwargs.get("token", os.getenv("KILROY_FACE_DISCORD_TOKEN")),
            channel_id=kwargs.get(
                "channel_id", os.getenv("KILROY_FACE_DISCORD_CHANNEL_ID")
            ),
            post_type=kwargs.get(
                "post_type", os.getenv("KILROY_FACE_DISCORD_POST_TYPE", "text")
            ),
            scoring_type=kwargs.get(
                "scoring_type",
                os.getenv("KILROY_FACE_DISCORD_SCORING_TYPE", "reactions"),
            ),
            scraping_type=kwargs.get(
                "scraping_type",
                os.getenv("KILROY_FACE_DISCORD_SCRAPING_TYPE", "basic"),
            ),
        )


class ServerConfig(BaseModel):
    host: str
    port: int

    @classmethod
    def build(cls, **kwargs) -> "ServerConfig":
        return cls(
            host=kwargs.get(
                "host", os.getenv("KILROY_FACE_DISCORD_HOST", "localhost")
            ),
            port=kwargs.get(
                "port", os.getenv("KILROY_FACE_DISCORD_PORT", 10000)
            ),
        )
