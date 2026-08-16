# TODO: Validate
"""The files Prime Video is read out of.

Prime Video's own web app asks for its pages as JSON, so every page is read the
way the site reads it rather than out of the HTML it renders. Deforestation is
what asks for them and what turns them into models.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from typing import Any, override

import httpx
from deforestation import USER_AGENT, Deforestation
from deforestation.constants import MARKETPLACES
from deforestation.detail.models import (
    AtfItem,
    DetailItem,
    DetailModel,
    EpisodePage,
    HeaderDetailItem,
    State,
    State1,
    Subscription,
)
from deforestation.detail.models import Payload1 as ExpandingCardPayload
from deforestation.detail.models import Payload2 as CardOptionPayload
from deforestation.detail_widgets.models import DetailWidgetsModel
from deforestation.detail_widgets.models import Episode as WidgetEpisode
from deforestation.exceptions import TitleNotFoundError
from deforestation.search.models import Entity, SearchModel
from pydantic import BaseModel
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, PartialGAPIJSON
from plugins.utils.get_around_client import get_around_client

# Where a share link is written, which is its own domain rather than a path on
# Prime Video's.
_SHARE_LINK_URL = "https://watch.amazon.com/detail"

# How long the redirect a share link answers with is waited for.
_REDIRECT_TIMEOUT_SECONDS = 30

# Which of a title's images stands for it, most wanted first.
_IMAGE_PREFERENCE = ("covershot", "packshot", "titleshot", "heroshot")

MOVIE_ENTITY_TYPE = "Movie"
"""What Prime Video calls a title that is a film rather than a series."""

# Prime itself is offered through the same payload as a channel, but a title
# included with Prime belongs to Prime Video rather than to a separate source.
_PRIME_BENEFIT_ID = "Prime"

# What a channel's own name is written after in the label it is offered under.
_CHANNEL_LABEL_PREFIXES = (
    "Watch with ",
    "Start your free trial to ",
    "Subscribe to ",
)

# What splits the two lines of an offer's label.
_LABEL_LINE_BREAK = "{lineBreak}"

# What a search lays its matches out as, which is what tells them apart from the
# rows of titles like them that it suggests alongside.
_GRID_CONTAINER_TYPE = "Grid"


# TODO: Validate
@cache
def deforestation() -> Deforestation:
    """Returns a cached Deforestation client.

    Read out of Prime Video's own marketplace rather than out of Amazon's,
    because a title is named by an id of one of two kinds and only this one
    answers for both: Amazon's own marketplace answers a link written with the
    id Prime Video writes by pointing at the id it uses itself instead.
    """
    return Deforestation(
        get_around_client=get_around_client(),
        host=MARKETPLACES["ROW"],
    )


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
@dataclass
class AmazonSearchResult:
    """One title a search matched."""

    key: str
    title: str
    entity_type: str
    year: int | None
    image_url: str | None


# TODO: Validate
def _pick_image(images: BaseModel) -> str | None:
    for name in _IMAGE_PREFERENCE:
        if url := getattr(images, name, None):
            return str(url)
    return None


# TODO: Validate
def _compact_key_from_link(link: str) -> str:
    """Return the id a link to a title carries, which is how its URL names it."""
    return link.split("?", 1)[0].rsplit("/", 1)[-1]


# TODO: Validate
def _channel_name(label: str) -> str:
    name = label.split(_LABEL_LINE_BREAK, 1)[0].strip()
    for prefix in _CHANNEL_LABEL_PREFIXES:
        name = name.removeprefix(prefix)
    if not name:
        msg = f"No channel name in {label!r}"
        raise ValueError(msg)
    return name


# TODO: Validate
def _episode_from_detail(item: DetailItem, compact_key: str) -> AmazonEpisode:
    """Return an episode read off the page of the season it belongs to."""
    return AmazonEpisode(
        key=item.title_id,
        compact_key=compact_key,
        title=item.title,
        episode_number=item.episode_number,
        synopsis=item.synopsis,
        duration=item.duration,
        release_date=item.release_date,
        image_url=_pick_image(item.images),
    )


# TODO: Validate
def _episode_from_widget(episode: WidgetEpisode) -> AmazonEpisode:
    """Return an episode read off a page of the season's episode list."""
    detail = episode.detail
    return AmazonEpisode(
        key=episode.title_id,
        compact_key=episode.self.compact_gti,
        title=detail.title,
        episode_number=detail.episode_number,
        synopsis=detail.synopsis,
        duration=detail.duration,
        release_date=detail.release_date,
        image_url=_pick_image(detail.images),
    )


