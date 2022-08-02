import json
from abc import ABC, abstractmethod
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from typing import Generic, Iterable, Optional
from uuid import UUID

from hikari import Bytes, Message, TextableChannel
from kilroy_face_server_py_sdk import (
    BasePostModel,
    BaseState,
    Categorizable,
    ConfigurableWithLoadableState,
    ImageData,
    ImageOnlyPost,
    ImageWithOptionalTextPost,
    JSON,
    JSONSchema,
    Parameter,
    StateType,
    TextAndImagePost,
    TextData,
    TextOnlyPost,
    TextOrImagePost,
    TextWithOptionalImagePost,
)


def to_json(post: BasePostModel) -> JSON:
    return json.loads(post.json())


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


class Processor(
    ConfigurableWithLoadableState[StateType],
    Categorizable,
    Generic[StateType],
    ABC,
):
    @abstractmethod
    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        pass

    @abstractmethod
    async def convert(self, message: Message) -> JSON:
        pass

    @staticmethod
    @abstractmethod
    def post_schema() -> JSONSchema:
        pass


# Text only


@dataclass
class TextOnlyProcessorState(BaseState):
    pass


class TextOnlyProcessor(Processor[TextOnlyProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "text"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextOnlyPost.schema())

    async def _create_initial_state(self) -> TextOnlyProcessorState:
        return TextOnlyProcessorState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        post = TextOnlyPost.parse_obj(post)
        return await send_message(channel, post.text.content)

    async def convert(self, message: Message) -> JSON:
        text = await get_text_data(message)
        post = TextOnlyPost(text=text)
        return to_json(post)


# Image only


@dataclass
class ImageOnlyProcessorState(BaseState):
    pass


class ImageOnlyProcessor(Processor[ImageOnlyProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(ImageOnlyPost.schema())

    async def _create_initial_state(self) -> ImageOnlyProcessorState:
        return ImageOnlyProcessorState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        post = ImageOnlyPost.parse_obj(post)
        image = image_to_bytes(post.image)
        return await send_message(channel, image)

    async def convert(self, message: Message) -> JSON:
        image = await get_image_data(message)
        post = ImageOnlyPost(image=image)
        return to_json(post)


# Text and image


@dataclass
class TextAndImageProcessorState(BaseState):
    pass


class TextAndImageProcessor(Processor[TextAndImageProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "text-and-image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextAndImagePost.schema())

    async def _create_initial_state(self) -> TextAndImageProcessorState:
        return TextAndImageProcessorState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        post = TextAndImagePost.parse_obj(post)
        image = image_to_bytes(post.image)
        return await send_message(channel, post.text.content, attachment=image)

    async def convert(self, message: Message) -> JSON:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = TextAndImagePost(text=text, image=image)
        return to_json(post)


# Text or image


@dataclass
class TextOrImageProcessorState(BaseState):
    pass


class TextOrImageProcessor(Processor[TextOrImageProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "text-or-image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextOrImagePost.schema())

    async def _create_initial_state(self) -> TextOrImageProcessorState:
        return TextOrImageProcessorState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        post = TextOrImagePost.parse_obj(post)
        kwargs = {}
        if post.text is not None:
            kwargs["content"] = post.text.content
        if post.image is not None:
            kwargs["attachment"] = image_to_bytes(post.image)
        return await send_message(channel, **kwargs)

    async def convert(self, message: Message) -> JSON:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = TextOrImagePost(text=text, image=image)
        return to_json(post)


# Text with optional image


@dataclass
class TextWithOptionalImageProcessorState(BaseState):
    pass


class TextWithOptionalImageProcessor(
    Processor[TextWithOptionalImageProcessorState]
):
    @classmethod
    def category(cls) -> str:
        return "text-with-optional-image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextWithOptionalImagePost.schema())

    async def _create_initial_state(
        self,
    ) -> TextWithOptionalImageProcessorState:
        return TextWithOptionalImageProcessorState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        post = TextWithOptionalImagePost.parse_obj(post)
        kwargs = {}
        if post.image is not None:
            kwargs["attachment"] = image_to_bytes(post.image)
        return await send_message(channel, post.text.content, **kwargs)

    async def convert(self, message: Message) -> JSON:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = TextWithOptionalImagePost(text=text, image=image)
        return to_json(post)


# Image with optional text


@dataclass
class ImageWithOptionalTextProcessorState(BaseState):
    pass


class ImageWithOptionalTextImageProcessor(
    Processor[ImageWithOptionalTextProcessorState]
):
    @classmethod
    def category(cls) -> str:
        return "image-with-optional-text"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(ImageWithOptionalTextPost.schema())

    async def _create_initial_state(
        self,
    ) -> ImageWithOptionalTextProcessorState:
        return ImageWithOptionalTextProcessorState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []

    async def post(self, channel: TextableChannel, post: JSON) -> UUID:
        post = ImageWithOptionalTextPost.parse_obj(post)
        kwargs = {}
        if post.image is not None:
            kwargs["attachment"] = image_to_bytes(post.image)
        return await send_message(channel, post.text.content, **kwargs)

    async def convert(self, message: Message) -> JSON:
        text = await get_text_data(message)
        image = await get_image_data(message)
        post = ImageWithOptionalTextPost(text=text, image=image)
        return to_json(post)
