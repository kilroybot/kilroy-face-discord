from abc import ABC, abstractmethod

from hikari import Message
from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize


class Scorer(Categorizable, ABC):
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Scorer"))

    @abstractmethod
    async def score(self, message: Message) -> float:
        pass


# Reactions


class ReactionsScorer(Scorer):
    async def score(self, message: Message) -> float:
        return sum(reaction.count for reaction in message.reactions)
