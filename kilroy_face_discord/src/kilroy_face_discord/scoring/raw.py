from abc import ABC, abstractmethod

from hikari import Message, RESTGuild, TextableGuildChannel
from hikari.impl import RESTClientImpl
from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize


class Scorer(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Scorer"))

    @abstractmethod
    async def score(
        self,
        client: RESTClientImpl,
        guild: RESTGuild,
        channel: TextableGuildChannel,
        message: Message,
    ) -> float:
        pass


# Reactions


class RelativeReactionsScorer(Scorer):
    async def score(
        self,
        client: RESTClientImpl,
        guild: RESTGuild,
        channel: TextableGuildChannel,
        message: Message,
    ) -> float:
        reactions = sum(reaction.count for reaction in message.reactions)
        members = guild.approximate_member_count
        return reactions / max(members, 1)
