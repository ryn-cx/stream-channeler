# TODO: Validate
"""What every other part of the plugin reads a Prime Video title by."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

from app.utils import tz_datetime
from plugins.Amazon.constants import IMAGE_PREFERENCE

if TYPE_CHECKING:
    from deforestation.detail_widgets.models import Episode as WidgetEpisode
    from pydantic import BaseModel


# TODO: Validate
@dataclass
class AmazonChannel:
    """A subscription other than Prime that a title can be watched with."""

    benefit_id: str
    name: str


# TODO: Validate
@dataclass
class AmazonSeason:
    """One season of a series, as its series' page lists it."""

    key: str
    name: str
    season_number: int


# TODO: Validate
@dataclass
class AmazonEpisode:
    """One episode of a season, as the season's episode list gives it."""

    key: str
    compact_key: str
    title: str
    episode_number: int | None
    synopsis: str | None
    duration: int | None
    release_date: str | None
    image_url: str | None


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://primevideo.com/{path.lstrip('/')}"


# TODO: Validate
def detail_url(compact_key: str) -> str:
    return build_url(f"detail/{compact_key}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"region/na/search?phrase={quote_plus(query)}")


# TODO: Validate
def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    # DTZ007 - Amazon release dates carry no timezone; localized below.
    parsed = datetime.strptime(value, "%b %d, %Y").date()  # noqa: DTZ007
    return tz_datetime.combine(parsed, datetime.min.time())


# TODO: Validate
def pick_image(images: BaseModel) -> str | None:
    for name in IMAGE_PREFERENCE:
        if url := getattr(images, name, None):
            return str(url)
    return None


# TODO: Validate
def pick_raw_image(images: dict[str, Any]) -> str | None:
    for name in IMAGE_PREFERENCE:
        if url := images.get(name):
            return str(url)
    return None


# TODO: Validate
def compact_key_from_link(link: str) -> str:
    """Return the id a link to a title carries, which is how its URL names it."""
    return link.split("?", 1)[0].rsplit("/", 1)[-1]


# TODO: Validate
def card_texts(card: dict[str, Any]) -> list[dict[str, Any]]:
    texts: list[dict[str, Any]] = []
    for component in (card.get("components") or {}).values():
        payload = component["componentPayload"]
        if collection := payload.get("textComponentCollection"):
            texts += collection["textList"]
        if text := payload.get("textComponent"):
            texts.append(text)
    return texts


# TODO: Validate
def card_channel_name(card: dict[str, Any]) -> str | None:
    """Return the channel's own name as the card it is offered on heads it.

    The button on the card is labelled with what pressing it does rather than
    with the channel, so more than one channel is offered under the same label.
    """
    for text in card_texts(card):
        # What a card writes the name of what it offers as.
        if text["textType"] == "HEADING":
            return text["text"].strip()
    return None


# TODO: Validate
def channel_name(label: str) -> str:
    # What splits the two lines of an offer's label.
    name = label.split("{lineBreak}", 1)[0].strip()
    # What a channel's own name is written after in the label it is offered
    # under.
    for prefix in ("Watch with ", "Start your free trial to ", "Subscribe to "):
        name = name.removeprefix(prefix)
    if not name:
        msg = f"No channel name in {label!r}"
        raise ValueError(msg)
    return name


# TODO: Validate
def episode_from_detail(
    title_id: str,
    item: dict[str, Any],
    compact_key: str,
) -> AmazonEpisode:
    """Return an episode read off the page of the season it belongs to."""
    return AmazonEpisode(
        key=title_id,
        compact_key=compact_key,
        title=item["title"],
        episode_number=item.get("episodeNumber"),
        synopsis=item["synopsis"],
        duration=item.get("duration"),
        release_date=item["releaseDate"],
        image_url=pick_raw_image(item["images"]),
    )


# TODO: Validate
def widget_episode_available(episode: WidgetEpisode) -> bool:
    return any(
        primary_action.payload.expanding_card or primary_action.payload.card_options
        for primary_action in episode.action.primary_actions
    )


# TODO: Validate
def episode_from_widget(episode: WidgetEpisode) -> AmazonEpisode:
    """Return an episode read off a page of the season's episode list."""
    detail = episode.detail
    return AmazonEpisode(
        key=episode.title_id,
        compact_key=episode.self.compact_gti,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        title=detail.title,
        episode_number=detail.episode_number,
        synopsis=detail.synopsis,
        duration=detail.duration,
        release_date=detail.release_date,
        image_url=pick_image(detail.images),
    )
