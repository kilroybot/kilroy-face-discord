from abc import ABC, abstractmethod
from typing import Type

from hikari import Message

from kilroy_face_discord.types import ScoringType


class Scorer(ABC):
    @staticmethod
    @abstractmethod
    async def score(message: Message) -> float:
        pass

    @staticmethod
    @abstractmethod
    def scoring_type() -> ScoringType:
        pass

    @classmethod
    def for_type(cls, scoring_type: ScoringType) -> Type["Scorer"]:
        for scorer in cls.__subclasses__():
            if scorer.scoring_type() == scoring_type:
                return scorer
        raise ValueError(f'Scorer for type "{scoring_type}" not found.')


class ReactionsScorer(Scorer):
    @staticmethod
    async def score(message: Message) -> float:
        return sum(reaction.count for reaction in message.reactions)

    @staticmethod
    def scoring_type() -> ScoringType:
        return "reactions"
