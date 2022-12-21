from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterable, Optional

from hikari import Message, TextableGuildChannel, UNDEFINED
from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize


class Scraper(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Scraper"))

    @abstractmethod
    def scrap(
        self,
        channel: TextableGuildChannel,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Message]:
        pass


# Basic


class BasicScraper(Scraper):
    async def scrap(
        self,
        channel: TextableGuildChannel,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Message]:
        history = channel.fetch_history(
            before=before or UNDEFINED, after=after or UNDEFINED
        )
        async for message in history:
            if not message.author.is_bot:
                yield message
