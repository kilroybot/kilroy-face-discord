import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, AsyncIterable, Dict, Optional, Set, Tuple, Type
from uuid import UUID

from aiostream import stream
from aiostream.aiter_utils import aiter, anext
from hikari import Message, RESTApp, TextableGuildChannel, TokenType
from hikari.impl import RESTClientImpl

from kilroy_face_discord.post import Post
from kilroy_face_discord.posters import Poster, BasicPoster
from kilroy_face_discord.processors import Processor
from kilroy_face_discord.restrictions import Restriction
from kilroy_face_discord.scoring.modifiers import ScoreModifier
from kilroy_face_discord.scoring.raw import Scorer, ReactionsScorer
from kilroy_face_discord.scrapers import Scraper, BasicScraper
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
from kilroy_server_py_utils import (
    CategorizableBasedOptionalParameter,
    Configurable,
)

logger = logging.getLogger(__name__)


class Params(SerializableModel):
    token: str
    scraping_channel_id: int
    posting_channel_id: int
    poster_type: str = "basic"
    posters_params: Dict[str, Dict[str, Any]] = {}
    scorer_type: str = "reactions"
    scorers_params: Dict[str, Dict[str, Any]] = {}
    score_modifier_type: Optional[str] = None
    score_modifiers_params: Dict[str, Dict[str, Any]] = {}
    scraper_type: str = "basic"
    scrapers_params: Dict[str, Dict[str, Any]] = {}
    restriction_type: Optional[str] = None
    restrictions_params: Dict[str, Dict[str, Any]] = {}


@dataclass
class State:
    token: str
    processor: Processor
    poster: Poster
    posters_params: Dict[str, Dict[str, Any]]
    scorer: Scorer
    scorers_params: Dict[str, Dict[str, Any]]
    score_modifier: Optional[ScoreModifier]
    score_modifiers_params: Dict[str, Dict[str, Any]]
    scraper: Scraper
    scrapers_params: Dict[str, Dict[str, Any]]
    restriction: Optional[Restriction]
    restrictions_params: Dict[str, Dict[str, Any]]
    app: RESTApp
    client: Optional[RESTClientImpl]
    scraping_channel: Optional[TextableGuildChannel]
    posting_channel: Optional[TextableGuildChannel]


class PosterParameter(CategorizableBasedParameter[State, Poster]):
    @classmethod
    async def _get_params(cls, state: State, category: str) -> Dict[str, Any]:
        return {**state.posters_params.get(category, {})}

    # noinspection PyMethodParameters
    @classproperty
    def default_categorizable(cls) -> Type[Poster]:
        return BasicPoster


class ScorerParameter(CategorizableBasedParameter[State, Scorer]):
    @classmethod
    async def _get_params(cls, state: State, category: str) -> Dict[str, Any]:
        return {**state.scorers_params.get(category, {})}

    # noinspection PyMethodParameters
    @classproperty
    def default_categorizable(cls) -> Type[Scorer]:
        return ReactionsScorer


class ScoreModifierParameter(
    CategorizableBasedOptionalParameter[State, ScoreModifier]
):
    @classmethod
    async def _get_params(cls, state: State, category: str) -> Dict[str, Any]:
        return {**state.score_modifiers_params.get(category, {})}


class ScraperParameter(CategorizableBasedParameter[State, Scraper]):
    @classmethod
    async def _get_params(cls, state: State, category: str) -> Dict[str, Any]:
        return {**state.scrapers_params.get(category, {})}

    # noinspection PyMethodParameters
    @classproperty
    def default_categorizable(cls) -> Type[Scraper]:
        return BasicScraper


class RestrictionParameter(
    CategorizableBasedOptionalParameter[State, Restriction]
):
    @classmethod
    async def _get_params(cls, state: State, category: str) -> Dict[str, Any]:
        return {**state.restrictions_params.get(category, {})}


