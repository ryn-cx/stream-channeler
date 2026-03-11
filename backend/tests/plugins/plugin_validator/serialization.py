from typing import Any

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

_CHILDREN: dict[type, tuple[str, type]] = {
    Plugin: ("sources", Source),
    Source: ("shows", Show),
    Show: ("seasons", Season),
    Season: ("episodes", Episode),
}


class SerializationMixin:
    @staticmethod
    def _dump_model(model: Plugin | Source | Show | Season) -> dict[str, Any]:
        """Recursively dump a model into a dict."""
        data = model.model_dump()
        if type(model) in _CHILDREN:
            key, _ = _CHILDREN[type(model)]
            data[key] = sorted(
                [
                    SerializationMixin._dump_model(child)
                    for child in getattr(model, key)
                ],
                key=lambda x: x["id"],
            )
        return data

    @staticmethod
    def _load_model[T: (Plugin, Source, Show, Season, Episode)](
        model_class: type[T],
        data: dict[str, Any],
    ) -> T:
        """Recursively load a dict into a model."""
        model = model_class.model_validate(data)
        if model_class in _CHILDREN:
            key, child_class = _CHILDREN[model_class]
            setattr(
                model,
                key,
                [
                    SerializationMixin._load_model(child_class, child)
                    for child in data[key]
                ],
            )
        return model
