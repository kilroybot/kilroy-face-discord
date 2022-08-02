from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterable, Generic, Iterable, Optional

from hikari import Message, TextableChannel, UNDEFINED
from kilroy_face_server_py_sdk import (
    BaseState,
    Categorizable,
    ConfigurableWithLoadableState,
    Parameter,
    StateType,
)


class Scraper(
    ConfigurableWithLoadableState[StateType],
    Categorizable,
    Generic[StateType],
    ABC,
):
    @abstractmethod
    def scrap(
        self,
        channel: TextableChannel,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Message]:
        pass


# Basic


@dataclass
class BasicScraperState(BaseState):
    pass


class BasicScraper(Scraper[BasicScraperState]):
    @classmethod
    def category(cls) -> str:
        return "basic"

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def _create_initial_state(self) -> BasicScraperState:
        return BasicScraperState()

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
