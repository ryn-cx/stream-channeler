# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.ParamountPlus.update import UpdateMixin


# TODO: Validate
class ParamountPlusBase(UpdateMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Paramount+"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (
            "Paramount Plus",
            "Paramount+",
            "Paramount+ Amazon Channel",
            "Paramount Plus Essential",
            "Paramount Plus Premium",
        )

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.paramountplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "paramountplus.com"
