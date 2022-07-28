from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from kilroy_ws_server_py_sdk import AppError, JSON

from kilroy_face_discord.errors import PARAMETER_GET_ERROR, PARAMETER_SET_ERROR
from kilroy_face_discord.types import StateType

ParameterType = TypeVar("ParameterType")


class Parameter(ABC, Generic[StateType, ParameterType]):
    async def get(self, state: StateType) -> ParameterType:
        try:
            return await self._get(state)
        except AppError as e:
            raise e
        except Exception as e:
            raise PARAMETER_GET_ERROR from e

    async def set(
        self,
        state: StateType,
        value: ParameterType,
    ) -> None:
        if (await self.get(state)) == value:
            return
        try:
            await self._set(state, value)
        except AppError as e:
            raise e
        except Exception as e:
            raise PARAMETER_SET_ERROR from e

    @abstractmethod
    async def _get(self, state: StateType) -> ParameterType:
        pass

    @abstractmethod
    async def _set(
        self,
        state: StateType,
        value: ParameterType,
    ) -> None:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def schema(self) -> JSON:
        pass

    @property
    def ui_schema(self) -> JSON:
        return {}
