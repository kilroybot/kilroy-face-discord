import json
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterable, Dict, Optional, Set, Tuple
from uuid import UUID

from aiostream import stream
from aiostream.aiter_utils import aiter, anext
from hikari import Message, RESTApp, TextableChannel, TokenType
from hikari.impl import RESTClientImpl
from kilroy_face_server_py_sdk import (
    Categorizable,
    CategorizableBasedParameter,
    Face,
    JSONSchema,
    Metadata,
    Parameter,
    Savable,
    SerializableModel,
    classproperty,
    normalize,
)

from kilroy_face_discord.processors import Processor
from kilroy_face_discord.scorers import Scorer
from kilroy_face_discord.scrapers import Scraper


class Params(SerializableModel):
    token: str
    channel_id: int
    scoring_type: str
    scorers_params: Dict[str, Dict[str, Any]] = {}
    scraping_type: str
    scrapers_params: Dict[str, Dict[str, Any]] = {}


@dataclass
class State:
    token: str
    processor: Processor
    scorer: Scorer
    scorers_params: Dict[str, Dict[str, Any]]
    scraper: Scraper
    scrapers_params: Dict[str, Dict[str, Any]]
    app: RESTApp
    client: Optional[RESTClientImpl]
    channel: Optional[TextableChannel]


class ScorerParameter(CategorizableBasedParameter[State, Scorer]):
    async def _get_params(self, state: State, category: str) -> Dict[str, Any]:
        return {**state.scorers_params.get(category, {})}


class ScraperParameter(CategorizableBasedParameter[State, Scraper]):
    async def _get_params(self, state: State, category: str) -> Dict[str, Any]:
        return {**state.scrapers_params.get(category, {})}


class DiscordFace(Categorizable, Face[State], ABC):
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
    async def _build_client(token: str, app: RESTApp) -> RESTClientImpl:
        client = app.acquire(token, TokenType.BOT)
        client.start()
        return client

    @staticmethod
    async def _build_channel(
        channel_id: int, client: RESTClientImpl
    ) -> TextableChannel:
        channel = await client.fetch_channel(channel_id)
        if not isinstance(channel, TextableChannel):
            raise ValueError("Channel is not textable.")
        return channel

    @classmethod
    async def _build_processor(cls) -> Processor:
        return await cls.build_generic(Processor, category=cls.post_type)

    @classmethod
    async def _build_scorer(
        cls, scoring_type: str, scorers_params: Dict[str, Dict[str, Any]]
    ) -> Scorer:
        return await cls.build_generic(
            Scorer,
            category=scoring_type,
            **scorers_params.get(scoring_type, {}),
        )

    @classmethod
    async def _build_scraper(
        cls, scraping_type: str, scrapers_params: Dict[str, Dict[str, Any]]
    ) -> Scraper:
        return await cls.build_generic(
            Scraper,
            category=scraping_type,
            **scrapers_params.get(scraping_type, {}),
        )

    async def build_default_state(self) -> State:
        params = Params(**self._kwargs)
        app = await self._build_app()
        client = await self._build_client(params.token, app)

        return State(
            token=params.token,
            processor=await self._build_processor(),
            scorer=await self._build_scorer(
                params.scoring_type, params.scorers_params
            ),
            scorers_params=params.scorers_params,
            scraper=await self._build_scraper(
                params.scraping_type, params.scrapers_params
            ),
            scrapers_params=params.scrapers_params,
            app=app,
            client=client,
            channel=await self._build_channel(params.channel_id, client),
        )

    @classmethod
    async def save_state(cls, state: State, directory: Path) -> None:
        if isinstance(state.processor, Savable):
            await state.processor.save(directory)
        if isinstance(state.scorer, Savable):
            await state.scorer.save(directory)
        if isinstance(state.scraper, Savable):
            await state.scraper.save(directory)

        state_dict = {
            "processor_type": state.processor.category,
            "scoring_type": state.scorer.category,
            "scrapers_params": state.scrapers_params,
            "scorers_params": state.scorers_params,
            "scraping_type": state.scraper.category,
            "channel_id": state.channel.id,
        }

        with open(directory / "state.json", "w") as f:
            json.dump(state_dict, f)

    async def load_saved_state(self, directory: Path) -> State:
        with open(directory / "state.json", "r") as f:
            state_dict = json.load(f)

        params = Params(**self._kwargs)

        app = await self._build_app()
        client = await self._build_client(params.token, app)

        return State(
            token=params.token,
            processor=await self.load_generic(
                directory, Processor, category=state_dict["processor_type"]
            ),
            scorer=await self.load_generic(
                directory,
                Scorer,
                category=state_dict["scoring_type"],
                **state_dict["scorers_params"].get(
                    state_dict["scoring_type"], {}
                ),
            ),
            scorers_params=state_dict["scorers_params"],
            scraper=await self.load_generic(
                directory,
                Scraper,
                category=state_dict["scraping_type"],
                **state_dict["scrapers_params"].get(
                    state_dict["scraping_type"], {}
                ),
            ),
            scrapers_params=state_dict["scrapers_params"],
            app=app,
            client=client,
            channel=await self._build_channel(
                state_dict["channel_id"], client
            ),
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
