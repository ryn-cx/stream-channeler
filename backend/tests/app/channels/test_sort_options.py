# TODO: Validate
"""What a channel can be sorted by."""

from app.channels import service
from app.channels.schemas import SortKeyInput


# TODO: Validate
def test_every_sortable_field_is_offered() -> None:
    options = service.get_sort_options()

    offered = {(option.model, option.field) for option in options}
    expected = {
        (model_name, field)
        for model_name, model in SortKeyInput.MODEL_MAP.items()
        for field in model.SORTABLE_FIELDS
    }
    assert offered == expected


# TODO: Validate
def test_every_option_is_labelled() -> None:
    assert all(option.label for option in service.get_sort_options())
