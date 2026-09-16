# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from plugins.ParamountPlus.files import (
    CarouselFile,
    CollectionFile,
    CollectionsFile,
    EpisodesFile,
    MovieFile,
    SectionFile,
    TitlePage,
    carousel_entries,
)
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trivial_minus.collection.models import Carousel as CollectionCarousel
    from trivial_minus.collections.models import Carousel as CollectionsCarousel

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class ParamountPlusBaseFiles(BasePlugin):
    # TODO: Validate
    def title_page_file(self, title_id: str) -> TitlePage:
        return self._cached_file(TitlePage, title_id)

    # TODO: Validate
    def episodes_file(
        self,
        title_id: str,
        season_number: int,
    ) -> EpisodesFile:
        return self._cached_file(EpisodesFile, title_id, season_number)

    # TODO: Validate
    def collections_file(self) -> CollectionsFile:
        return self._cached_file(CollectionsFile)

    # TODO: Validate
    def collection_file(self, collection_id: str) -> CollectionFile:
        return self._cached_file(CollectionFile, collection_id)

    # TODO: Validate
    def carousel_file(
        self,
        carousel: CollectionsCarousel | CollectionCarousel,
    ) -> CarouselFile:
        return self._cached_file(
            CarouselFile,
            carousel.slug,
            str(carousel.carousel_id),
            carousel.token,
        )

    # TODO: Validate
    def carousel_files(
        self,
        carousels: Sequence[CollectionsCarousel | CollectionCarousel],
    ) -> list[CarouselFile]:
        return [self.carousel_file(carousel) for carousel in carousels]

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BaseFile[Any]]:
        collections_file = self.collections_file()
        collections_file.download_if_outdated()
        hub_carousel_files = self.carousel_files(collections_file.parsed().carousels)
        self._download_if_outdated(hub_carousel_files)

        files: list[BaseFile[Any]] = [collections_file, *hub_carousel_files]
        for collection_key in self.collections():
            collection_file = self.collection_file(collection_key)
            collection_file.download_if_outdated()
            files.append(collection_file)
            files += self.carousel_files(collection_file.parsed().carousels)
        return files

    # TODO: Validate
    def collections(self) -> dict[str, str]:
        names: dict[str, str] = {}
        carousels = self.collections_file().parsed().carousels
        for carousel_file in self.carousel_files(carousels):
            for page in carousel_file.parsed():
                for entry in carousel_entries(page):
                    if entry.slug and entry.title:
                        names.setdefault(entry.slug, entry.title)
        return names

    # TODO: Validate
    def section_file(self, title_id: str, section_id: int) -> SectionFile:
        return self._cached_file(SectionFile, title_id, section_id)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._cached_file(MovieFile, movie_id)
