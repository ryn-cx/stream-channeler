# TODO: Validate
from typing import Annotated

from fastapi import Depends, HTTPException

from app.plugins.identifiers import TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY
from app.sources.dependencies import ExistingSource
from app.sources.models import Source


# TODO: Validate
def _require_store_source(source: ExistingSource) -> Source:
    if source.plugin.key in {TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY}:
        raise HTTPException(status_code=404, detail="Source is not in the video store")
    return source


StoreSource = Annotated[Source, Depends(_require_store_source)]
