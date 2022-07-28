from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Type

from hikari import Message

from kilroy_face_discord.face.utils import Configurable
from kilroy_face_discord.types import ScoringType, StateType
from kilroy_face_discord.utils import Deepcopyable


class Scorer(Configurable[StateType], Generic[StateType], ABC):
    @abstractmethod
    async def score(self, message: Message) -> float:
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


# Reactions


@dataclass
class ReactionsScorerState(Deepcopyable):
    pass


class ReactionsScorer(Scorer[ReactionsScorerState]):
    async def score(self, message: Message) -> float:
        return sum(reaction.count for reaction in message.reactions)

    @staticmethod
    def scoring_type() -> ScoringType:
        return "reactions"

    async def _create_initial_state(self) -> ReactionsScorerState:
        return ReactionsScorerState()
