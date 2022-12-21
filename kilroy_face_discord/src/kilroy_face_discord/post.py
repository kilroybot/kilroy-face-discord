from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Optional
from uuid import UUID

from hikari import Message, Bytes
from kilroy_face_py_shared import SerializableModel


class PostTextData(SerializableModel):
    content: str


class PostImageData(SerializableModel):
    raw: str
    filename: Optional[str]

    def to_bytes(self) -> Bytes:
        return Bytes(
            urlsafe_b64decode(self.raw.encode("ascii")), self.filename
        )


class PostData(SerializableModel):
    text: Optional[PostTextData]
    image: Optional[PostImageData]


class Post(SerializableModel):
    data: PostData
    id: UUID
    url: str

    @classmethod
    async def from_message(cls, message: Message) -> "Post":
        text = None
        image = None
        if message.content is not None:
            text = PostTextData(content=message.content)
        if message.attachments:
            attachment = message.attachments[0]
            image_bytes = await attachment.read()
            image = PostImageData(
                raw=urlsafe_b64encode(image_bytes).decode("ascii"),
                filename=attachment.filename,
            )
        return cls(
            data=PostData(text=text, image=image),
            id=UUID(int=message.id),
            url=message.make_link(message.guild_id),
        )
