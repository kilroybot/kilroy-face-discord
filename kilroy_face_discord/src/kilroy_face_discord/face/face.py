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
from kilroy_face_server_py_sdk import JSON, JSONSchema

from kilroy_face_discord.config import FaceConfig
from kilroy_face_discord.face.parameters import Parameter
from kilroy_face_discord.face.processors import Processor
from kilroy_face_discord.face.scorers import Scorer
from kilroy_face_discord.face.scrapers import Scraper
from kilroy_face_discord.face.utils import Configurable
from kilroy_face_discord.types import (
    StateType,
)
from kilroy_face_discord.utils import Deepcopyable


@dataclass
class DiscordFaceState(Deepcopyable):
    token: str
    processor: Processor
    scorer: Scorer
    scraper: Scraper
    app: RESTApp
    client: Optional[RESTClientImpl]
    channel: Optional[TextableChannel]

    async def __adeepcopy_to__(
        self, new: "DiscordFaceState", memo: Dict[int, Any]
    ) -> None:
        new.token = await self.__deepcopy_attribute__("token", memo)
        new.processor = await self.__deepcopy_attribute__("processor", memo)
        new.scorer = await self.__deepcopy_attribute__("scorer", memo)
        new.scraper = await self.__deepcopy_attribute__("scraper", memo)
        new.app = RESTApp()
        new.client = new.app.acquire(self.token, TokenType.BOT)
        new.client.start()
        new.channel = await new.client.fetch_channel(self.channel.id)


class ProcessorParameter(Parameter[DiscordFaceState, JSON]):
    async def _get(self, state: DiscordFaceState) -> JSON:
        return await state.processor.get_config()

    async def _set(self, state: DiscordFaceState, value: JSON) -> None:
        await state.processor.set_config(value)

    def name(self, state: DiscordFaceState) -> str:
        return "processor"

    def schema(self, state: DiscordFaceState) -> JSON:
        return {
            "type": "object",
            "properties": state.processor.config_properties_schema,
        }

    def ui_schema(self, state: StateType) -> JSON:
        return state.processor.config_ui_schema


class ScorerParameter(Parameter[DiscordFaceState, JSON]):
    async def _get(self, state: DiscordFaceState) -> JSON:
        return await state.scorer.get_config()

    async def _set(self, state: DiscordFaceState, value: JSON) -> None:
        await state.scorer.set_config(value)

    def name(self, state: DiscordFaceState) -> str:
        return "scorer"

    def schema(self, state: DiscordFaceState) -> JSON:
        return {
            "type": "object",
            "properties": state.scorer.config_properties_schema,
        }

    def ui_schema(self, state: StateType) -> JSON:
        return state.scorer.config_ui_schema


class ScraperParameter(Parameter[DiscordFaceState, JSON]):
    async def _get(self, state: DiscordFaceState) -> JSON:
        return await state.scraper.get_config()

    async def _set(self, state: DiscordFaceState, value: JSON) -> None:
        await state.scraper.set_config(value)

    def name(self, state: DiscordFaceState) -> str:
        return "scraper"

    def schema(self, state: DiscordFaceState) -> JSON:
        return {
            "type": "object",
            "properties": state.scraper.config_properties_schema,
        }

    def ui_schema(self, state: StateType) -> JSON:
        return state.scraper.config_ui_schema


class DiscordFace(Configurable[DiscordFaceState]):
    async def _create_initial_state(self, config: FaceConfig) -> StateType:
        app = RESTApp()
        client = app.acquire(config.token, TokenType.BOT)
        client.start()
        channel = await client.fetch_channel(config.channel_id)
        if not isinstance(channel, TextableChannel):
            raise ValueError("Channel is not textable.")
        return DiscordFaceState(
            token=config.token,
            processor=await Processor.for_type(config.post_type).build(
                **config.processor_config
            ),
            scorer=await Scorer.for_type(config.scoring_type).build(
                **config.scorer_config
            ),
            scraper=await Scraper.for_type(config.scraping_type).build(
                **config.scraper_config
            ),
            app=app,
            client=client,
            channel=channel,
        )

    @property
    def post_json_schema(self) -> JSONSchema:
        return self._state.processor.post_schema()

    @property
    def _parameters(self) -> Iterable[Parameter]:
        return [ProcessorParameter(), ScorerParameter(), ScraperParameter()]

    @staticmethod
    async def _destroy_state(state: DiscordFaceState) -> None:
        await state.client.close()

    async def post(self, post: JSON) -> UUID:
        message = await self._state.processor.post(self._state.channel, post)
        return UUID(int=message.id)

    async def score(self, post_id: UUID) -> float:
        message = await self._state.channel.fetch_message(post_id.int)
        return await self._state.scorer.score(message)

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
                try:
                    uuid = UUID(int=message.id)
                    yield uuid, await processor.convert(message)
                except Exception:
                    continue

        messages = self._state.scraper.scrap(
            self._state.channel, before, after
        )
        posts = islice(fetch(messages, self._state.processor), limit)

        async for post_id, post in posts:
            yield post_id, post