# TODO: Validate
def _search_result(entity: Entity) -> AmazonSearchResult:
    return AmazonSearchResult(
        key=_compact_key_from_link(entity.link.url),
        title=entity.title,
        entity_type=entity.entity_type,
        year=int(entity.release_year) if entity.release_year else None,
        image_url=entity.images.cover.url,
    )


# TODO: Validate
class ShareLinkRedirect(BaseFile[str]):
    """Where a share link points.

    Amazon writes a share link with an id of its own that none of Prime Video's
    pages are keyed by, and answers it by pointing at the page that is. What it
    pointed at is stored so the id can be read off it, and so that reading it
    again is not another round trip.
    """

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, share_key: str) -> None:
        """Initialize the file."""
        self.share_key = share_key
        self.unique_identifier = share_key
        super().__init__(session, plugin)

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".txt"

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.share_key):
            # Asked for directly rather than through Deforestation, because that
            # one fetches a page and hands back what it settled on, and what is
            # wanted here is the address it was pointed at.
            #
            # Amazon decides where to point by what it is told is asking: a
            # request naming no browser is sent to the page advertising its app
            # rather than to the title, and that address carries no id.
            response = httpx.get(
                _SHARE_LINK_URL,
                params={"gti": self.share_key},
                headers={"User-Agent": USER_AGENT},
                follow_redirects=False,
                timeout=_REDIRECT_TIMEOUT_SECONDS,
            )
            self.write(response.headers.get("location"))

    # TODO: Validate
    def location(self) -> str | None:
        """Return the address the share link pointed at."""
        return self.database_record.content


