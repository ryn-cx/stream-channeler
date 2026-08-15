# TODO: Validate
"""What each test cost to run, measured the way the existing validator measures it."""

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

from tests.old_mess.plugins.plugin_validator.log_stats import (
    log_stats as _log_stats,
)

if TYPE_CHECKING:
    from tests.plugins.plugin_validator_alt.database import DatabaseMixinAlt


# TODO: Validate
def log_stats(plugin_validator: DatabaseMixinAlt[Any]) -> AbstractContextManager[None]:
    """Record what the block cost, under the alt validator's own stats files."""
    return _log_stats(plugin_validator)  # type: ignore[arg-type]
