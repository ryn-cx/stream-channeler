# TODO: Validate
from enum import StrEnum

from app.schemas import ReadOptions


class MediaOwner(StrEnum):
    official = "official"
    others = "others"


class AdminReadOptions(ReadOptions):
    owner: MediaOwner


class MediaReadOptions(ReadOptions):
    owner: MediaOwner | None = None