# TODO: Validate
class Detail(GAPIJSON[DetailModel]):
    """A title's own page.

    A series has no page of its own on Prime Video: every page is one season of
    it, and each of them lists every season there is.
    """

    API_ENDPOINT = deforestation().detail

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, title_key: str) -> None:
        """Initialize the file."""
        self.title_key = title_key
        self.session = session
        self.plugin = plugin
        super().__init__(session, plugin, title_key)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        # Occurs when a user puts in an invalid URL.
        return isinstance(error, TitleNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid title {self.title_key}"

    # TODO: Validate
    @override
    def _download(self) -> None:
        super()._download()

        # The episode list is only ever read alongside the page it belongs to, so
        # the pages of it come down with the page rather than being asked for by
        # whatever reads the episodes.
        for page in self.episode_pages():
            page.download_if_outdated()

    # TODO: Validate
    @override
    def is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        if super().is_outdated(minimum_timestamp):
            return True
        # A missing page of the episode list makes this page outdated too, since
        # that is the only thing that downloads one.
        return any(page.is_outdated() for page in self.episode_pages())

    # TODO: Validate
    def _atf_state(self) -> State:
        return self.parsed().body.atf.state

    # TODO: Validate
    def _btf_state(self) -> State1:
        return self.parsed().body.btf.state

    # TODO: Validate
    def page_key(self) -> str:
        """Return the id of the title the page settled on.

        The id a URL carries is not always the id of the title it opens, since a
        title can be reached by any of the ids of the copies Amazon sells of it.
        """
        return self._atf_state().page_title_id

    # TODO: Validate
    def compact_key(self) -> str:
        """Return the id of this title that a link to it is written with."""
        page_key = self.page_key()
        for item in self._atf_state().self:
            if item.title_id == page_key:
                return item.compact_gti
        msg = f"No id for {page_key} on its own page"
        raise ValueError(msg)

    # TODO: Validate
    def _header(self) -> HeaderDetailItem:
        page_key = self.page_key()
        for item in self._atf_state().detail.header_detail:
            if item.title_id == page_key:
                return item
        msg = f"No details for {page_key} on its own page"
        raise ValueError(msg)

    # TODO: Validate
    def entity_type(self) -> str:
        """Return whether the title is a film or part of a series."""
        return self._header().entity_type

    # TODO: Validate
    def title(self) -> str:
        """Return the name of the title itself, season and all."""
        return self._header().title

    # TODO: Validate
    def series_title(self) -> str:
        """Return the name of the series, for a page that is a season of one."""
        header = self._header()
        return header.parent_title or header.title

    # TODO: Validate
    def synopsis(self) -> str | None:
        """Return what the title is about."""
        return self._header().synopsis

    # TODO: Validate
    def image_url(self) -> str | None:
        """Return the image the title is pictured by."""
        return _pick_image(self._header().images)

    # TODO: Validate
    def release_date(self) -> str | None:
        """Return the day the title came out, as Prime Video writes it."""
        return self._header().release_date

    # TODO: Validate
    def release_year(self) -> int | None:
        """Return the year the title came out."""
        return self._header().release_year

    # TODO: Validate
    def season_number(self) -> int | None:
        """Return which season of its series the page is."""
        return self._header().season_number

    # TODO: Validate
    def duration(self) -> int | None:
        """Return how long the title runs for, in seconds."""
        return self._header().duration

    # TODO: Validate
    def genres(self) -> list[str]:
        """Return the genres the title is filed under."""
        return [genre.text for genre in self._header().genres]

    # TODO: Validate
    def seasons(self) -> list[AmazonSeason]:
        """Return every season of the series this page is a season of."""
        seasons = self._atf_state().seasons
        # A title that is a season of nothing carries no seasons at all, which
        # is written as an empty object rather than as an empty list.
        if not isinstance(seasons, list):
            return []
        page_key = self.page_key()
        return [
            AmazonSeason(
                # Keyed by the id its own page is addressed by rather than by
                # the id the listing names it with, so that a season is the same
                # season whichever way in it was found.
                key=_compact_key_from_link(entry.season_link),
                name=entry.display_name,
                season_number=entry.sequence_number,
            )
            for season in seasons
            if season.title_id == page_key
            for entry in season.value
        ]

    # TODO: Validate
    def _episode_page_entries(self) -> list[EpisodePage]:
        """Return every page the season's episode list is split over."""
        actions = self._btf_state().episode_list.actions
        return list(actions.episode_pages) if actions else []

    # TODO: Validate
    def episode_page_token(self, page_index: int) -> str:
        """Return the token the page of the episode list at `page_index` is asked for by."""
        return self._episode_page_entries()[page_index].token

    # TODO: Validate
    def episode_pages(self) -> list[EpisodeList]:
        """Return every page of the episode list that is not on this page already.

        A season's page carries the page of its episode list that it opens on,
        so that one is read out of the page rather than asked for again.
        """
        if not self.database_record.content:
            return []
        return [
            EpisodeList(self.session, self.plugin, self.title_key, index)
            for index, page in enumerate(self._episode_page_entries())
            if not page.is_selected
        ]

    # TODO: Validate
    def _page_episodes(self) -> list[AmazonEpisode]:
        """Return the episodes the season's own page carries."""
        state = self._btf_state()
        details = {item.title_id: item for item in state.detail.detail}
        compact_keys = {
            item.title_id: item.compact_gti
            for item in self.raise_if_not_is_instance(state.self, list)
        }
        return [
            _episode_from_detail(details[title_id], compact_keys[title_id])
            for title_id in state.episode_list.card_title_ids or []
        ]

    # TODO: Validate
    def episodes(self) -> list[AmazonEpisode]:
        """Return every episode of the season, across all of its pages."""
        entries = self._episode_page_entries()
        if not entries:
            return self._page_episodes()

        episodes: list[AmazonEpisode] = []
        for index, entry in enumerate(entries):
            if entry.is_selected:
                episodes += self._page_episodes()
            else:
                page = EpisodeList(self.session, self.plugin, self.title_key, index)
                episodes += page.episodes()
        return episodes

    # TODO: Validate
    def _offer_payloads(self) -> list[ExpandingCardPayload | CardOptionPayload]:
        """Return everything the page says about how the title can be watched.

        Every way to watch is an action on a card, and a card is laid out either
        as the one offer the page leads with or as one of a set to pick from.
        """
        payloads: list[ExpandingCardPayload | CardOptionPayload] = []
        for action in self._offer_actions():
            for primary_action in action.primary_actions:
                payload = primary_action.payload
                if card := payload.expanding_card:
                    payloads += [option.payload for option in card.actions]
                for card_option in payload.card_options or []:
                    payloads += [option.payload for option in card_option.actions]
        return payloads

    # TODO: Validate
    def _offer_actions(self) -> list[AtfItem]:
        page_key = self.page_key()
        return [
            item for item in self._atf_state().action.atf if item.title_id == page_key
        ]

    # TODO: Validate
    def _subscriptions(self) -> list[Subscription]:
        return [
            payload.subscription
            for payload in self._offer_payloads()
            if payload.subscription
        ]

    # TODO: Validate
    def channels(self) -> list[AmazonChannel]:
        """Return every Amazon Channel this title can be watched with.

        A channel is offered more than once when it offers the title in more than
        one way, and the offer the page leads with is the one that names it.
        """
        channels: list[AmazonChannel] = []
        seen: set[str] = set()
        for subscription in self._subscriptions():
            benefit_id = subscription.benefit_id
            if benefit_id == _PRIME_BENEFIT_ID or benefit_id in seen:
                continue
            seen.add(benefit_id)
            channels.append(
                AmazonChannel(benefit_id, _channel_name(subscription.label)),
            )
        return channels

    # TODO: Validate
    def included_with_prime(self) -> bool:
        """Report whether a Prime subscription is enough to watch this title."""
        return any(
            subscription.benefit_id == _PRIME_BENEFIT_ID
            for subscription in self._subscriptions()
        )

    # TODO: Validate
    def purchasable(self) -> bool:
        """Report whether this title can be bought or rented.

        A title can be offered both ways, such as with a channel subscription and
        as a purchase, so this is asked on top of the other ways to watch it.
        """
        return any(payload.transaction for payload in self._offer_payloads())


# TODO: Validate
class EpisodeList(PartialGAPIJSON[DetailWidgetsModel]):
    """One page of a season's episode list.

    The page a season opens on only carries the episodes it shows, so every page
    of them is asked for by the token the season's page carries for it.
    """

    API_ENDPOINT = deforestation().detail_widgets

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        season_key: str,
        page_index: int,
    ) -> None:
        """Initialize the file."""
        self.season_key = season_key
        self.page_index = page_index
        self.session = session
        self.plugin = plugin
        super().__init__(session, plugin, f"{season_key}/{page_index}")

    # TODO: Validate
    @override
    def _get(self) -> DetailWidgetsModel:
        detail = Detail(self.session, self.plugin, self.season_key)
        token = detail.episode_page_token(self.page_index)
        return self.API_ENDPOINT.download_and_parse(self.season_key, token)

    # TODO: Validate
    def episodes(self) -> list[AmazonEpisode]:
        """Return the episodes this page holds."""
        episode_list = self.parsed().widgets.episode_list
        return [_episode_from_widget(episode) for episode in episode_list.episodes]


