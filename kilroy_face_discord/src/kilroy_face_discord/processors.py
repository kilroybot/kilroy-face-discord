import json
from abc import ABC, abstractmethod
from typing import Any, Dict

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

from kilroy_face_discord.post import PostData, PostTextData, PostImageData


class Processor(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Processor"))

    @abstractmethod
    async def to_external(self, data: PostData) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        pass

    # noinspection PyMethodParameters
    @classproperty
    @abstractmethod
    def post_schema(cls) -> JSONSchema:
        pass


# Text only


class TextOnlyProcessor(Processor):
    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextOnlyPost.schema())

    async def to_external(self, data: PostData) -> Dict[str, Any]:
        if data.text is None:
            raise ValueError("Text data is required in this post type.")
        if data.image is not None:
            raise ValueError("Image data is not allowed in this post type.")
        post = TextOnlyPost(text=TextData(content=data.text.content))
        return json.loads(post.json())

    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        post = TextOnlyPost.parse_obj(data)
        return PostData(text=PostTextData(content=post.text.content))


# Image only


class ImageOnlyProcessor(Processor):
    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**ImageOnlyPost.schema())

    async def to_external(self, data: PostData) -> Dict[str, Any]:
        if data.text is not None:
            raise ValueError("Text data is not allowed in this post type.")
        if data.image is None:
            raise ValueError("Image data is required in this post type.")
        post = ImageOnlyPost(
            image=ImageData(raw=data.image.raw, filename=data.image.filename)
        )
        return json.loads(post.json())

    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        post = ImageOnlyPost.parse_obj(data)
        return PostData(
            image=PostImageData(
                raw=post.image.raw, filename=post.image.filename
            )
        )


# Text and image


class TextAndImageProcessor(Processor):
    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextAndImagePost.schema())

    async def to_external(self, data: PostData) -> Dict[str, Any]:
        if data.text is None or data.image is None:
            raise ValueError("Text and image data are required.")
        post = TextAndImagePost(
            text=TextData(content=data.text.content),
            image=ImageData(raw=data.image.raw, filename=data.image.filename),
        )
        return json.loads(post.json())

    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        post = TextAndImagePost.parse_obj(data)
        return PostData(
            text=PostTextData(content=post.text.content),
            image=PostImageData(
                raw=post.image.raw, filename=post.image.filename
            ),
        )


# Text or image


class TextOrImageProcessor(Processor):
    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextOrImagePost.schema())

    async def to_external(self, data: PostData) -> Dict[str, Any]:
        if data.text is None and data.image is None:
            raise ValueError("Either text or image data is required.")
        post = TextOrImagePost(
            text=TextData(content=data.text.content) if data.text else None,
            image=ImageData(raw=data.image.raw, filename=data.image.filename)
            if data.image
            else None,
        )
        return json.loads(post.json())

    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        post = TextOrImagePost.parse_obj(data)
        text = (
            PostTextData(content=post.text.content)
            if post.text is not None
            else None
        )
        image = (
            PostImageData(raw=post.image.raw, filename=post.image.filename)
            if post.image is not None
            else None
        )
        return PostData(text=text, image=image)


# Text with optional image


class TextWithOptionalImageProcessor(Processor):
    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextWithOptionalImagePost.schema())

    async def to_external(self, data: PostData) -> Dict[str, Any]:
        if data.text is None:
            raise ValueError("Text data is required.")
        post = TextWithOptionalImagePost(
            text=TextData(content=data.text.content),
            image=ImageData(raw=data.image.raw, filename=data.image.filename)
            if data.image
            else None,
        )
        return json.loads(post.json())

    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        post = TextWithOptionalImagePost.parse_obj(data)
        text = PostTextData(content=post.text.content)
        image = (
            PostImageData(raw=post.image.raw, filename=post.image.filename)
            if post.image is not None
            else None
        )
        return PostData(text=text, image=image)


# Image with optional text


class ImageWithOptionalTextProcessor(Processor):
    # noinspection PyMethodParameters
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**ImageWithOptionalTextPost.schema())

    async def to_external(self, data: PostData) -> Dict[str, Any]:
        if data.image is None:
            raise ValueError("Image data is required.")
        post = ImageWithOptionalTextPost(
            text=TextData(content=data.text.content) if data.text else None,
            image=ImageData(raw=data.image.raw, filename=data.image.filename),
        )
        return json.loads(post.json())

    async def to_internal(self, data: Dict[str, Any]) -> PostData:
        post = ImageWithOptionalTextPost.parse_obj(data)
        text = (
            PostTextData(content=post.text.content)
            if post.text is not None
            else None
        )
        image = PostImageData(raw=post.image.raw, filename=post.image.filename)
        return PostData(text=text, image=image)
