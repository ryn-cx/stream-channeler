# TODO: Validate
"""Plugin dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record, readable_record
from app.plugins.models import Plugin

ReadablePlugin = Annotated[Plugin, Depends(readable_record(Plugin, "plugin_id"))]
EditablePlugin = Annotated[Plugin, Depends(editable_record(Plugin, "plugin_id"))]