class DiscordFaceBase(Face[State], ABC):
    # noinspection PyMethodParameters
    @classproperty
    @abstractmethod
    def post_type(cls) -> str:
        pass

    @staticmethod
    async def _build_app() -> RESTApp:
        return RESTApp()

    @staticmethod
    async def _build_client(params: Params, app: RESTApp) -> RESTClientImpl:
        client = app.acquire(params.token, TokenType.BOT)
        client.start()
        return client

    @staticmethod
    async def _build_channel(
        channel_id: int, client: RESTClientImpl
    ) -> TextableGuildChannel:
        channel = await client.fetch_channel(channel_id)
        if not isinstance(channel, TextableGuildChannel):
            raise ValueError("Channel is not textable.")
        return channel

    @classmethod
    async def _build_scraping_channel(
        cls, params: Params, client: RESTClientImpl
    ) -> TextableGuildChannel:
        return await cls._build_channel(params.scraping_channel_id, client)

    @classmethod
    async def _build_posting_channel(
        cls, params: Params, client: RESTClientImpl
    ) -> TextableGuildChannel:
        return await cls._build_channel(params.posting_channel_id, client)

    @classmethod
    async def _build_processor(cls) -> Processor:
        return await cls._build_generic(Processor, category=cls.post_type)

    @classmethod
    async def _build_poster(cls, params: Params) -> Poster:
        return await cls._build_generic(
            Poster,
            category=params.poster_type,
            **params.posters_params.get(params.poster_type, {}),
        )

    @classmethod
    async def _build_scorer(cls, params: Params) -> Scorer:
        return await cls._build_generic(
            Scorer,
            category=params.scorer_type,
            **params.scorers_params.get(params.scorer_type, {}),
        )

    @classmethod
    async def _build_score_modifier(
        cls, params: Params
    ) -> Optional[ScoreModifier]:
        if params.score_modifier_type is None:
            return None
        return await cls._build_generic(
            ScoreModifier,
            category=params.score_modifier_type,
            **params.score_modifiers_params.get(
                params.score_modifier_type, {}
            ),
        )

    @classmethod
    async def _build_scraper(cls, params: Params) -> Scraper:
        return await cls._build_generic(
            Scraper,
            category=params.scraper_type,
            **params.scrapers_params.get(params.scraper_type, {}),
        )

    @classmethod
    async def _build_restriction(cls, params: Params) -> Optional[Restriction]:
        if params.restriction_type is None:
            return None
        return await cls._build_generic(
            Restriction,
            category=params.restriction_type,
            **params.restrictions_params.get(params.restriction_type, {}),
        )

    async def _build_default_state(self) -> State:
        params = Params(**self._kwargs)
        app = await self._build_app()
        client = await self._build_client(params, app)

        return State(
            token=params.token,
            processor=await self._build_processor(),
            poster=await self._build_poster(params),
            posters_params=params.posters_params,
            scorer=await self._build_scorer(params),
            scorers_params=params.scorers_params,
            score_modifier=await self._build_score_modifier(params),
            score_modifiers_params=params.score_modifiers_params,
            scraper=await self._build_scraper(params),
            scrapers_params=params.scrapers_params,
            restriction=await self._build_restriction(params),
            restrictions_params=params.restrictions_params,
            app=app,
            client=client,
            scraping_channel=await self._build_scraping_channel(
                params, client
            ),
            posting_channel=await self._build_posting_channel(params, client),
        )

    @staticmethod
    async def _save_processor(state: State, directory: Path) -> None:
        if isinstance(state.processor, Savable):
            await state.processor.save(directory / "processor")

    @staticmethod
    async def _save_poster(state: State, directory: Path) -> None:
        if isinstance(state.poster, Savable):
            await state.poster.save(directory / "poster")

    @staticmethod
    async def _save_scorer(state: State, directory: Path) -> None:
        if isinstance(state.scorer, Savable):
            await state.scorer.save(directory / "scorer")

    @staticmethod
    async def _save_score_modifier(state: State, directory: Path) -> None:
        if isinstance(state.score_modifier, Savable):
            await state.score_modifier.save(directory / "score_modifier")

    @staticmethod
    async def _save_scraper(state: State, directory: Path) -> None:
        if isinstance(state.scraper, Savable):
            await state.scraper.save(directory / "scraper")

    @staticmethod
    async def _save_restriction(state: State, directory: Path) -> None:
        if isinstance(state.restriction, Savable):
            await state.restriction.save(directory / "restriction")

    @staticmethod
    async def _create_state_dict(state: State) -> Dict[str, Any]:
        return {
            "processor_type": state.processor.category,
            "poster_type": state.poster.category,
            "scorer_type": state.scorer.category,
            "score_modifier_type": state.score_modifier.category
            if state.score_modifier is not None
            else None,
            "scraper_type": state.scraper.category,
            "restriction_type": state.restriction.category
            if state.restriction is not None
            else None,
            "posters_params": state.posters_params,
            "scorers_params": state.scorers_params,
            "score_modifiers_params": state.score_modifiers_params,
            "scrapers_params": state.scrapers_params,
            "restrictions_params": state.restrictions_params,
        }

    @classmethod
    async def _save_state(cls, state: State, directory: Path) -> None:
        await cls._save_processor(state, directory)
        await cls._save_poster(state, directory)
        await cls._save_scorer(state, directory)
        await cls._save_score_modifier(state, directory)
        await cls._save_scraper(state, directory)
        await cls._save_restriction(state, directory)
        state_dict = await cls._create_state_dict(state)
        await cls._save_state_dict(state_dict, directory)

    @classmethod
    async def _load_processor(
        cls, directory: Path, state_dict: Dict[str, Any]
    ) -> Processor:
        category = state_dict.get("processor_type", cls.post_type)
        return await cls._load_generic(
            directory / "processor",
            Processor,
            category=category,
            default=partial(cls._build_processor),
        )

    @classmethod
    async def _load_poster(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Poster:
        category = state_dict.get("poster_type", params.poster_type)
        return await cls._load_generic(
            directory / "poster",
            Poster,
            category=category,
            **state_dict.get("posters_params", params.posters_params).get(
                category, {}
            ),
            default=partial(cls._build_poster, params),
        )

    @classmethod
    async def _load_scorer(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Scorer:
        category = state_dict.get("scorer_type", params.scorer_type)
        return await cls._load_generic(
            directory / "scorer",
            Scorer,
            category=category,
            **state_dict.get("scorers_params", params.scorers_params).get(
                category, {}
            ),
            default=partial(cls._build_scorer, params),
        )

    @classmethod
    async def _load_score_modifier(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Optional[ScoreModifier]:
        if "score_modifier_type" in state_dict:
            category = state_dict["score_modifier_type"]
        else:
            category = params.score_modifier_type

        if category is None:
            return None
        return await cls._load_generic(
            directory / "score_modifier",
            ScoreModifier,
            category=category,
            **state_dict.get(
                "score_modifiers_params", params.score_modifiers_params
            ).get(category, {}),
            default=partial(cls._build_score_modifier, params),
        )

    @classmethod
    async def _load_scraper(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Scraper:
        category = state_dict.get("scraper_type", params.scraper_type)
        return await cls._load_generic(
            directory / "scraper",
            Scraper,
            category=category,
            **state_dict.get("scrapers_params", params.scrapers_params).get(
                category, {}
            ),
            default=partial(cls._build_scraper, params),
        )

    @classmethod
    async def _load_restriction(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Optional[Restriction]:
        if "restriction_type" in state_dict:
            category = state_dict["restriction_type"]
        else:
            category = params.restriction_type

        if category is None:
            return None
        return await cls._load_generic(
            directory / "restriction",
            Restriction,
            category=category,
            **state_dict.get(
                "restrictions_params", params.restrictions_params
            ).get(category, {}),
            default=partial(cls._build_restriction, params),
        )

    async def _load_saved_state(self, directory: Path) -> State:
        state_dict = await self._load_state_dict(directory)
        params = Params(**self._kwargs)

        app = await self._build_app()
        client = await self._build_client(params, app)

        return State(
            token=params.token,
            processor=await self._load_processor(directory, state_dict),
            poster=await self._load_poster(directory, state_dict, params),
            posters_params=state_dict.get(
                "posters_params", params.posters_params
            ),
            scorer=await self._load_scorer(directory, state_dict, params),
            scorers_params=state_dict.get(
                "scorers_params", params.scorers_params
            ),
            score_modifier=await self._load_score_modifier(
                directory, state_dict, params
            ),
            score_modifiers_params=state_dict.get(
                "score_modifiers_params", params.score_modifiers_params
            ),
            scraper=await self._load_scraper(directory, state_dict, params),
            scrapers_params=state_dict.get(
                "scrapers_params", params.scrapers_params
            ),
            restriction=await self._load_restriction(
                directory, state_dict, params
            ),
            restrictions_params=state_dict.get(
                "restrictions_params", params.restrictions_params
            ),
            app=app,
            client=client,
            scraping_channel=await self._build_scraping_channel(
                params, client
            ),
            posting_channel=await self._build_posting_channel(params, client),
        )

    async def cleanup(self) -> None:
        async with self.state.write_lock() as state:
            if isinstance(state.processor, Configurable):
                await state.processor.cleanup()
            if isinstance(state.poster, Configurable):
                await state.poster.cleanup()
            if isinstance(state.scorer, Configurable):
                await state.scorer.cleanup()
            if isinstance(state.score_modifier, Configurable):
                await state.score_modifier.cleanup()
            if isinstance(state.scraper, Configurable):
                await state.scraper.cleanup()
            if isinstance(state.restriction, Configurable):
                await state.restriction.cleanup()


class DiscordFace(DiscordFaceBase, Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("DiscordFace"))

    # noinspection PyMethodParameters
    @classproperty
    def metadata(cls) -> Metadata:
        return Metadata(
            key="kilroy-face-discord", description="Kilroy face for Discord"
        )

    # noinspection PyMethodParameters
    @classproperty
    def post_type(cls) -> str:
        return cls.category

    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return Processor.for_category(cls.post_type).post_schema

    # noinspection PyMethodParameters
    @classproperty
    def parameters(cls) -> Set[Type[Parameter]]:
        return {
            PosterParameter,
            ScorerParameter,
            ScoreModifierParameter,
            ScraperParameter,
            RestrictionParameter,
        }

    async def cleanup(self) -> None:
        await super().cleanup()
        async with self.state.write_lock() as state:
            await state.client.close()

    async def post(
        self, content: Dict[str, Any]
    ) -> Tuple[UUID, Optional[str]]:
        logger.info("Creating new post...")

        async with self.state.read_lock() as state:
            data = await state.processor.to_internal(content)
            if state.restriction is not None:
                if not await state.restriction.check(data):
                    raise ValueError("Post is not allowed to be posted.")
            post = await state.poster.post(state.posting_channel, data)

        logger.info(f"New post id: {str(post.id)}.")
        return post.id, post.url

    async def score(self, id: UUID) -> float:
        logger.info(f"Scoring post {str(id)}...")

        async with self.state.read_lock() as state:
            message = await state.posting_channel.fetch_message(id.int)
            score = await state.scorer.score(message)
            if state.score_modifier is not None:
                score = await state.score_modifier.modify(message, score)

        logger.info(f"Score for post {str(id)}: {score}.")
        return score

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
                if state.score_modifier is not None:
                    score = await state.score_modifier.modify(message, score)

                try:
                    post = await Post.from_message(message)
                    data = await state.processor.to_external(post.data)
                except Exception:
                    continue

                yield post_id, data, score

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, Dict[str, Any], float]]:
        async with self.state.read_lock() as state:
            messages = state.scraper.scrap(
                state.scraping_channel, before, after
            )

        posts = self._fetch(messages)
        if limit is not None:
            posts = stream.take(posts, limit)
        else:
            posts = stream.iterate(posts)

        logger.info("Scraping posts...")

        async with posts.stream() as streamer:
            async for post_id, post, score in streamer:
                logger.info(f"Scraped post {str(post_id)}.")
                yield post_id, post, score

        logger.info("Scraping finished.")

    async def reset_self(self) -> None:
        logger.info("Resetting state...")
        await super().reset_self()
        logger.info("State reset.")

    async def save_self(self, directory: Path) -> None:
        logger.info("Saving state...")
        await super().save_self(directory)
        logger.info("State saved.")


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
