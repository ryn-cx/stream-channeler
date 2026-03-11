# TODO: Validate
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Literal, Self, get_args

from pydantic import BaseModel

from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

ValidatorRuleType = Literal["Ignore", "Static", "Incremented", "Decremented", "Changed"]
ValidatorKey = type[BaseModel] | uuid.UUID | str

_ALL_MODELS = (Plugin, Source, Show, Season, Episode)


class Validator:
    """Stores validation rules for plugin field validation.

    Rules can be added for:
    - Model classes (e.g., Plugin, Source) - applies to all instances
    - UUIDs - applies to specific instance by id
    - Strings - applies to specific instance by key
    """

    def __init__(self) -> None:
        self._rules: dict[ValidatorKey, dict[ValidatorRuleType, list[str]]] = (
            defaultdict(lambda: defaultdict(list))
        )

    def ignore(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields to be ignored during validation."""
        self._rules[key]["Ignore"].extend(field_names)
        return self

    def incremented(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must have increased in value."""
        self._rules[key]["Incremented"].extend(field_names)
        return self

    def decremented(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must have decreased in value."""
        self._rules[key]["Decremented"].extend(field_names)
        return self

    def static(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must remain the same value."""
        self._rules[key]["Static"].extend(field_names)
        return self

    def changed(self, key: ValidatorKey, *field_names: str) -> Self:
        """Mark fields that must have changed to a different value."""
        self._rules[key]["Changed"].extend(field_names)
        return self

    def ignore_all(self, *field_names: str) -> Self:
        """Mark fields to be ignored for all model types."""
        for model in _ALL_MODELS:
            self.ignore(model, *field_names)
        return self

    def static_all(self, *field_names: str) -> Self:
        """Mark fields that must remain the same for all model types."""
        for model in _ALL_MODELS:
            self.static(model, *field_names)
        return self

    def incremented_all(self, *field_names: str) -> Self:
        """Mark fields that must have increased for all model types."""
        for model in _ALL_MODELS:
            self.incremented(model, *field_names)
        return self

    def decremented_all(self, *field_names: str) -> Self:
        """Mark fields that must have decreased for all model types."""
        for model in _ALL_MODELS:
            self.decremented(model, *field_names)
        return self

    def changed_all(self, *field_names: str) -> Self:
        """Mark fields that must have changed for all model types."""
        for model in _ALL_MODELS:
            self.changed(model, *field_names)
        return self

    def remove(self, key: ValidatorKey, *field_names: str) -> Self:
        """Remove validation rules for specific fields."""
        if key not in self._rules:
            return self
        for rule_type in get_args(ValidatorRuleType):
            for field_name in field_names:
                if field_name in self._rules[key][rule_type]:
                    self._rules[key][rule_type].remove(field_name)
        return self

    def remove_all(self, *field_names: str) -> Self:
        """Remove validation rules for specific fields across all model types."""
        for model in _ALL_MODELS:
            self.remove(model, *field_names)
        return self

    def get_rule(
        self,
        obj: Plugin | Source | Show | Season | Episode | File,
        field_name: str,
    ) -> ValidatorRuleType | None:
        """Get the validation rule for a specific object and field.

        Checks in priority order: id, key, class type.
        """
        for rules_key in (obj.id, obj.key, obj.__class__):
            rules = self._rules[rules_key]
            for rule_type in get_args(ValidatorRuleType):
                if field_name in rules[rule_type]:
                    return rule_type
        return None

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

    def _validate_fields[T: Plugin | Source | Show | Season | Episode](
        self,
        original: T,
        actual: T,
    ) -> list[str]:
        errors: list[str] = []

        if len(original.children()) != len(actual.children()):
            original_children = original.children()
            actual_children = actual.children()
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
                sorted(original.children(), key=lambda x: x.key),
                sorted(actual.children(), key=lambda x: x.key),
                strict=True,
            ):
                # type-var - This seems to be a bug in MyPy. validate_fields defines
                # the parameters as a plugin, source, show, season, or episode.
                # Therefore it is impossible for either arguement to ever be a
                # MetadataMixin. MyPy incorrectly identifies one of the arguements as a
                # MetadataMixin so the error should be ignored.
                errors.extend(self._validate_fields(original_child, actual_child))  # type: ignore[type-var]

        # Validate each individual field
        for field_name in original.__class__.model_fields:
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

    # PLR0911 - Reducing the number of returns just makes the code more complex and much
    # harder to comprehend.
    def _validate_field[T: str | int | datetime](
        self,
        original_obj: Plugin | Source | Show | Season | Episode | File,
        field_name: str,
        original_value: T | None,
        new_value: T | None,
    ) -> str | None:
        """Validate a single field and return an error message if validation fails."""
        validator_rule = self.get_rule(original_obj, field_name)

        match validator_rule:
            case "Ignore":
                return None
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
            case "Static" | None:
                if original_value != new_value:
                    return (
                        f"{original_obj}\n"
                        f"Key Changed: {field_name}\n"
                        f"Original: {original_value}\n"
                        f"Updated : {new_value}"
                    )

        return None
