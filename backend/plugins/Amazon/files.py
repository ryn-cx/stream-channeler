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
from typing import Any, cast, override

import httpx
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.Amazon import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    BaseFile,
    EndpointJSON,
    JSONFile,
)

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

# What a card writes the name of what it offers as.
_HEADING_TEXT_TYPE = "HEADING"

# What a search lays its matches out as, which is what tells them apart from the
# rows of titles like them that it suggests alongside.
_GRID_CONTAINER_TYPE = "Grid"


# TODO: Validate
class AmazonJSON(EndpointJSON[dict[str, Any]]):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return self.raise_if_not_is_instance(raw, dict)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)


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
def _compact_key_from_link(link: str) -> str:
    """Return the id a link to a title carries, which is how its URL names it."""
    return link.split("?", 1)[0].rsplit("/", 1)[-1]


# TODO: Validate
def _card_texts(card: dict[str, Any]) -> list[dict[str, Any]]:
    texts: list[dict[str, Any]] = []
    for component in (card.get("components") or {}).values():
        payload = component["componentPayload"]
        if collection := payload.get("textComponentCollection"):
            texts += collection["textList"]
        if text := payload.get("textComponent"):
            texts.append(text)
    return texts


# TODO: Validate
def _card_channel_name(card: dict[str, Any]) -> str | None:
    """Return the channel's own name as the card it is offered on heads it.

    The button on the card is labelled with what pressing it does rather than
    with the channel, so more than one channel is offered under the same label.
    """
    for text in _card_texts(card):
        if text["textType"] == _HEADING_TEXT_TYPE:
            return text["text"].strip()
    return None


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
def _pick_raw_image(images: dict[str, Any]) -> str | None:
    for name in _IMAGE_PREFERENCE:
        if url := images.get(name):
            return str(url)
    return None


# TODO: Validate
def _episode_from_detail(
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
        image_url=_pick_raw_image(item["images"]),
    )


# TODO: Validate
def _episode_from_widget(episode: dict[str, Any]) -> AmazonEpisode:
    """Return an episode read off a page of the season's episode list."""
    detail = episode["detail"]
    return AmazonEpisode(
        key=episode["titleID"],
        compact_key=episode["self"]["compactGTI"],
        title=detail["title"],
        episode_number=detail["episodeNumber"],
        synopsis=detail["synopsis"],
        duration=detail["duration"],
        release_date=detail["releaseDate"],
        image_url=_pick_raw_image(detail["images"]),
    )


# TODO: Validate
def _search_result(entity: dict[str, Any]) -> AmazonSearchResult:
    release_year = entity.get("releaseYear")
    return AmazonSearchResult(
        key=_compact_key_from_link(entity["link"]["url"]),
        title=entity["title"],
        entity_type=entity["entityType"],
        year=int(release_year) if release_year else None,
        image_url=entity["images"]["cover"]["url"],
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
                headers={"User-Agent": api.USER_AGENT},
                follow_redirects=False,
                timeout=_REDIRECT_TIMEOUT_SECONDS,
            )
            self.write(response.headers.get("location"))

    # TODO: Validate
    def location(self) -> str | None:
        """Return the address the share link pointed at."""
        return self.database_record.content


