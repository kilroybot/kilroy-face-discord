import json
from abc import ABC, abstractmethod
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Type

from hikari import Bytes, Message, TextableChannel
from kilroy_face_server_py_sdk import JSONSchema
from kilroy_ws_server_py_sdk import JSON

from kilroy_face_discord.posts import (
    ImageData,
    ImageOnlyPost,
    TextAndImagePost,
    TextData,
    TextOnlyPost,
)
from kilroy_face_discord.types import PostType


class Processor(ABC):
    @staticmethod
    @abstractmethod
    async def post(channel: TextableChannel, post: JSON) -> Message:
        pass

    @staticmethod
    @abstractmethod
    async def convert(message: Message) -> JSON:
        pass

    @staticmethod
    @abstractmethod
    def post_type() -> PostType:
        pass

    @staticmethod
    @abstractmethod
    def post_schema() -> JSONSchema:
        pass

    @classmethod
    def for_type(cls, post_type: PostType) -> Type["Processor"]:
        for processor in cls.__subclasses__():
            if processor.post_type() == post_type:
                return processor
        raise ValueError(f'Processor for type "{post_type}" not found.')


class TextOnlyProcessor(Processor):
    @staticmethod
    def post_type() -> PostType:
        return "text"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextOnlyPost.schema())

    @staticmethod
    async def post(channel: TextableChannel, post: JSON) -> Message:
        post = TextOnlyPost.parse_obj(post)
        return await channel.send(post.text.content)

    @staticmethod
    async def convert(message: Message) -> JSON:
        post = TextOnlyPost(text=TextData(content=message.content or ""))
        return json.loads(post.json())


class ImageOnlyProcessor(Processor):
    @staticmethod
    def post_type() -> PostType:
        return "image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(ImageOnlyPost.schema())

    @staticmethod
    async def post(channel: TextableChannel, post: JSON) -> Message:
        post = ImageOnlyPost.parse_obj(post)
        return await channel.send(
            Bytes(
                urlsafe_b64decode(post.image.raw.encode("ascii")),
                post.image.filename,
            )
        )

    @staticmethod
    async def convert(message: Message) -> JSON:
        attachment = message.attachments[0]
        image_bytes = await attachment.read()
        encoded_image_bytes = urlsafe_b64encode(image_bytes).decode("ascii")
        post = ImageOnlyPost(
            image=ImageData(
                raw=encoded_image_bytes, filename=attachment.filename
            )
        )
        return json.loads(post.json())


class TextAndImageProcessor(Processor):
    @staticmethod
    def post_type() -> PostType:
        return "text+image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextAndImagePost.schema())

    @staticmethod
    async def post(channel: TextableChannel, post: JSON) -> Message:
        post = TextAndImagePost.parse_obj(post)
        return await channel.send(
            post.text.content,
            attachment=Bytes(
                urlsafe_b64decode(post.image.raw.encode("ascii")),
                post.image.filename,
            ),
        )

    @staticmethod
    async def convert(message: Message) -> JSON:
        attachment = message.attachments[0]
        image_bytes = await attachment.read()
        encoded_image_bytes = urlsafe_b64encode(image_bytes).decode("ascii")
        post = TextAndImagePost(
            text=TextData(content=message.content or ""),
            image=ImageData(
                raw=encoded_image_bytes, filename=attachment.filename
            ),
        )
        return json.loads(post.json())
