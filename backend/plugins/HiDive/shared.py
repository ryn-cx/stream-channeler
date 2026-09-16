# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol, override

from plugins.HiDive.base_files import HiDiveBaseFiles
from plugins.HiDive.constants import RELEASE_DATE_PREFIX

if TYPE_CHECKING:
    from diving_board.season import models as season_models
    from diving_board.vod import models as vod_models


# TODO: Validate
class HiDiveElement(Protocol):
    field_type: str


# TODO: Validate
class HiDiveShared(HiDiveBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HIDIVE"

    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://static.diceplatform.com/prod/original/dce.hidive/settings/"
            "HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356"
        )

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    # TODO: Validate
    @override
    def _next_source_update_at(self) -> datetime:
        return self._source_files_data_timestamp() + timedelta(days=1)

    # TODO: Validate
    @classmethod
    def build_url(cls, path: str) -> str:
        return f"https://hidive.com/{path.lstrip('/')}"

    # TODO: Validate
    @classmethod
    def episode_url(cls, episode_key: str | int) -> str:
        return cls.build_url(f"video/{episode_key}")

    # TODO: Validate
    @classmethod
    def single_element[ElementT: HiDiveElement](
        cls,
        elements: list[ElementT],
        field_type: str,
    ) -> ElementT:
        matches = [element for element in elements if element.field_type == field_type]
        if len(matches) != 1:
            msg = f"Expected one {field_type} element, found {len(matches)}"
            raise ValueError(msg)
        return matches[0]

    # TODO: Validate
    @classmethod
    def vod_hero(cls, vod_data: vod_models.VodModel) -> vod_models.Element:
        """Return the hero element of a parsed vod file."""
        return cls.single_element(vod_data.elements, "hero")

    # TODO: Validate
    @classmethod
    def hero_image_url(cls, hero: season_models.Element | vod_models.Element) -> str:
        """Return the image URL a hero is illustrated with."""
        if not hero.attributes.image:
            msg = "No image found in hero element."
            raise ValueError(msg)
        return hero.attributes.image.attributes.source

    # TODO: Validate
    @classmethod
    def tag_text(cls, tag: vod_models.Tag) -> str | None:
        text = tag.attributes.text
        if text is None or isinstance(text, str):
            return text
        return text.attributes.text

    # TODO: Validate
    @classmethod
    def release_date(cls, hero: vod_models.Element) -> datetime | None:
        """Return the day the title came out, as its hero's tags give it."""
        for content in hero.attributes.content or []:
            for tag in content.attributes.tags or []:
                text = cls.tag_text(tag)
                if text and text.startswith(RELEASE_DATE_PREFIX):
                    date_string = text.removeprefix(RELEASE_DATE_PREFIX)
                    return datetime.strptime(date_string, "%B %d, %Y").astimezone()
        return None