# TODO: Validate
class Detail(JSONFile[dict[str, Any]]):
    """A title's own page.

    A series has no page of its own on Prime Video: every page is one season of
    it, and each of them lists every season there is.

    Read as the raw payload rather than through a Deforestation model, because
    Amazon keeps hanging fields the model has never seen off this page and a
    model built to forbid them fails the whole page over a field nothing here
    reads. What is read out of it is a handful of values, so they are picked out
    by name and the rest is left alone.

    That leaves the page as Amazon writes it, which is not the shape a model of
    it has: what a model turns into a list keyed by `titleId` is a map keyed by
    the title id here, and it is read by looking the id up rather than by
    searching a list for it.
    """

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, title_key: str) -> None:
        """Initialize the file."""
        self.title_key = title_key
        self.unique_identifier = title_key
        self.session = session
        self.plugin = plugin
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", raw)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.title_key):
            try:
                self.write(api.detail(self.title_key))
            except api.TitleNotFoundError:
                # Occurs when a user puts in an invalid URL.
                self.write(None, f"Invalid title {self.title_key}")

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
    def _atf_state(self) -> dict[str, Any]:
        state: dict[str, Any] = self.parsed()["body"]["atf"]["state"]
        return state

    # TODO: Validate
    def _btf_state(self) -> dict[str, Any]:
        state: dict[str, Any] = self.parsed()["body"]["btf"]["state"]
        return state

    # TODO: Validate
    def page_key(self) -> str:
        """Return the id of the title the page settled on.

        The id a URL carries is not always the id of the title it opens, since a title
        can be reached by any of the ids of the non-canonical rows Amazon sells of it.
        """
        return str(self._atf_state()["pageTitleId"])

    # TODO: Validate
    def compact_key(self) -> str:
        """Return the id of this title that a link to it is written with."""
        return str(self._atf_state()["self"][self.page_key()]["compactGTI"])

    # TODO: Validate
    def _header(self) -> dict[str, Any]:
        header: dict[str, Any] = self._atf_state()["detail"]["headerDetail"][
            self.page_key()
        ]
        return header

    # TODO: Validate
    def entity_type(self) -> str:
        """Return whether the title is a film or part of a series."""
        return str(self._header()["entityType"])

    # TODO: Validate
    def title(self) -> str:
        """Return the name of the title itself, season and all."""
        return str(self._header()["title"])

    # TODO: Validate
    def series_title(self) -> str:
        """Return the name of the series, for a page that is a season of one."""
        header = self._header()
        return str(header.get("parentTitle") or header["title"])

    # TODO: Validate
    def synopsis(self) -> str | None:
        """Return what the title is about."""
        synopsis: str | None = self._header()["synopsis"]
        return synopsis

    # TODO: Validate
    def image_url(self) -> str | None:
        """Return the image the title is pictured by."""
        return _pick_raw_image(self._header()["images"])

    # TODO: Validate
    def release_date(self) -> str | None:
        """Return the day the title came out, as Prime Video writes it."""
        release_date: str | None = self._header()["releaseDate"]
        return release_date

    # TODO: Validate
    def release_year(self) -> int | None:
        """Return the year the title came out."""
        release_year: int | None = self._header()["releaseYear"]
        return release_year

    # TODO: Validate
    def season_number(self) -> int | None:
        """Return which season of its series the page is."""
        return self._header().get("seasonNumber")

    # TODO: Validate
    def duration(self) -> int | None:
        """Return how long the title runs for, in seconds."""
        return self._header().get("duration")

    # TODO: Validate
    def genres(self) -> list[str]:
        """Return the genres the title is filed under."""
        return [genre["text"] for genre in self._header()["genres"]]

    # TODO: Validate
    def seasons(self) -> list[AmazonSeason]:
        """Return every season of the series this page is a season of."""
        return [
            AmazonSeason(
                # Keyed by the id its own page is addressed by rather than by
                # the id the listing names it with, so that a season is the same
                # season whichever way in it was found.
                key=_compact_key_from_link(entry["seasonLink"]),
                name=entry["displayName"],
                season_number=entry["sequenceNumber"],
            )
            for entry in self._atf_state()["seasons"].get(self.page_key(), [])
        ]

    # TODO: Validate
    def _episode_list(self) -> dict[str, Any]:
        """Return the episode list, which a title with no episodes has none of."""
        episode_list: dict[str, Any] = self._btf_state().get("episodeList") or {}
        return episode_list

    # TODO: Validate
    def _episode_page_entries(self) -> list[dict[str, Any]]:
        """Return every page the season's episode list is split over."""
        actions = self._episode_list().get("actions") or {}
        return list(actions.get("episodePages") or [])

    # TODO: Validate
    def episode_page_token(self, page_index: int) -> str:
        """Return the token the page of the episode list at `page_index` is asked for by."""
        return str(self._episode_page_entries()[page_index]["token"])

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
            if not page["isSelected"]
        ]

    # TODO: Validate
    def _page_episodes(self) -> list[AmazonEpisode]:
        """Return the episodes the season's own page carries."""
        card_title_ids = self._episode_list().get("cardTitleIds") or []
        if not card_title_ids:
            return []

        state = self._btf_state()
        details = state["detail"]["detail"]
        compact_keys = state["self"]
        return [
            _episode_from_detail(
                title_id,
                details[title_id],
                compact_keys[title_id]["compactGTI"],
            )
            for title_id in card_title_ids
        ]

    # TODO: Validate
    def episodes(self) -> list[AmazonEpisode]:
        """Return every episode of the season, across all of its pages."""
        entries = self._episode_page_entries()
        if not entries:
            return self._page_episodes()

        episodes: list[AmazonEpisode] = []
        for index, entry in enumerate(entries):
            if entry["isSelected"]:
                episodes += self._page_episodes()
            else:
                page = EpisodeList(self.session, self.plugin, self.title_key, index)
                episodes += page.episodes()
        return episodes

    # TODO: Validate
    def _offer_cards(self) -> list[dict[str, Any]]:
        """Return every card the page offers a way to watch the title on.

        A card is laid out either as the one offer the page leads with or as one
        of a set to pick from.
        """
        cards: list[dict[str, Any]] = []
        for action in self._offer_actions():
            for primary_action in action["primaryActions"]:
                payload = primary_action["payload"]
                if card := payload.get("expandingCard"):
                    cards.append(card)
                cards += payload.get("cardOptions") or []
        return cards

    # TODO: Validate
    def _offer_payloads(self) -> list[dict[str, Any]]:
        """Return everything the page says about how the title can be watched.

        Every way to watch is an action on a card, and a card is laid out either
        as the one offer the page leads with or as one of a set to pick from.
        """
        return [
            option["payload"]
            for card in self._offer_cards()
            for option in card["actions"]
        ]

    # TODO: Validate
    def _offer_actions(self) -> list[dict[str, Any]]:
        action = self._atf_state()["action"]["atf"].get(self.page_key())
        return [action] if action else []

    # TODO: Validate
    def _subscriptions(self) -> list[dict[str, Any]]:
        return [
            payload["subscription"]
            for payload in self._offer_payloads()
            if payload.get("subscription")
        ]

    # TODO: Validate
    def channels(self) -> list[AmazonChannel]:
        """Return every Amazon Channel this title can be watched with.

        A channel is offered more than once when it offers the title in more than
        one way, and the offer the page leads with is the one that names it.
        """
        channels: list[AmazonChannel] = []
        seen: set[str] = set()
        for card in self._offer_cards():
            for option in card["actions"]:
                subscription = option["payload"].get("subscription")
                if not subscription:
                    continue
                benefit_id = subscription["benefitId"]
                if benefit_id == _PRIME_BENEFIT_ID or benefit_id in seen:
                    continue
                seen.add(benefit_id)
                name = _card_channel_name(card) or _channel_name(subscription["label"])
                channels.append(AmazonChannel(benefit_id, name))
        return channels

    # TODO: Validate
    def included_with_prime(self) -> bool:
        """Report whether a Prime subscription is enough to watch this title."""
        return any(
            subscription["benefitId"] == _PRIME_BENEFIT_ID
            for subscription in self._subscriptions()
        )

    # TODO: Validate
    def purchasable(self) -> bool:
        """Report whether this title can be bought or rented.

        A title can be offered both ways, such as with a channel subscription and
        as a purchase, so this is asked on top of the other ways to watch it.
        """
        return any(payload.get("transaction") for payload in self._offer_payloads())


