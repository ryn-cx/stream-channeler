# TODO: Validate
"""What every other part of the plugin reads an NHK World title by."""

from __future__ import annotations

from typing import TYPE_CHECKING

MINIMUM_THUMBNAIL_WIDTH = 480

if TYPE_CHECKING:
    from collections.abc import Sequence

    from naphki.video_episodes.models import Image as EpisodeImage
    from naphki.video_program.models import LandscapeItem, PortraitItem


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://www3.nhk.or.jp/{path.lstrip('/')}"


# TODO: Validate
def image_url(images: Sequence[LandscapeItem | PortraitItem | EpisodeImage]) -> str:
    largest = max(images, key=lambda image: image.width)
    return build_url(largest.url)


# TODO: Validate
def thumbnail_url(images: Sequence[LandscapeItem | PortraitItem | EpisodeImage]) -> str:
    wide_enough = [image for image in images if image.width >= MINIMUM_THUMBNAIL_WIDTH]
    chosen = (
        min(wide_enough, key=lambda image: image.width)
        if wide_enough
        else max(images, key=lambda image: image.width)
    )
    return build_url(chosen.url)
