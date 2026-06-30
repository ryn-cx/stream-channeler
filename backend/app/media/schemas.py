# TODO: Validate
from enum import StrEnum

from app.schemas import ReadOptions


class MediaOwner(StrEnum):
    official = "official"
    others = "others"


class MediaReadOptions(ReadOptions):
    owner: MediaOwner | None = None