# TODO: Validate
class EpisodeList(AmazonJSON):
    """One page of a season's episode list.

    The page a season opens on only carries the episodes it shows, so every page
    of them is asked for by the token the season's page carries for it.
    """

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
    def _fetch(self) -> dict[str, Any]:
        detail = Detail(self.session, self.plugin, self.season_key)
        token = detail.episode_page_token(self.page_index)
        return api.detail_widgets(self.season_key, token)

    # TODO: Validate
    def episodes(self) -> list[AmazonEpisode]:
        """Return the episodes this page holds."""
        episode_list = self.parsed()["widgets"]["episodeList"]
        return [_episode_from_widget(episode) for episode in episode_list["episodes"]]


# TODO: Validate
class Search(AmazonJSON):
    """Everything one search query matched.

    Prime Video answers a search with every match at once, so there is a single
    file for a query rather than one for each page of it.
    """

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.search(self.unique_identifier)

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
        for container in self.parsed()["body"]["containers"]:
            if container["containerType"] != _GRID_CONTAINER_TYPE:
                continue
            for entity in container["entities"]:
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
        """Return data for a title."""
        return self._file(Detail, title_key)

    # TODO: Validate
    def share_link_file(self, share_key: str) -> ShareLinkRedirect:
        """Return where the share link written with `share_key` points."""
        return self._file(ShareLinkRedirect, share_key)

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        """Return data for search results."""
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
