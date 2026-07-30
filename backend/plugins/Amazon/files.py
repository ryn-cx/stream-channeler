# TODO: Validate
import json
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, cast, override

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import BaseFile, HTMLFile
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
        self._hydration_cache: dict[str, Any] | None = None
        super().__init__(session, plugin, asin)

    @override
    def write(self, content: str | None) -> None:
        self._hydration_cache = None
        super().write(content)

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
                self.write(None)
                self.database_record.extra = f"Invalid title {self.asin}"
                return
            response.raise_for_status()
            self.write(response.text)

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

    def channel(self) -> AmazonChannel | None:
        """Return the Amazon Channel this title needs, or None when it is included."""
        for subscription in self._subscriptions():
            benefit_id = subscription.get("benefitId")
            label = subscription.get("label")
            if benefit_id in _PRIME_BENEFIT_IDS:
                continue
            if benefit_id and label:
                return AmazonChannel(benefit_id, _channel_name(label))
        return None

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

    def episodes(self) -> list[AmazonEpisode]:
        state = self._body()["btf"]["state"]
        details = state.get("detail", {}).get("detail", {})
        asins = state.get("episodeList", {}).get("cardTitleIds", [])
        result: list[AmazonEpisode] = []
        for asin in asins:
            detail = details.get(asin)
            if detail is None:
                continue
            result.append(
                AmazonEpisode(
                    asin=asin,
                    title=detail["title"],
                    episode_number=detail["episodeNumber"],
                    synopsis=detail.get("synopsis"),
                    duration=detail.get("duration"),
                    release_date=detail.get("releaseDate"),
                    image_url=_pick_image(detail.get("images", {})),
                ),
            )
        return result


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
