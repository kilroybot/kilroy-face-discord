from typing import Literal, TypeVar

StateType = TypeVar("StateType")
PostType = Literal["text", "image", "text+image"]
ScoringType = Literal["reactions"]
ScrapingType = Literal["basic"]
