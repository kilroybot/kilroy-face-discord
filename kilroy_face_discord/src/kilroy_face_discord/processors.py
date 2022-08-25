import json
from abc import ABC, abstractmethod
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any, Dict, Optional
from uuid import UUID

from hikari import Bytes, Message, TextableChannel
from kilroy_face_server_py_sdk import (
    Categorizable,
    ImageData,
    ImageOnlyPost,
    ImageWithOptionalTextPost,
    JSONSchema,
    TextAndImagePost,
    TextData,
    TextOnlyPost,
    TextOrImagePost,
    TextWithOptionalImagePost,
    classproperty,
    normalize,
)


async def send_message(channel: TextableChannel, *args, **kwargs) -> UUID:
    message = await channel.send(*args, **kwargs)
    return UUID(int=message.id)


async def get_text_data(message: Message) -> Optional[TextData]:
    if message.content is None:
        return None
    return TextData(content=message.content)


async def get_image_data(message: Message) -> Optional[ImageData]:
    if not message.attachments:
        return None
    attachment = message.attachments[0]
    image_bytes = await attachment.read()
    encoded_image_bytes = urlsafe_b64encode(image_bytes).decode("ascii")
    return ImageData(raw=encoded_image_bytes, filename=attachment.filename)


def image_to_bytes(image: ImageData) -> Bytes:
    return Bytes(
        urlsafe_b64decode(image.raw.encode("ascii")),
        image.filename,
    )


class Processor(Categorizable, ABC):
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Processor"))

    @abstractmethod
    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        pass

    @abstractmethod
    async def convert(self, message: Message) -> Dict[str, Any]:
        pass

    @classproperty
    @abstractmethod
    def post_schema(cls) -> JSONSchema:
        pass


# Text only


class TextOnlyProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextOnlyPost.schema())

    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        post = TextOnlyPost.parse_obj(post)
        return await send_message(channel, post.text.content)

    async def convert(self, message: Message) -> Dict[str, Any]:
        text = await get_text_data(message)
        post = TextOnlyPost(text=text)
        return json.loads(post.json())


# Image only


class ImageOnlyProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**ImageOnlyPost.schema())

    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        post = ImageOnlyPost.parse_obj(post)
        image = image_to_bytes(post.image)
        return await send_message(channel, image)

    async def convert(self, message: Message) -> Dict[str, Any]:
        image = await get_image_data(message)
        post = ImageOnlyPost(image=image)
        return json.loads(post.json())


# Text and image


class TextAndImageProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextAndImagePost.schema())

    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        post = TextAndImagePost.parse_obj(post)
        image = image_to_bytes(post.image)
        return await send_message(channel, post.text.content, attachment=image)

    async def convert(self, message: Message) -> Dict[str, Any]:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = TextAndImagePost(text=text, image=image)
        return json.loads(post.json())


# Text or image


class TextOrImageProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextOrImagePost.schema())

    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        post = TextOrImagePost.parse_obj(post)
        kwargs = {}
        if post.text is not None:
            kwargs["content"] = post.text.content
        if post.image is not None:
            kwargs["attachment"] = image_to_bytes(post.image)
        return await send_message(channel, **kwargs)

    async def convert(self, message: Message) -> Dict[str, Any]:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = TextOrImagePost(text=text, image=image)
        return json.loads(post.json())


# Text with optional image


class TextWithOptionalImageProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextWithOptionalImagePost.schema())

    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        post = TextWithOptionalImagePost.parse_obj(post)
        kwargs = {}
        if post.image is not None:
            kwargs["attachment"] = image_to_bytes(post.image)
        return await send_message(channel, post.text.content, **kwargs)

    async def convert(self, message: Message) -> Dict[str, Any]:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = TextWithOptionalImagePost(text=text, image=image)
        return json.loads(post.json())


# Image with optional text


class ImageWithOptionalTextProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**ImageWithOptionalTextPost.schema())

    async def post(
        self, channel: TextableChannel, post: Dict[str, Any]
    ) -> UUID:
        post = ImageWithOptionalTextPost.parse_obj(post)
        kwargs = {}
        if post.image is not None:
            kwargs["attachment"] = image_to_bytes(post.image)
        return await send_message(channel, post.text.content, **kwargs)

    async def convert(self, message: Message) -> Dict[str, Any]:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = ImageWithOptionalTextPost(text=text, image=image)
        return json.loads(post.json())