# TODO: Validate
class Search(GAPIJSON[SearchModel]):
    """Everything one search query matched.

    Prime Video answers a search with every match at once, so there is a single
    file for a query rather than one for each page of it.
    """

    API_ENDPOINT = deforestation().search

    # TODO: Validate
    def results(self) -> list[AmazonSearchResult]:
        """Return the titles the query matched, best match first.

        Prime Video answers a search with the titles it matched and with rows of
        titles like them, and only the matches are results of the search. The
        matches are the ones it lays out as a grid; the rows it suggests are
        carousels.
        """
        results: list[AmazonSearchResult] = []
        seen: set[str] = set()
        for container in self.parsed().body.containers:
            if container.container_type != _GRID_CONTAINER_TYPE:
                continue
            for entity in container.entities:
                result = _search_result(entity)
                if result.key in seen:
                    continue
                seen.add(result.key)
                results.append(result)
        return results


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def detail_file(self, title_key: str) -> Detail:
        """Returns data for a title."""
        return self._file(Detail, title_key)

    # TODO: Validate
    def share_link_file(self, share_key: str) -> ShareLinkRedirect:
        """Returns where the share link written with `share_key` points."""
        return self._file(ShareLinkRedirect, share_key)

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        """Returns data for search results."""
        return self._file(Search, query)

    # TODO: Validate
    def _is_movie(self, title_key: str) -> bool:
        return self.detail_file(title_key).entity_type() == MOVIE_ENTITY_TYPE

    # TODO: Validate
    def _season_entries(self, show_key: str) -> list[AmazonSeason]:
        """Return every season of a title, which a film is one of itself."""
        page = self.detail_file(show_key)
        if seasons := page.seasons():
            return seasons
        return [
            AmazonSeason(
                key=page.compact_key(),
                name=page.title(),
                season_number=page.season_number() or 1,
            ),
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.detail_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the season and new episodes of it.
            self.detail_file(season_key),
            # Required to detect a season being taken off the show.
            self.detail_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return [self.detail_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return [season.key for season in self._season_entries(show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            if self._is_movie(season_key):
                # A film is the only episode of the only season of itself.
                episode_keys.append(season_key)
            else:
                episode_keys += [
                    episode.key for episode in self.detail_file(season_key).episodes()
                ]
        return episode_keys
