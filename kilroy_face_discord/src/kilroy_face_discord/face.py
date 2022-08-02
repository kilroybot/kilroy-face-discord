from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    AsyncIterable,
    Dict,
    Iterable,
    Optional,
    Tuple,
)
from uuid import UUID

from asyncstdlib import islice
from hikari import Message, RESTApp, TextableChannel, TokenType
from hikari.impl import RESTClientImpl
from kilroy_face_server_py_sdk import (
    BaseState,
    Face,
    JSON,
    JSONSchema,
    Parameter,
)

from kilroy_face_discord.config import FaceConfig
from kilroy_face_discord.processors import Processor
from kilroy_face_discord.scorers import Scorer
from kilroy_face_discord.scrapers import Scraper


@dataclass
class DiscordFaceState(BaseState):
    token: str
    processor: Processor
    scoring_type: str
    scorers: Dict[str, Scorer]
    scraping_type: str
    scrapers: Dict[str, Scraper]
    app: RESTApp
    client: Optional[RESTClientImpl]
    channel: Optional[TextableChannel]

    @property
    def scorer(self) -> Scorer:
        return self.scorers[self.scoring_type]

    @property
    def scraper(self) -> Scraper:
        return self.scrapers[self.scraping_type]

    async def __adestroy__(self) -> None:
        await self.client.close()

    async def __adeepcopy_to__(
        self, new: "DiscordFaceState", memo: Dict[int, Any]
    ) -> None:
        for attr in (
            "token",
            "processor",
            "scoring_type",
            "scorers",
            "scraping_type",
            "scrapers",
        ):
            setattr(new, attr, await self.__deepcopy_attribute__(attr, memo))
        new.app = RESTApp()
        new.client = new.app.acquire(self.token, TokenType.BOT)
        new.client.start()
        new.channel = await new.client.fetch_channel(self.channel.id)


class ProcessorParameter(Parameter[DiscordFaceState, JSON]):
    async def _get(self, state: DiscordFaceState) -> JSON:
        return await state.processor.config.get()

    async def _set(self, state: DiscordFaceState, value: JSON) -> None:
        await state.processor.config.set(value)

    async def name(self, state: DiscordFaceState) -> str:
        return "processor"

    async def schema(self, state: DiscordFaceState) -> JSON:
        return {
            "type": "object",
            "properties": await state.processor.config.get_properties_schema(),
        }


class ScorerParameter(Parameter[DiscordFaceState, JSON]):
    async def _get(self, state: DiscordFaceState) -> JSON:
        return {
            "type": state.scoring_type,
            "config": await state.scorer.config.get(),
        }

    async def _set(self, state: DiscordFaceState, value: JSON) -> None:
        state.scoring_type = value["type"]
        await state.scorer.config.set(value["config"])

    async def name(self, state: DiscordFaceState) -> str:
        return "scorer"

    async def schema(self, state: DiscordFaceState) -> JSON:
        return {
            "type": "object",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "const": scoring_type,
                        },
                        "config": {
                            "type": "object",
                            "properties": await state.scorers[
                                scoring_type
                            ].config.get_properties_schema(),
                        },
                    },
                }
                for scoring_type in Scorer.all_categories()
            ],
        }


class ScraperParameter(Parameter[DiscordFaceState, JSON]):
    async def _get(self, state: DiscordFaceState) -> JSON:
        return {
            "type": state.scraping_type,
            "config": await state.scraper.config.get(),
        }

    async def _set(self, state: DiscordFaceState, value: JSON) -> None:
        state.scraping_type = value["type"]
        await state.scraper.config.set(value["config"])

    async def name(self, state: DiscordFaceState) -> str:
        return "scraper"

    async def schema(self, state: DiscordFaceState) -> JSON:
        return {
            "type": "object",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "const": scraping_type,
                        },
                        "config": {
                            "type": "object",
                            "properties": await state.scrapers[
                                scraping_type
                            ].config.get_properties_schema(),
                        },
                    },
                }
                for scraping_type in Scraper.all_categories()
            ],
        }


class DiscordFace(Face[DiscordFaceState]):
    def __init__(self, config: FaceConfig) -> None:
        super().__init__()
        self._face_config = config

    async def _create_initial_state(self) -> DiscordFaceState:
        app = RESTApp()
        client = app.acquire(self._face_config.token, TokenType.BOT)
        client.start()
        channel = await client.fetch_channel(self._face_config.channel_id)
        if not isinstance(channel, TextableChannel):
            raise ValueError("Channel is not textable.")
        return DiscordFaceState(
            token=self._face_config.token,
            processor=await Processor.for_category(
                self._face_config.post_type
            ).build(
                **self._face_config.processors_params.get(
                    self._face_config.post_type, {}
                )
            ),
            scoring_type=self._face_config.default_scoring_type,
            scorers={
                scoring_type: await Scorer.for_category(scoring_type).build(
                    **self._face_config.scorers_params.get(scoring_type, {})
                )
                for scoring_type in Scorer.all_categories()
            },
            scraping_type=self._face_config.default_scraping_type,
            scrapers={
                scraping_type: await Scraper.for_category(scraping_type).build(
                    **self._face_config.scrapers_params.get(scraping_type, {})
                )
                for scraping_type in Scraper.all_categories()
            },
            app=app,
            client=client,
            channel=channel,
        )

    @property
    def post_schema(self) -> JSONSchema:
        return self.state.processor.post_schema()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return [ProcessorParameter(), ScorerParameter(), ScraperParameter()]

    async def post(self, post: JSON) -> UUID:
        return await self.state.processor.post(self.state.channel, post)

    async def score(self, post_id: UUID) -> float:
        message = await self.state.channel.fetch_message(post_id.int)
        return await self.state.scorer.score(message)

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, JSON]]:
        async def fetch(
            msgs: AsyncIterable[Message], processor: Processor
        ) -> AsyncIterable[Tuple[UUID, JSON]]:
            async for message in msgs:
                uuid = UUID(int=message.id)
                try:
                    post = await processor.convert(message)
                except Exception:
                    continue
                yield uuid, post

        messages = self.state.scraper.scrap(self.state.channel, before, after)
        posts = islice(fetch(messages, self.state.processor), limit)

        async for post_id, post in posts:
            yield post_id, post
