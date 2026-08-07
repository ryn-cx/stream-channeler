# TODO: Validate
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, cast, override

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import BaseFile, HTMLFile, JSONFile
from plugins.utils.get_around_client import get_around_client

_HYDRATION_SCRIPT_ID = "dv-web-page-hydration-data"
_HYDRATION_STRAINER = SoupStrainer("script", attrs={"id": _HYDRATION_SCRIPT_ID})
_IMAGE_PREFERENCE = ("covershot", "packshot", "titleshot", "heroshot")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_PAGE_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def _pick_image(images: dict[str, Any]) -> str | None:
    for key in _IMAGE_PREFERENCE:
        if url := images.get(key):
            return url
    return None


# Prime itself is offered through the same subscription payload as a channel, but a
# title included with Prime belongs to Prime Video rather than a separate source.
_PRIME_BENEFIT_IDS = frozenset({"Prime"})

# The payload a title carries when it is offered for sale or for rent.
_PURCHASE_DATA_KEY = "purchaseData"


def _episode_from_detail(asin: str, detail: dict[str, Any]) -> AmazonEpisode:
    return AmazonEpisode(
        asin=asin,
        title=detail["title"],
        episode_number=detail["episodeNumber"],
        synopsis=detail.get("synopsis"),
        duration=detail.get("duration"),
        release_date=detail.get("releaseDate"),
        image_url=_pick_image(detail.get("images", {})),
    )


def _channel_name(label: str) -> str:
    name = label.split("{lineBreak}", 1)[0].removeprefix("Watch with ").strip()
    if not name:
        msg = f"No channel name in {label!r}"
        raise ValueError(msg)
    return name


@dataclass
class AmazonChannel:
    benefit_id: str
    name: str


@dataclass
class AmazonSeason:
    asin: str
    name: str
    season_number: int


@dataclass
class AmazonEpisode:
    asin: str
    title: str
    episode_number: int
    synopsis: str | None
    duration: int | None
    release_date: str | None
    image_url: str | None


class DetailPage(HTMLFile):
    """Detail page file."""

    def __init__(self, session: Session, plugin: Plugin, asin: str) -> None:
        self.asin = asin
        self.session = session
        self.plugin = plugin
        self._hydration_cache: dict[str, Any] | None = None
        super().__init__(session, plugin, asin)

    @override
    def write(self, content: str | None, extra: str | None = None) -> None:
        self._hydration_cache = None
        super().write(content, extra)

    @override
    def _download(self) -> None:
        with self._log_download(self.asin):
            url = f"https://www.amazon.com/gp/video/detail/{self.asin}"
            response = get_around_client().get(
                url,
                headers=_PAGE_HEADERS,
                follow_redirects=True,
            )
            if response.status_code == HTTPStatus.NOT_FOUND:
                self.write(None, f"Invalid title {self.asin}")
                return
            response.raise_for_status()
            self.write(response.text)

        for page in self._episode_pages():
            page.download_if_outdated()

    def _episode_pages(self) -> list[EpisodeListPage]:
        if not self.database_record.content:
            return []
        return [
            EpisodeListPage(self.session, self.plugin, self.asin, index)
            for index in range(len(self.episode_page_tokens()))
        ]

    @override
    def is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        if super().is_outdated(minimum_timestamp):
            return True
        # The episode list is only ever downloaded alongside this page, so a
        # missing page of it makes this page outdated as well.
        return any(page.is_outdated() for page in self._episode_pages())

    @override
    def parsed(self) -> BeautifulSoup:
        """Return only the page's hydration-data script element."""
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)
            self._cached_parsed = BeautifulSoup(
                content,
                "lxml",
                parse_only=_HYDRATION_STRAINER,
            )
        return self._cached_parsed

    def _hydration(self) -> dict[str, Any]:
        if self._hydration_cache is None:
            script = self.parsed().find("script", id=_HYDRATION_SCRIPT_ID)
            if not isinstance(script, Tag) or script.string is None:
                msg = f"No hydration data found for {self.asin}"
                raise ValueError(msg)
            self._hydration_cache = json.loads(script.string)
        return self._hydration_cache

    def _body(self) -> dict[str, Any]:
        return self._hydration()["init"]["preparations"]["body"]

    def _page_id(self) -> str:
        # The URL ASIN can differ from the page Amazon resolves to (redirects),
        # so the hydration data is keyed by the page's own title id.
        header_detail = self._body()["atf"]["state"]["detail"]["headerDetail"]
        page_id = self._body()["atf"]["state"].get("pageTitleId")
        if page_id in header_detail:
            return page_id
        return next(iter(header_detail))

    def _header(self) -> dict[str, Any]:
        return self._body()["atf"]["state"]["detail"]["headerDetail"][self._page_id()]

    def entity_type(self) -> str:
        return self._header()["entityType"]

    def title(self) -> str:
        return self._header()["title"]

    def series_title(self) -> str:
        header = self._header()
        return header.get("parentTitle") or header["title"]

    def synopsis(self) -> str | None:
        return self._header().get("synopsis")

    def image_url(self) -> str | None:
        return _pick_image(self._header().get("images", {}))

    def release_date(self) -> str | None:
        return self._header().get("releaseDate")

    def season_number(self) -> int | None:
        return self._header().get("seasonNumber")

    def _subscriptions(self) -> list[dict[str, Any]]:
        actions = self._body()["atf"]["state"]["action"]["atf"].get(self._page_id(), {})
        found: list[dict[str, Any]] = []

        def collect(node: object) -> None:
            if isinstance(node, dict):
                mapping = cast("dict[str, Any]", node)
                if isinstance(subscription := mapping.get("subscription"), dict):
                    found.append(cast("dict[str, Any]", subscription))
                for value in mapping.values():
                    collect(value)
            elif isinstance(node, list):
                for value in cast("list[Any]", node):
                    collect(value)

        collect(actions)
        return found

    def channels(self) -> list[AmazonChannel]:
        """Return every Amazon Channel this title can be watched with.

        A channel is listed more than once when it offers the title in more than
        one way, and only the first listing names the channel.
        """
        channels: list[AmazonChannel] = []
        seen: set[str] = set()
        for subscription in self._subscriptions():
            benefit_id = subscription.get("benefitId")
            label = subscription.get("label")
            if not benefit_id or not label:
                continue
            if benefit_id in _PRIME_BENEFIT_IDS or benefit_id in seen:
                continue
            seen.add(benefit_id)
            channels.append(AmazonChannel(benefit_id, _channel_name(label)))
        return channels

    def included_with_prime(self) -> bool:
        """Report whether a Prime subscription is enough to watch this title."""
        return any(
            subscription.get("benefitId") in _PRIME_BENEFIT_IDS
            for subscription in self._subscriptions()
        )

    def purchasable(self) -> bool:
        """Report whether this title can be bought or rented.

        A title can be offered both ways, such as with a channel subscription and
        as a purchase, so this is asked on top of the other ways to watch it.
        """
        actions = self._body()["atf"]["state"]["action"]["atf"].get(self._page_id(), {})

        def has_purchase_data(node: object) -> bool:
            if isinstance(node, dict):
                mapping = cast("dict[str, Any]", node)
                if isinstance(mapping.get(_PURCHASE_DATA_KEY), dict):
                    return True
                return any(has_purchase_data(value) for value in mapping.values())
            if isinstance(node, list):
                values: list[Any] = node
                return any(has_purchase_data(value) for value in values)
            return False

        return has_purchase_data(actions)

    def seasons(self) -> list[AmazonSeason]:
        seasons_by_id = self._body()["atf"]["state"].get("seasons", {})
        entries = seasons_by_id.get(self._page_id(), [])
        return [
            AmazonSeason(
                asin=entry["seasonId"],
                name=entry["displayName"],
                season_number=entry["sequenceNumber"],
            )
            for entry in entries
        ]

    def episode_page_tokens(self) -> list[str]:
        """Return the token of every page the episode list is split over.

        The page only carries the episodes of the page it opens on, so every page
        is read from the episode list endpoint rather than from the page itself.
        """
        actions = self._body()["btf"]["state"].get("episodeList", {}).get("actions", {})
        return [page["token"] for page in actions.get("episodePages", [])]

    def episodes(self) -> list[AmazonEpisode]:
        """Return every episode of the season, across all of its pages."""
        episodes: list[AmazonEpisode] = []
        seen: set[str] = set()
        for page in self._episode_pages():
            for episode in page.episodes():
                if episode.asin not in seen:
                    seen.add(episode.asin)
                    episodes.append(episode)
        return episodes


