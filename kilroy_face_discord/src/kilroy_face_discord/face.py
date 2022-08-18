from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    AsyncIterable,
    Dict,
    Optional,
    Set,
    Tuple,
)
from uuid import UUID

from aiostream import stream
from hikari import Message, RESTApp, TextableChannel, TokenType
from hikari.impl import RESTClientImpl
from kilroy_face_server_py_sdk import (
    CategorizableBasedParameter,
    Configurable,
    Face,
    JSONSchema,
    Metadata,
    NestedParameter,
    Parameter,
    SerializableModel,
    classproperty,
)
from kilroy_server_py_utils import Categorizable, normalize

from kilroy_face_discord.processors import (
    ImageOnlyProcessor,
    ImageWithOptionalTextProcessor,
    Processor,
    TextAndImageProcessor,
    TextOnlyProcessor,
    TextOrImageProcessor,
    TextWithOptionalImageProcessor,
)
from kilroy_face_discord.scorers import Scorer
from kilroy_face_discord.scrapers import Scraper


class DiscordFaceParams(SerializableModel):
    token: str
    channel_id: int
    processor_params: Dict[str, Dict[str, Any]] = {}
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

    @property
    def metadata(self) -> Metadata:
        return Metadata(
            key="kilroy-face-discord", description="Kilroy face for Discord"
        )

    @classproperty
    def post_type(cls) -> str:
        return cls.category

    @property
    def post_schema(self) -> JSONSchema:
        return Processor.for_category(self.post_type).post_schema

    @classproperty
    @abstractmethod
    def processor_parameter(self) -> Parameter:
        pass

    @classproperty
    def parameters(cls) -> Set[Parameter]:
        return {
            cls.processor_parameter,
            ScorerParameter(),
            ScraperParameter(),
        }

    @staticmethod
    async def _build_app(params: DiscordFaceParams) -> RESTApp:
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
    async def _build_processor(cls, params: DiscordFaceParams) -> Processor:
        processor_cls = Processor.for_category(cls.post_type)
        processor_params = params.processor_params.get(cls.post_type, {})
        if issubclass(processor_cls, Configurable):
            optimizer = await processor_cls.build(**processor_params)
            await optimizer.init()
        else:
            optimizer = processor_cls(**processor_params)
        return optimizer

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
        app = await self._build_app(params)
        client = await self._build_client(params, app)

        return DiscordFaceState(
            token=params.token,
            processor=await self._build_processor(params),
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

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, Dict[str, Any]]]:
        state = await self.state.value.fetch()

        async def fetch(
            msgs: AsyncIterable[Message], processor: Processor
        ) -> AsyncIterable[Tuple[UUID, Dict[str, Any]]]:
            async for message in msgs:
                uuid = UUID(int=message.id)
                try:
                    post = await processor.convert(message)
                except Exception:
                    continue
                yield uuid, post

        messages = state.scraper.scrap(state.channel, before, after)
        posts = fetch(messages, state.processor)
        if limit is not None:
            posts = stream.take(posts, limit)
        else:
            posts = stream.iterate(posts)

        async with posts.stream() as streamer:
            async for post_id, post in streamer:
                yield post_id, post


class TextOnlyDiscordFace(DiscordFace):
    @classproperty
    def processor_parameter(self) -> Parameter:
        class ProcessorParameter(
            NestedParameter[DiscordFaceState, TextOnlyProcessor]
        ):
            pass

        return ProcessorParameter()


class ImageOnlyDiscordFace(DiscordFace):
    @classproperty
    def processor_parameter(self) -> Parameter:
        class ProcessorParameter(
            NestedParameter[DiscordFaceState, ImageOnlyProcessor]
        ):
            pass

        return ProcessorParameter()


class TextAndImageDiscordFace(DiscordFace):
    @classproperty
    def processor_parameter(self) -> Parameter:
        class ProcessorParameter(
            NestedParameter[DiscordFaceState, TextAndImageProcessor]
        ):
            pass

        return ProcessorParameter()


class TextOrImageDiscordFace(DiscordFace):
    @classproperty
    def processor_parameter(self) -> Parameter:
        class ProcessorParameter(
            NestedParameter[DiscordFaceState, TextOrImageProcessor]
        ):
            pass

        return ProcessorParameter()


class TextWithOptionalImageDiscordFace(DiscordFace):
    @classproperty
    def processor_parameter(self) -> Parameter:
        class ProcessorParameter(
            NestedParameter[DiscordFaceState, TextWithOptionalImageProcessor]
        ):
            pass

        return ProcessorParameter()


class ImageWithOptionalTextDiscordFace(DiscordFace):
    @classproperty
    def processor_parameter(self) -> Parameter:
        class ProcessorParameter(
            NestedParameter[DiscordFaceState, ImageWithOptionalTextProcessor]
        ):
            pass

        return ProcessorParameter()
