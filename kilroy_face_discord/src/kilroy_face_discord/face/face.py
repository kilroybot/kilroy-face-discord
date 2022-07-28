from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import (
    AsyncIterable,
    Iterable,
    Optional,
    Tuple,
    Type,
)
from uuid import UUID

from asyncstdlib import islice
from hikari import Message, RESTApp, TextableChannel, TokenType
from hikari.impl import RESTClientImpl
from kilroy_face_server_py_sdk import JSON, JSONSchema

from kilroy_face_discord.config import FaceConfig
from kilroy_face_discord.face.parameters import Parameter
from kilroy_face_discord.face.processors import Processor
from kilroy_face_discord.face.scorers import Scorer
from kilroy_face_discord.face.scrapers import Scraper
from kilroy_face_discord.face.utils import Configurable
from kilroy_face_discord.types import PostType, ScoringType, ScrapingType


@dataclass
class DiscordFaceState:
    token: str
    post_type: PostType
    scoring_type: ScoringType
    scraping_type: ScrapingType
    app: RESTApp
    client: Optional[RESTClientImpl]
    channel: Optional[TextableChannel]


class DiscordFace(Configurable[DiscordFaceState]):
    @classmethod
    async def build(cls, config: FaceConfig) -> "DiscordFace":
        face = cls()
        app = RESTApp()
        client = app.acquire(config.token, TokenType.BOT)
        client.start()
        channel = await client.fetch_channel(config.channel_id)
        if not isinstance(channel, TextableChannel):
            raise ValueError("Channel is not textable.")
        await face._initialize_state(
            DiscordFaceState(
                token=config.token,
                post_type=config.post_type,
                scoring_type=config.scoring_type,
                scraping_type=config.scraping_type,
                app=app,
                client=client,
                channel=channel,
            )
        )
        return face

    @property
    def _parameters(self) -> Iterable[Parameter]:
        return []

    @property
    def post_schema(self) -> JSONSchema:
        return self._processor.post_schema()

    @staticmethod
    async def _copy_state(state: DiscordFaceState) -> DiscordFaceState:
        return deepcopy(state)

    @staticmethod
    async def _destroy_state(state: DiscordFaceState) -> None:
        await state.client.close()

    @property
    def _processor(self) -> Type[Processor]:
        return Processor.for_type(self._state.post_type)

    @property
    def _scorer(self) -> Type[Scorer]:
        return Scorer.for_type(self._state.scoring_type)

    @property
    def _scraper(self) -> Type[Scraper]:
        return Scraper.for_type(self._state.scraping_type)

    async def post(self, post: JSON) -> UUID:
        message = await self._processor.post(self._state.channel, post)
        return UUID(int=message.id)

    async def score(self, post_id: UUID) -> float:
        message = await self._state.channel.fetch_message(post_id.int)
        return await self._scorer.score(message)

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, JSON]]:
        async def fetch(
            msgs: AsyncIterable[Message], processor: Type[Processor]
        ) -> AsyncIterable[Tuple[UUID, JSON]]:
            async for message in msgs:
                try:
                    uuid = UUID(int=message.id)
                    yield uuid, await processor.convert(message)
                except Exception:
                    continue

        messages = self._scraper.scrap(self._state.channel, before, after)
        posts = islice(fetch(messages, self._processor), limit)

        async for post_id, post in posts:
            yield post_id, post
