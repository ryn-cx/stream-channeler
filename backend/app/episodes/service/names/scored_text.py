# TODO: Validate
from app.episodes.service.names.forms import (
    get_cased_episode_name,
    part_numbers,
)
from app.episodes.service.names.matching import (
    is_only_numbered_name,
    is_untitled_name,
)


# TODO: Validate
def name_for_scoring(
    name: str | None,
    title_name: str | None = None,
    season_name: str | None = None,
    series_name: str | None = None,
) -> str:
    meaningful = part_numbers(
        get_cased_episode_name(name, title_name, season_name, series_name),
    )
    if (
        not meaningful
        or is_untitled_name(meaningful)
        or is_only_numbered_name(meaningful)
    ):
        return ""
    return (name or "").strip()


# TODO: Validate
def description_for_scoring(description: str | None) -> str:
    return (description or "").strip()
