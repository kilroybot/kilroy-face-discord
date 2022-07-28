from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterable, Generic, Optional, Type

from hikari import Message, TextableChannel, UNDEFINED

from kilroy_face_discord.face.utils import Configurable
from kilroy_face_discord.types import ScrapingType, StateType
from kilroy_face_discord.utils import Deepcopyable


class Scraper(Configurable[StateType], Generic[StateType], ABC):
    @abstractmethod
    def scrap(
        self,
        channel: TextableChannel,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Message]:
        pass

    @staticmethod
    @abstractmethod
    def scraping_type() -> ScrapingType:
        pass

    @classmethod
    def for_type(cls, scraping_type: ScrapingType) -> Type["Scraper"]:
        for scorer in cls.__subclasses__():
            if scorer.scraping_type() == scraping_type:
                return scorer
        raise ValueError(f'Scraper for type "{scraping_type}" not found.')


# Basic


@dataclass
class BasicScraperState(Deepcopyable):
    pass


class BasicScraper(Scraper[BasicScraperState]):
    async def scrap(
        self,
        channel: TextableChannel,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Message]:
        history = channel.fetch_history(
            before=before or UNDEFINED, after=after or UNDEFINED
        )
        async for message in history:
            if not message.author.is_bot:
                yield message

    @staticmethod
    def scraping_type() -> ScrapingType:
        return "basic"

    async def _create_initial_state(self) -> BasicScraperState:
        return BasicScraperState()
