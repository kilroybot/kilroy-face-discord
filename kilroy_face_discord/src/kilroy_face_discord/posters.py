from abc import ABC, abstractmethod
from uuid import UUID

from hikari import TextableGuildChannel
from kilroy_server_py_utils import Categorizable, classproperty, normalize

from kilroy_face_discord.post import PostData, Post


class Poster(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Poster"))

    @abstractmethod
    async def post(
        self, channel: TextableGuildChannel, data: PostData
    ) -> Post:
        pass


# Basic


class BasicPoster(Poster):
    async def post(
        self, channel: TextableGuildChannel, data: PostData
    ) -> Post:
        kwargs = {}
        if data.text is not None:
            kwargs["content"] = data.text.content
        if data.image is not None:
            kwargs["attachment"] = data.image.to_bytes()
        message = await channel.send(**kwargs)
        return Post(
            data=data,
            id=UUID(int=message.id),
            url=message.make_link(channel.guild_id),
        )
