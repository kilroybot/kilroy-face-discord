from abc import ABC, abstractmethod
from asyncio import Queue
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncIterable,
    Dict,
    Generic,
    Iterable,
)
from uuid import uuid4

from kilroy_face_server_py_sdk import JSONSchema
from kilroy_ws_server_py_sdk import JSON

from kilroy_face_discord.errors import (
    INVALID_CONFIG_ERROR,
    STATE_NOT_READY_ERROR,
)
from kilroy_face_discord.face.parameters import Parameter
from kilroy_face_discord.types import StateType


class Observable(ABC):
    _queues: Dict[str, Dict[Any, Queue]]

    def __init__(self) -> None:
        self._queues = {}

    @asynccontextmanager
    async def _create_queue(self, topic: str) -> Queue:
        queue_id = uuid4()
        queue = Queue()

        if topic not in self._queues:
            self._queues[topic] = {}
        self._queues[topic][queue_id] = queue

        yield queue

        self._queues[topic].pop(queue_id)
        if len(self._queues[topic]) == 0:
            self._queues.pop(topic)

    async def _subscribe(self, topic: str) -> AsyncIterable[Any]:
        async with self._create_queue(topic) as queue:
            while (message := await queue.get()) is not None:
                yield message

    async def _notify(self, topic: str, message: Any) -> None:
        for queue in self._queues.get(topic, {}).values():
            await queue.put(message)


class Loadable(Observable, Generic[StateType], ABC):
    __state: StateType
    __ready: bool

    def __init__(self) -> None:
        super().__init__()
        self.__ready = False

    async def _initialize_state(self, state: StateType) -> None:
        self.__state = state
        await self._set_ready(True)

    async def cleanup(self) -> None:
        await self._destroy_state(self.__state)

    async def _set_ready(self, value: bool) -> None:
        self.__ready = value
        await self._notify("ready", value)

    @asynccontextmanager
    async def _loading(self) -> StateType:
        await self._set_ready(False)
        try:
            state = await self._copy_state(self.__state)
            yield state
            old_state = self.__state
            self.__state = state
            await self._destroy_state(old_state)
        finally:
            await self._set_ready(True)

    @property
    def _state(self) -> StateType:
        if not self.__ready:
            raise STATE_NOT_READY_ERROR
        return self.__state

    @staticmethod
    @abstractmethod
    async def _copy_state(state: StateType) -> StateType:
        pass

    @staticmethod
    @abstractmethod
    async def _destroy_state(state: StateType) -> None:
        pass

    async def is_ready(self) -> bool:
        return self.__ready

    async def watch_ready(self) -> AsyncIterable[bool]:
        async for ready in self._subscribe("ready"):
            yield ready


class Configurable(Loadable[StateType], Generic[StateType], ABC):
    async def get_config(self) -> JSON:
        return {
            name: await parameter.get(self._state)
            for name, parameter in self._parameters_mapping.items()
        }

    async def set_config(self, config: JSON) -> JSON:
        if set(config.keys()) != set(self._parameters_mapping.keys()):
            raise INVALID_CONFIG_ERROR

        async with self._loading() as state:
            for name, value in config.items():
                try:
                    await self._parameters_mapping[name].set(state, value)
                except Exception as e:
                    raise INVALID_CONFIG_ERROR from e

        config = await self.get_config()
        await self._notify("config", config)
        return config

    async def watch_config(self) -> AsyncIterable[JSON]:
        async for config in self._subscribe("config"):
            yield config

    @property
    def config_schema(self) -> JSONSchema:
        return JSONSchema(
            {
                "title": "Face config schema",
                "type": "object",
                "properties": {
                    name: parameter.schema
                    for name, parameter in self._parameters_mapping.items()
                },
            }
        )

    @property
    def config_ui_schema(self) -> JSON:
        return {
            name: parameter.ui_schema
            for name, parameter in self._parameters_mapping.items()
        }

    @property
    def _parameters_mapping(self) -> Dict[str, Parameter]:
        return {parameter.name: parameter for parameter in self._parameters}

    @property
    @abstractmethod
    def _parameters(self) -> Iterable[Parameter]:
        pass
