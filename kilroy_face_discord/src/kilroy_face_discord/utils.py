from abc import ABC
from copy import deepcopy
from typing import Any, Dict, Optional, TypeVar

D = TypeVar("D", bound="Deepcopyable")


class Deepcopyable(ABC):
    async def __adeepcopy__(
        self: D, memo: Optional[Dict[int, Any]] = None
    ) -> D:
        memo = memo if memo is not None else {}
        new = self.__class__.__new__(self.__class__)
        memo[id(self)] = new
        await self.__adeepcopy_to__(new, memo)
        return new

    async def __adeepcopy_to__(self: D, new: D, memo: Dict[int, Any]) -> None:
        for name in self.__dict__:
            setattr(new, name, await self.__deepcopy_attribute__(name, memo))

    async def __deepcopy_attribute__(
        self, name: str, memo: Dict[int, Any]
    ) -> Any:
        return deepcopy(getattr(self, name), memo)
