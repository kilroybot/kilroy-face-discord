from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Iterable

from hikari import Message
from kilroy_face_server_py_sdk import (
    BaseState,
    Categorizable,
    ConfigurableWithLoadableState,
    Parameter,
    StateType,
)


class Scorer(
    ConfigurableWithLoadableState[StateType],
    Categorizable,
    Generic[StateType],
    ABC,
):
    @abstractmethod
    async def score(self, message: Message) -> float:
        pass


# Reactions


@dataclass
class ReactionsScorerState(BaseState):
    pass


class ReactionsScorer(Scorer[ReactionsScorerState]):
    @classmethod
    def category(cls) -> str:
        return "reactions"

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def _create_initial_state(self) -> ReactionsScorerState:
        return ReactionsScorerState()

    async def score(self, message: Message) -> float:
        return sum(reaction.count for reaction in message.reactions)