class EpisodeListPage(JSONFile[dict[str, Any]]):
    """One page of a season's episode list.

    Only the first page is part of the detail page, so the rest are asked for with
    the token the detail page carries for them.
    """

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        asin: str,
        page_index: int,
    ) -> None:
        self.asin = asin
        self.page_index = page_index
        self.session = session
        self.plugin = plugin
        self.unique_identifier = f"{asin}/{page_index}"
        super().__init__(session, plugin)

    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", raw)

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            detail_page = DetailPage(self.session, self.plugin, self.asin)
            token = detail_page.episode_page_tokens()[self.page_index]
            widgets = json.dumps(
                [{"widgetType": "EpisodeList", "widgetToken": token}],
            )
            response = get_around_client().get(
                "https://www.amazon.com/gp/video/api/getDetailWidgets",
                params={"titleID": self.asin, "isTvodOnRow": "", "widgets": widgets},
                headers={
                    **_PAGE_HEADERS,
                    "Accept": "*/*",
                    # The endpoint only answers requests the page itself would make.
                    "x-requested-with": "XMLHttpRequest",
                    "Referer": f"https://www.amazon.com/gp/video/detail/{self.asin}",
                },
                follow_redirects=True,
            )
            response.raise_for_status()
            self.write(response.text)

    def episodes(self) -> list[AmazonEpisode]:
        """Return the episodes this page holds."""
        episode_list = self.parsed().get("widgets", {}).get("episodeList", {})
        return [
            _episode_from_detail(entry["detail"]["catalogId"], entry["detail"])
            for entry in episode_list.get("episodes", [])
            if entry.get("detail")
        ]


class FileMixin(TMDBMixin, register=False):
    def detail_page(self, asin: str) -> DetailPage:
        """Returns DetailPage file."""
        return self._file(DetailPage, asin)

    def _is_movie(self, show_key: str) -> bool:
        return self.detail_page(show_key).entity_type() == "Movie"

    def _season_entries(self, show_key: str) -> list[AmazonSeason]:
        page = self.detail_page(show_key)
        if seasons := page.seasons():
            return seasons
        return [
            AmazonSeason(
                asin=show_key,
                name=page.title(),
                season_number=page.season_number() or 1,
            ),
        ]

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([self.detail_page(show_key)], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file(
            [self.detail_page(season_key)],
            season_key,
            show_key,
        )

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_episode_file(
            [self.detail_page(season_key)],
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [show_key]
        return [season.asin for season in self._season_entries(show_key)]

    @override
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            page = self.detail_page(season_key)
            if page.entity_type() == "Movie":
                episode_keys.append(season_key)
            else:
                episode_keys += [episode.asin for episode in page.episodes()]
        return episode_keys
