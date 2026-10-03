# TODO: Validate
import re

from pydantic import BaseModel

from app.tmdb_media.tmdb import TMDB_PAGE_URL

_SUGGESTION = re.compile(
    r"^Incorrect Title Information\. The correct title is (?P<name>.+?)"
    r"(?: \((?P<year>\d+)\))? \[(?P<media_type>movie|tv) (?P<tmdb_id>\d+)\]\.$",
)


# TODO: Validate
class SuggestedTitle(BaseModel):
    name: str
    year: int | None
    url: str


# TODO: Validate
def suggested_title(report: str) -> SuggestedTitle | None:
    match = _SUGGESTION.match(report)
    if match is None:
        return None
    return SuggestedTitle(
        name=match["name"],
        year=int(match["year"]) if match["year"] else None,
        url=f"{TMDB_PAGE_URL}/{match['media_type']}/{match['tmdb_id']}",
    )
