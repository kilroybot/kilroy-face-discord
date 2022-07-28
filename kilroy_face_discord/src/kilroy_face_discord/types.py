from typing import Literal, TypeVar

from kilroy_face_discord.utils import Deepcopyable

StateType = TypeVar("StateType", bound=Deepcopyable)
PostType = Literal["text", "image", "text+image"]
ScoringType = Literal["reactions"]
ScrapingType = Literal["basic"]
