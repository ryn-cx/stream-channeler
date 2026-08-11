# TODO: Validate
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal, Self, get_args

from pydantic import BaseModel

from app.episodes.models import Episode
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile

ValidatorRuleType = Literal[
    "Static",
    "Incremented",
    "Decremented",
    "Changed",
    "ChangedTo",
    "Populated",
    "PopulatedOrDecremented",
    "Ignored",
]
ValidatorKey = type[BaseModel] | uuid.UUID | str
ChangedToValue = datetime | int | str

_ALL_MODELS = (Plugin, Source, Show, Season, Episode)


# TODO: Validate
class Validator:
    """Stores validation rules for plugin field validation.

    Rules can be added for:
    - Model classes (e.g., Plugin, Source) - applies to all instances
    - UUIDs - applies to specific instance by id
    - Strings - applies to specific instance by key
    """

    # TODO: Validate
    def __init__(self) -> None:
        """Initialize Validator."""
        self._rules: dict[ValidatorKey, dict[ValidatorRuleType, list[str]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self._changed_to_values: dict[ValidatorKey, dict[str, ChangedToValue]] = (
            defaultdict(dict)
        )

    # TODO: Validate
    def incremented(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must have increased in value."""
        self._rules[key]["Incremented"].extend(field_names)
        return self

    # TODO: Validate
    def decremented(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must have decreased in value."""
        self._rules[key]["Decremented"].extend(field_names)
        return self

    # TODO: Validate
    def static(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must remain the same value."""
        self._rules[key]["Static"].extend(field_names)
        return self

    # TODO: Validate
    def changed(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must have changed to a different value."""
        self._rules[key]["Changed"].extend(field_names)
        return self

    # TODO: Validate
    def changed_to(
        self,
        key: ValidatorKey,
        field_name: str,
        value: ChangedToValue,
    ) -> Self:
        """Mark a field that must have changed to a specific new value."""
        self._rules[key]["ChangedTo"].append(field_name)
        self._changed_to_values[key][field_name] = value
        return self

    # TODO: Validate
    def populated(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must go from None to a non-None value."""
        self._rules[key]["Populated"].extend(field_names)
        return self

    # TODO: Validate
    def populated_or_decremented(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must be populated if None, or decremented otherwise."""
        self._rules[key]["PopulatedOrDecremented"].extend(field_names)
        return self

    # TODO: Validate
    def ignored(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields whose value is not validated at all.

        Used when a field's post-update value is legitimately plugin- or
        data-dependent (e.g. an optimized update that only conditionally recomputes
        `update_at`) so no single Static/Changed/Populated rule fits every case.
        """
        self._rules[key]["Ignored"].extend(field_names)
        return self

    # TODO: Validate
    def static_all(self, *field_names: str) -> Self:
        """Mark fields that must remain the same for all model types."""
        for model in _ALL_MODELS:
            self.static(model, *field_names)
        return self

    # TODO: Validate
    def incremented_all(self, *field_names: str) -> Self:
        """Mark fields that must have increased for all model types."""
        for model in _ALL_MODELS:
            self.incremented(model, *field_names)
        return self

    # TODO: Validate
    def decremented_all(self, *field_names: str) -> Self:
        """Mark fields that must have decreased for all model types."""
        for model in _ALL_MODELS:
            self.decremented(model, *field_names)
        return self

    # TODO: Validate
    def changed_all(self, *field_names: str) -> Self:
        """Mark fields that must have changed for all model types."""
        for model in _ALL_MODELS:
            self.changed(model, *field_names)
        return self

    # TODO: Validate
    def populated_all(self, *field_names: str) -> Self:
        """Mark fields that must go from None to a non-None value for all model types."""
        for model in _ALL_MODELS:
            self.populated(model, *field_names)
        return self

    # TODO: Validate
    def remove(self, key: ValidatorKey, *field_names: str) -> Self:
        """Remove validation rules for specific fields."""
        if key not in self._rules:
            return self
        for rule_type in get_args(ValidatorRuleType):
            for field_name in field_names:
                if field_name in self._rules[key][rule_type]:
                    self._rules[key][rule_type].remove(field_name)
        for field_name in field_names:
            self._changed_to_values[key].pop(field_name, None)
        return self

    # TODO: Validate
    def remove_all(self, *field_names: str) -> Self:
        """Remove validation rules for specific fields across all model types."""
        for model in _ALL_MODELS:
            self.remove(model, *field_names)
        return self

    # TODO: Validate
    def _get_files(
        self,
        plugin: BasePlugin,
        entity: Show | Season | Episode,
    ) -> Sequence[BaseFile[Any]]:
        match entity:
            case Show():
                return plugin._show_files(entity.key)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
            case Season():
                return plugin._season_files(entity.key, entity.show.key)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
            case Episode():
                show = entity.season.show
                return plugin._episode_files(  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
                    entity.key,
                    entity.season.key,
                    show.key,
                )

    # TODO: Validate
    def apply_shared_file_rules(
        self,
        entity: Show | Season | Episode,
        plugin: BasePlugin,
    ) -> None:
        updated_files = set(self._get_files(plugin, entity))
        match entity:
            case Show():
                self._apply_show_share_rules(entity, plugin, updated_files)
            case Season():
                self._apply_season_share_rules(entity, plugin, updated_files)
            case Episode():
                self._apply_episode_share_rules(entity, plugin, updated_files)

    # TODO: Validate
    def _apply_show_share_rules(
        self,
        show: Show,
        plugin: BasePlugin,
        updated_files: set[BaseFile[Any]],
    ) -> None:
        for season in show.seasons:
            if self._get_files(plugin, season)[0] in updated_files:
                self.incremented(season.id, "modified_at", "data_timestamp")
            for episode in season.episodes:
                if self._get_files(plugin, episode)[0] in updated_files:
                    self.incremented(episode.id, "modified_at", "data_timestamp")

    # TODO: Validate
    def _apply_season_share_rules(
        self,
        season: Season,
        plugin: BasePlugin,
        updated_files: set[BaseFile[Any]],
    ) -> None:
        if self._get_files(plugin, season.show)[0] in updated_files:
            self.incremented(season.show.id, "modified_at", "data_timestamp")
        for episode in season.episodes:
            if self._get_files(plugin, episode)[0] in updated_files:
                self.incremented(episode.id, "modified_at", "data_timestamp")

    # TODO: Validate
    def _apply_episode_share_rules(
        self,
        episode: Episode,
        plugin: BasePlugin,
        updated_files: set[BaseFile[Any]],
    ) -> None:
        if self._get_files(plugin, episode.season)[0] in updated_files:
            self.incremented(episode.season.id, "modified_at", "data_timestamp")
        show = episode.season.show
        if self._get_files(plugin, show)[0] in updated_files:
            self.incremented(show.id, "modified_at", "data_timestamp")
        for sibling in episode.season.episodes:
            if self._get_files(plugin, sibling)[0] in updated_files:
                self.incremented(sibling.id, "modified_at", "data_timestamp")

    # TODO: Validate
    def get_rule(
        self,
        obj: Plugin | Source | Show | Season | Episode | File,
        field_name: str,
    ) -> ValidatorRuleType | None:
        """Get the validation rule for a specific object and field.

        Checks in priority order: id, key, class type.
        """
        for rules_key in (obj.id, obj.key, type(obj)):
            rules = self._rules[rules_key]
            for rule_type in get_args(ValidatorRuleType):
                if field_name in rules[rule_type]:
                    return rule_type
        return None

    # TODO: Validate
    def _get_changed_to_value(
        self,
        obj: Plugin | Source | Show | Season | Episode | File,
        field_name: str,
    ) -> ChangedToValue:
        """Get the expected value for a ChangedTo field, checking id, key, then type."""
        for rules_key in (obj.id, obj.key, type(obj)):
            if field_name in self._changed_to_values[rules_key]:
                return self._changed_to_values[rules_key][field_name]
        message = f"No changed_to value configured for {field_name}"
        raise KeyError(message)

    # TODO: Validate
    def validate[T: Plugin | Source | Show | Season | Episode](
        self,
        original: T,
        actual: T,
    ) -> None:
        """Validate that actual matches original according to the configured rules.

        Raises:
            AssertionError: If validation fails with details about mismatches.
        """
        if errors := self._validate_fields(original, actual):
            raise AssertionError("\n\n".join(errors))

    # TODO: Validate
    def _validate_fields[T: Plugin | Source | Show | Season | Episode](
        self,
        original: T,
        actual: T,
    ) -> list[str]:
        errors: list[str] = []

        if len(original.children) != len(actual.children):
            original_children = original.children
            actual_children = actual.children
            missing = [
                original_child
                for original_child in original_children
                if original_child not in actual_children
            ]
            extra = [
                actual_child
                for actual_child in actual_children
                if actual_child not in original_children
            ]
            detail_lines = [
                f"\n{original}",
                "Number of children do not match.",
                f"Original: {len(original_children)}",
                f"Actual  : {len(actual_children)}",
            ]
            detail_lines.extend(f"Missing : {child}" for child in missing)
            detail_lines.extend(f"Extra   : {child}" for child in extra)
            errors.append("\n".join(detail_lines))
            # If the number of children don't match there is no point in further
            # comparisons because they will be junk.
            return errors

        # Recursively validate children
        if isinstance(original, (Plugin, Source, Show, Season)):
            for original_child, actual_child in zip(
                sorted(original.children, key=lambda x: x.key),
                sorted(actual.children, key=lambda x: x.key),
                strict=True,
            ):
                # Help MyPy identify the objects correctly.
                assert isinstance(original_child, (Source, Show, Season, Episode))
                assert isinstance(actual_child, (Source, Show, Season, Episode))
                errors.extend(self._validate_fields(original_child, actual_child))

        # Validate each individual field
        for field_name in type(original).model_fields:
            original_value = getattr(original, field_name)
            actual_value = getattr(actual, field_name)

            if error := self._validate_field(
                original,
                field_name,
                original_value,
                actual_value,
            ):
                errors.append(error)

        return errors

    # PLR0911/C901 - Reducing the number of returns or match cases just makes the code
    # more complex and much harder to comprehend.
    # TODO: Validate
    def _validate_field[T: str | int | datetime](  # noqa: PLR0911, PLR0912, C901
        self,
        original_obj: Plugin | Source | Show | Season | Episode | File,
        field_name: str,
        original_value: T | None,
        new_value: T | None,
    ) -> str | None:
        """Validate a single field and return an error message if validation fails."""
        validator_rule = self.get_rule(original_obj, field_name)

        match validator_rule:
            case "Incremented":
                # operator - The types are guaranteed to be the same so the comparison
                # is safe to execute.
                if not (original_value and new_value) or original_value >= new_value:  # type: ignore[operator]
                    return (
                        f"{original_obj}\n"
                        f"Key Not Incremented: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )
            case "Decremented":
                # operator - The types are guaranteed to be the same so the comparison
                # is safe to execute.
                if not (original_value and new_value) or original_value <= new_value:  # type: ignore[operator]
                    return (
                        f"{original_obj}\n"
                        f"Key Not Decremented: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )
            case "Changed":
                if original_value == new_value:
                    return (
                        f"{original_obj}\n"
                        f"Key Not Changed: {field_name}\n"
                        f"Value: {original_value}\n"
                    )
            case "ChangedTo":
                expected_value = self._get_changed_to_value(original_obj, field_name)
                if new_value != expected_value:
                    return (
                        f"{original_obj}\n"
                        f"Key Not Changed To Expected Value: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Expected: {expected_value}\n"
                        f"Updated : {new_value}"
                    )
            case "Populated":
                if original_value is not None:
                    return (
                        f"{original_obj}\n"
                        f"Key Already Populated: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )
                if new_value is None:
                    return (
                        f"{original_obj}\n"
                        f"Key Not Populated: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )
            case "PopulatedOrDecremented":
                if original_value is None:
                    if new_value is None:
                        return (
                            f"{original_obj}\n"
                            f"Key Not Populated: {field_name}\n"
                            f"Original: {original_value}\n"
                            f"Updated : {new_value}"
                        )
                elif new_value is None or original_value <= new_value:  # type: ignore[operator]
                    return (
                        f"{original_obj}\n"
                        f"Key Not Decremented: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )
            case "Ignored":
                return None
            case "Static" | None:
                if original_value != new_value:
                    return (
                        f"{original_obj}\n"
                        f"Key Changed: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )

        return None
