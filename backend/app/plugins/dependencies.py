# TODO: Validate
"""Plugin dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import existing_record
from app.plugins.models import Plugin

ExistingPlugin = Annotated[Plugin, Depends(existing_record(Plugin, "plugin_id"))]
