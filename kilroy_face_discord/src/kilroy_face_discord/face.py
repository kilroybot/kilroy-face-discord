from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterable, Dict, Optional, Set, Tuple
from uuid import UUID

from aiostream import stream
from aiostream.aiter_utils import aiter, anext
from hikari import Message, RESTApp, TextableChannel, TokenType
from hikari.impl import RESTClientImpl
from kilroy_face_server_py_sdk import (
    Categorizable,
    CategorizableBasedParameter,
    Configurable,
    Face,
    JSONSchema,
    Metadata,
    Parameter,
    SerializableModel,
    classproperty,
    normalize,
)

from kilroy_face_discord.processors import Processor
from kilroy_face_discord.scorers import Scorer
from kilroy_face_discord.scrapers import Scraper


class DiscordFaceParams(SerializableModel):
    token: str
    channel_id: int
    scoring_type: str
    scorers_params: Dict[str, Dict[str, Any]] = {}
    scraping_type: str
    scrapers_params: Dict[str, Dict[str, Any]] = {}


@dataclass
class DiscordFaceState:
    token: str
    processor: Processor
    scorer: Scorer
    scorers_params: Dict[str, Dict[str, Any]]
    scraper: Scraper
    scrapers_params: Dict[str, Dict[str, Any]]
    app: RESTApp
    client: Optional[RESTClientImpl]
    channel: Optional[TextableChannel]


class ScorerParameter(CategorizableBasedParameter[DiscordFaceState, Scorer]):
    async def _get_params(
        self, state: DiscordFaceState, category: str
    ) -> Dict[str, Any]:
        return {**state.scorers_params.get(category, {})}


class ScraperParameter(CategorizableBasedParameter[DiscordFaceState, Scraper]):
    async def _get_params(
        self, state: DiscordFaceState, category: str
    ) -> Dict[str, Any]:
        return {**state.scrapers_params.get(category, {})}


class DiscordFace(Categorizable, Face[DiscordFaceState], ABC):
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("DiscordFace"))

    @classproperty
    def metadata(cls) -> Metadata:
        return Metadata(
            key="kilroy-face-discord", description="Kilroy face for Discord"
        )

    @classproperty
    def post_type(cls) -> str:
        return cls.category

    @classproperty
    def post_schema(cls) -> JSONSchema:
        return Processor.for_category(cls.post_type).post_schema

    @classproperty
    def parameters(cls) -> Set[Parameter]:
        return {ScorerParameter(), ScraperParameter()}

    @staticmethod
    async def _build_app() -> RESTApp:
        return RESTApp()

    @staticmethod
    async def _build_client(
        params: DiscordFaceParams, app: RESTApp
    ) -> RESTClientImpl:
        client = app.acquire(params.token, TokenType.BOT)
        client.start()
        return client

    @staticmethod
    async def _build_channel(
        params: DiscordFaceParams, client: RESTClientImpl
    ) -> TextableChannel:
        channel = await client.fetch_channel(params.channel_id)
        if not isinstance(channel, TextableChannel):
            raise ValueError("Channel is not textable.")
        return channel

    @classmethod
    async def _build_processor(cls) -> Processor:
        return Processor.for_category(cls.post_type)()

    @staticmethod
    async def _build_scorer(params: DiscordFaceParams) -> Scorer:
        scorer_cls = Scorer.for_category(params.scoring_type)
        scorer_params = params.scorers_params.get(params.scoring_type, {})
        if issubclass(scorer_cls, Configurable):
            scorer = await scorer_cls.build(**scorer_params)
            await scorer.init()
        else:
            scorer = scorer_cls(**scorer_params)
        return scorer

    @staticmethod
    async def _build_scraper(params: DiscordFaceParams) -> Scraper:
        scraper_cls = Scraper.for_category(params.scraping_type)
        scraper_params = params.scrapers_params.get(params.scraping_type, {})
        if issubclass(scraper_cls, Configurable):
            scraper = await scraper_cls.build(**scraper_params)
            await scraper.init()
        else:
            scraper = scraper_cls(**scraper_params)
        return scraper

    async def build_default_state(self) -> DiscordFaceState:
        params = DiscordFaceParams(**self._kwargs)
        app = await self._build_app()
        client = await self._build_client(params, app)

        return DiscordFaceState(
            token=params.token,
            processor=await self._build_processor(),
            scorer=await self._build_scorer(params),
            scorers_params=params.scorers_params,
            scraper=await self._build_scraper(params),
            scrapers_params=params.scrapers_params,
            app=app,
            client=client,
            channel=await self._build_channel(params, client),
        )

    async def cleanup(self) -> None:
        async with self.state.write_lock() as state:
            await state.client.close()

    async def post(self, post: Dict[str, Any]) -> UUID:
        async with self.state.read_lock() as state:
            return await state.processor.post(state.channel, post)

    async def score(self, post_id: UUID) -> float:
        async with self.state.read_lock() as state:
            message = await state.channel.fetch_message(post_id.int)
            return await state.scorer.score(message)

    async def _fetch(
        self,
        messages: AsyncIterable[Message],
    ) -> AsyncIterable[Tuple[UUID, Dict[str, Any], float]]:
        messages = aiter(messages)

        while True:
            async with self.state.read_lock() as state:
                try:
                    message = await anext(messages)
                except StopAsyncIteration:
                    break

                post_id = UUID(int=message.id)
                score = await state.scorer.score(message)

                try:
                    post = await state.processor.convert(message)
                except Exception:
                    continue

                yield post_id, post, score

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, Dict[str, Any], float]]:
        async with self.state.read_lock() as state:
            messages = state.scraper.scrap(state.channel, before, after)

        posts = self._fetch(messages)
        if limit is not None:
            posts = stream.take(posts, limit)
        else:
            posts = stream.iterate(posts)

        async with posts.stream() as streamer:
            async for post_id, post, score in streamer:
                yield post_id, post, score


class TextOnlyDiscordFace(DiscordFace):
    pass


class ImageOnlyDiscordFace(DiscordFace):
    pass


class TextAndImageDiscordFace(DiscordFace):
    pass


class TextOrImageDiscordFace(DiscordFace):
    pass


class TextWithOptionalImageDiscordFace(DiscordFace):
    pass


class ImageWithOptionalTextDiscordFace(DiscordFace):
    pass
