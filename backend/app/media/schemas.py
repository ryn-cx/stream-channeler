# TODO: Validate
from enum import StrEnum

from app.schemas import ReadOptions


# TODO: Validate
class MediaScope(StrEnum):
    """Which media a list endpoint returns.

    Mirrors `RecordScope`'s `owned`, `public` and `all` so the media tabs match the
    `Channel` and `ChannelOrder` ones, and keeps the admin-only `official`/`others`
    split of everyone else's media. Media has no `favorites`.
    """

    owned = "owned"
    public = "public"
    all = "all"
    official = "official"
    others = "others"


# TODO: Validate
class MediaReadOptions(ReadOptions):
    """Read options for the media lists.

    Defaults to `owned` so an unscoped read returns the `User`'s own media rather
    than demanding admin rights.
    """

    scope: MediaScope = MediaScope.owned
